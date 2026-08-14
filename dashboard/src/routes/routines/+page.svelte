<script lang="ts">
  // Routines — derived from the profile rules and each day's protocol items,
  // never a hard-coded list. Every state is shown separately: a routine with
  // 0 done and 5 not-reported is a measurement problem, not a discipline one,
  // and collapsing them into one percentage hides which.
  import { onMount } from "svelte";
  import { isAuthed, repoRef } from "$lib/auth";
  import SignIn from "$lib/components/SignIn.svelte";
  import { todayNYC, nowHHMM } from "$lib/daily";
  import { buildSummary, loadRange, recentDates } from "$lib/history";
  import { rollupRoutines, type RoutineRollup } from "$lib/analytics";
  import type { DaySummary } from "$lib/types";

  const RANGES = [7, 14, 30];

  let authed = $state(false);
  let loading = $state(true);
  let range = $state(14);
  let today = $state(todayNYC());
  let days = $state<DaySummary[]>([]);
  let expanded = $state<string | null>(null);

  const rows = $derived(rollupRoutines(days));
  const closed = $derived(days.filter((d) => !d.isToday).length);

  onMount(async () => {
    authed = isAuthed();
    if (authed) await load();
    loading = false;
  });

  async function load() {
    loading = true;
    today = todayNYC();
    const now = nowHHMM();
    const recs = await loadRange(repoRef(), recentDates(today, range));
    days = recs.map((r) => buildSummary(r, today, now));
    loading = false;
  }

  async function setRange(n: number) {
    range = n;
    await load();
  }

  /** Width of each segment in the state bar, as a percentage. */
  function seg(row: RoutineRollup, n: number) {
    const total = row.done + row.skipped + row.notReported + row.missing;
    return total ? (n / total) * 100 : 0;
  }
</script>

<svelte:head><title>Routines — OptiMind</title></svelte:head>

{#if !authed && !loading}
  <SignIn onconnected={async () => { authed = true; await load(); }} />
{:else}
  <header style="margin-bottom:var(--s-2);">
    <h1>Routines</h1>
    <p class="small muted">{closed} closed days · states counted separately, never averaged into one score</p>
  </header>

  <div class="card">
    <div class="row wrap">
      {#each RANGES as n}
        <button class="small-btn" class:primary={range === n} onclick={() => setRange(n)}>{n}d</button>
      {/each}
    </div>
  </div>

  {#if loading}
    <div class="card" style="margin-top:var(--s-2);"><p class="muted">Loading…</p></div>
  {:else}
    <div class="stack" style="margin-top:var(--s-2);">
      {#each rows as row (row.id)}
        <div class="card">
          <div class="row-between">
            <div class="grow">
              <strong>{row.label}</strong>
              <p class="tiny muted mono" style="margin-top:2px;">
                {row.done} done · {row.skipped} skipped · {row.notReported} not reported · {row.missing} missing
              </p>
            </div>
            <button class="ghost small-btn"
                    onclick={() => (expanded = expanded === row.id ? null : row.id)}
                    aria-expanded={expanded === row.id}>
              {expanded === row.id ? "Hide" : "Dates"}
            </button>
          </div>

          <!-- Segmented bar: each state is its own width, none absorbed into another. -->
          <div class="row" style="gap:2px;margin-top:10px;height:6px;border-radius:3px;overflow:hidden;">
            <div style="width:{seg(row, row.done)}%;background:var(--ok);" title="{row.done} done"></div>
            <div style="width:{seg(row, row.skipped)}%;background:var(--text-3);" title="{row.skipped} skipped"></div>
            <div style="width:{seg(row, row.notReported)}%;background:var(--surface-3);" title="{row.notReported} not reported"></div>
            <div style="width:{seg(row, row.missing)}%;background:var(--warn);" title="{row.missing} missing"></div>
          </div>

          {#if row.confidence < 0.7}
            <p class="tiny" style="color:var(--warn);margin-top:8px;">
              Outcome known on {Math.round(row.confidence * 100)}% of days — too little evidence to call this a habit result.
            </p>
          {/if}

          {#if expanded === row.id}
            <div class="stack-sm small" style="margin-top:var(--s-2);">
              {#if row.dates.done.length}
                <div><span class="muted tiny">Done</span> <span class="mono tiny">{row.dates.done.join(" ")}</span></div>
              {/if}
              {#if row.dates.skipped.length}
                <div><span class="muted tiny">Skipped</span> <span class="mono tiny">{row.dates.skipped.join(" ")}</span></div>
              {/if}
              {#if row.dates.missing.length}
                <div><span class="muted tiny">Missing</span> <span class="mono tiny">{row.dates.missing.join(" ")}</span></div>
              {/if}
            </div>
          {/if}
        </div>
      {:else}
        <div class="card"><p class="muted small">No routines in this window.</p></div>
      {/each}
    </div>
  {/if}
{/if}
