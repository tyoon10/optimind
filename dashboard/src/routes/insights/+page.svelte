<script lang="ts">
  // Insights — at most three actionable items, ranked deterministically.
  // Language stays observational: `observed`, `coverage`, `open loop`. A
  // priority is not a causal claim, and a chart is not an explanation.
  import { onMount } from "svelte";
  import { isAuthed, login, repoRef } from "$lib/auth";
  import { todayNYC, nowHHMM } from "$lib/daily";
  import { buildSummary, loadRange, recentDates } from "$lib/history";
  import { buildTrends } from "$lib/analytics";
  import { activeInsights, buildInsights, dismissNudge, readNudgeState, snoozeNudge } from "$lib/insights";
  import TrendChart from "$lib/components/TrendChart.svelte";
  import type { DaySummary, Insight } from "$lib/types";

  let authed = $state(false);
  let loading = $state(true);
  let today = $state(todayNYC());
  let days = $state<DaySummary[]>([]);
  let nudgeState = $state(readNudgeState());
  let range = $state(14);

  const trends = $derived(buildTrends(days));
  const all = $derived(buildInsights(days, today));
  const active = $derived(activeInsights(all, today, nudgeState));

  onMount(async () => {
    authed = isAuthed();
    if (authed) await load();
    loading = false;
  });

  async function load() {
    loading = true;
    today = todayNYC();
    const now = nowHHMM();
    days = (await loadRange(repoRef(), recentDates(today, range))).map((r) => buildSummary(r, today, now));
    loading = false;
  }

  function dismiss(i: Insight) {
    dismissNudge(i.id);
    nudgeState = readNudgeState();
  }
  function snooze(i: Insight) {
    const d = new Date(`${today}T12:00:00Z`);
    d.setUTCDate(d.getUTCDate() + 3);
    snoozeNudge(i.id, d.toISOString().slice(0, 10));
    nudgeState = readNudgeState();
  }

  const TONE: Record<string, string> = {
    integrity: "integrity", safety: "safety", measurement: "attention", coverage: "attention",
  };
  const KIND_LABEL: Record<string, string> = {
    integrity: "Record integrity", safety: "Safety gate",
    measurement: "Unmeasured", coverage: "Low coverage",
  };

  function arrow(d: string) {
    return d === "up" ? "↑" : d === "down" ? "↓" : d === "flat" ? "→" : "·";
  }
</script>

<svelte:head><title>Insights — OptiMind</title></svelte:head>

{#if !authed && !loading}
  <div class="card stack">
    <h1>Insights</h1>
    <button class="primary" onclick={() => login()}>Connect GitHub</button>
  </div>
{:else}
  <header style="margin-bottom:var(--s-2);">
    <h1>Insights</h1>
    <p class="small muted">Last {range} days · at most three actions at a time</p>
  </header>

  {#if loading}
    <div class="card"><p class="muted">Loading…</p></div>
  {:else}
    <div class="section-title">What matters now</div>
    {#if active.length}
      <div class="stack">
        {#each active as i (i.id)}
          <div class="banner {TONE[i.kind]}">
            <span class="mono" aria-hidden="true">
              {i.kind === "integrity" ? "◑" : i.kind === "safety" ? "!" : "○"}
            </span>
            <div class="grow">
              <p class="tiny muted" style="text-transform:uppercase;letter-spacing:0.06em;">
                {KIND_LABEL[i.kind]}
              </p>
              <strong>{i.title}</strong>
              <p class="small dim" style="margin-top:4px;">{i.evidence}</p>

              {#if i.sources.length}
                <p class="tiny muted mono" style="margin-top:6px;">
                  {i.sources.map((s) => s.path).join(" · ")}
                </p>
              {/if}

              <div class="row wrap" style="margin-top:10px;">
                {#if i.action?.href}
                  <a class="btn small-btn primary" href={i.action.href}>{i.action.label}</a>
                {:else if i.action}
                  <a class="btn small-btn primary" href="/">{i.action.label}</a>
                {/if}
                <button class="ghost small-btn" onclick={() => snooze(i)}>Snooze 3d</button>
                <button class="ghost small-btn" onclick={() => dismiss(i)}>Dismiss</button>
              </div>
            </div>
          </div>
        {/each}
      </div>
      {#if all.length > active.length}
        <p class="tiny muted" style="margin-top:var(--s-1);">
          {all.length - active.length} more held back — three at a time, by design.
        </p>
      {/if}
    {:else}
      <div class="card">
        <p class="small">Nothing needs attention in this window.</p>
        <p class="tiny muted" style="margin-top:4px;">
          Snoozed and dismissed items live in this browser only, never in the repository.
        </p>
      </div>
    {/if}

    <div class="section-title" style="margin-top:var(--s-3);">Trends</div>
    <div class="grid" style="grid-template-columns:repeat(auto-fit,minmax(260px,1fr));">
      {#each trends as t (t.id)}
        <div class="card">
          <div class="row-between">
            <strong class="small">{t.label}</strong>
            <span class="mono small dim">
              {t.latest ?? "—"}{t.scale ? `/${t.scale}` : t.unit ? ` ${t.unit}` : ""}
              <span class="muted">{arrow(t.direction)}</span>
            </span>
          </div>
          <TrendChart series={t} />
        </div>
      {/each}
    </div>

    <p class="tiny muted" style="margin-top:var(--s-2);">
      Hollow markers are days the journal recorded but the structured log lost. Dotted baseline
      marks are days with no reading — an unknown value, not a zero. Ranking reflects stated
      priorities and observed coverage; it is not a claim about cause.
    </p>
  {/if}
{/if}
