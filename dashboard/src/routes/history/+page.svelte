<script lang="ts">
  // History — see what is true, spot what is broken, repair it in one commit.
  import { onMount } from "svelte";
  import { page } from "$app/stores";
  import { isAuthed, login, repoRef } from "$lib/auth";
  import { todayNYC, nowHHMM } from "$lib/daily";
  import { buildSummary, loadRange, recentDates, clearCache, type DayRecord } from "$lib/history";
  import { rollupIntegrity } from "$lib/analytics";
  import { draftFromEvidence, draftToWrites } from "$lib/backfill";
  import { logFields } from "$lib/writeDaily";
  import StatusBadge from "$lib/components/StatusBadge.svelte";
  import type { BackfillDraft, DaySummary } from "$lib/types";

  const RANGES = [7, 14, 30, 90];
  const FILTERS = [
    { id: "all", label: "All" },
    { id: "journal_only", label: "Journal only" },
    { id: "needs_input", label: "Needs you" },
    { id: "missing", label: "Has gaps" },
    { id: "blackout", label: "No entry" },
  ];

  let authed = $state(false);
  let loading = $state(true);
  let busy = $state(false);
  let err = $state<string | null>(null);
  let toast = $state<string | null>(null);

  let today = $state(todayNYC());
  let now = $state(nowHHMM());
  let range = $state(7);
  let filter = $state("all");
  let records = $state<DayRecord[]>([]);
  let selected = $state<string | null>(null);
  let draft = $state<BackfillDraft | null>(null);

  const days = $derived(records.map((r) => buildSummary(r, today, now)).sort((a, b) => b.date.localeCompare(a.date)));
  const integrity = $derived(rollupIntegrity(days));
  const shown = $derived(days.filter(matches));
  const selectedDay = $derived(days.find((d) => d.date === selected) ?? null);
  const selectedRecord = $derived(records.find((r) => r.date === selected) ?? null);

  function matches(d: DaySummary) {
    if (filter === "all") return true;
    if (filter === "journal_only") return d.journalOnly.length > 0 || d.structuredOnly.length > 0;
    if (filter === "needs_input") return d.needsInput.length > 0;
    if (filter === "missing") return d.routines.some((r) => r.state === "missing");
    if (filter === "blackout") return d.integrity === "blackout" || d.integrity === "no_data";
    return true;
  }

  onMount(async () => {
    authed = isAuthed();
    const f = $page.url.searchParams.get("filter");
    if (f && FILTERS.some((x) => x.id === f)) filter = f;
    const d = $page.url.searchParams.get("date");
    if (d) selected = d;
    if (authed) await load();
    loading = false;
  });

  async function load() {
    err = null;
    loading = true;
    try {
      today = todayNYC();
      now = nowHHMM();
      records = await loadRange(repoRef(), recentDates(today, range));
    } catch (e) {
      err = (e as Error).message;
    } finally {
      loading = false;
    }
  }

  async function setRange(n: number) {
    range = n;
    await load();
  }

  function openBackfill(date: string) {
    const rec = records.find((r) => r.date === date);
    const day = days.find((d) => d.date === date);
    if (!rec || !day) return;
    draft = draftFromEvidence(date, rec.facts, [...day.journalOnly, ...day.needsInput]);
  }

  async function saveDraft() {
    if (!draft) return;
    busy = true;
    err = null;
    try {
      const { writes, errors } = draftToWrites(draft);
      if (!writes.length) {
        err = errors.join(" · ") || "Nothing to write";
        return;
      }
      const res = await logFields(repoRef(), writes, draft.date);
      toast = `${draft.date}: ${res.fields.length} fields in one commit (${res.sha.slice(0, 7)}) — both records verified`;
      setTimeout(() => (toast = null), 4000);
      draft = null;
      clearCache();
      await load();
    } catch (e) {
      err = (e as Error).message;
    } finally {
      busy = false;
    }
  }

  function toggleFieldState(i: number, state: "value" | "skipped" | "not_reported") {
    if (!draft) return;
    const fields = [...draft.fields];
    fields[i] = { ...fields[i], state, error: state === "value" ? fields[i].error : undefined };
    draft = { ...draft, fields };
  }

  function removeField(i: number) {
    if (!draft) return;
    draft = { ...draft, fields: draft.fields.filter((_, j) => j !== i) };
  }

  /** Dashboard lines from the selected day, as evidence in the detail drawer. */
  const evidence = $derived(
    selectedRecord?.facts.map((f) => `[${f.field}] ${f.raw}`).join("\n") ?? "",
  );
</script>

<svelte:head><title>History — OptiMind</title></svelte:head>

{#if !authed && !loading}
  <div class="card stack">
    <h1>History</h1>
    <button class="primary" onclick={() => login()}>Connect GitHub</button>
  </div>
{:else}
  <header style="margin-bottom:var(--s-2);">
    <h1>History</h1>
    <p class="small muted">
      {integrity.matched}/{integrity.closed} closed days consistent
      {#if integrity.repairable}· <span style="color:var(--info)">{integrity.repairable} repairable</span>{/if}
      {#if integrity.needsInput}· <span style="color:var(--warn)">{integrity.needsInput} need you</span>{/if}
    </p>
  </header>

  {#if err}<div class="banner safety" style="margin-bottom:var(--s-2);"><span class="mono">!</span><div class="grow small">{err}</div></div>{/if}

  <div class="card">
    <div class="row wrap" style="margin-bottom:var(--s-2);">
      {#each RANGES as n}
        <button class="small-btn" class:primary={range === n} onclick={() => setRange(n)}>{n}d</button>
      {/each}
    </div>
    <div class="row wrap">
      {#each FILTERS as f}
        <button class="small-btn ghost" class:primary={filter === f.id} onclick={() => (filter = f.id)}>
          {f.label}
        </button>
      {/each}
    </div>

    <div class="strip" style="margin-top:var(--s-2);">
      {#each [...days].reverse() as d (d.date)}
        <button class="strip-cell" data-state={d.integrity} data-selected={selected === d.date}
                onclick={() => (selected = selected === d.date ? null : d.date)}
                title="{d.date} — {d.integrity}">
          <span class="glyph" aria-hidden="true">
            {d.integrity === "matched" ? "✓" : d.integrity === "in_progress" ? "●"
              : d.integrity === "blackout" || d.integrity === "no_data" ? "—"
              : d.integrity === "needs_input" ? "!" : "◑"}
          </span>
          <span>{d.date.slice(8)}</span>
        </button>
      {/each}
    </div>
  </div>

  {#if loading}
    <div class="card"><p class="muted">Loading {range} days…</p></div>
  {:else}
    <div class="card scroll-x" style="margin-top:var(--s-2);">
      <table>
        <thead>
          <tr>
            <th>Date</th><th>Record</th><th>Sleep</th><th>Back</th><th>Routines</th><th></th>
          </tr>
        </thead>
        <tbody>
          {#each shown as d (d.date)}
            <tr>
              <td class="mono">{d.date.slice(5)}{d.isToday ? " ·" : ""}</td>
              <td><StatusBadge state={d.integrity} size="sm" /></td>
              <td class="mono small">{d.sleep.quality.value != null ? `${d.sleep.quality.value}/5` : "—"}</td>
              <td class="mono small">{d.backPain.value != null ? `${d.backPain.value}/5` : "—"}</td>
              <td class="small dim">
                {d.routines.filter((r) => r.state === "done").length} done
                {#if d.routines.filter((r) => r.state === "missing").length}
                  · {d.routines.filter((r) => r.state === "missing").length} missing
                {/if}
              </td>
              <td>
                {#if d.journalOnly.length || d.needsInput.length}
                  <button class="small-btn" onclick={() => openBackfill(d.date)}>Repair</button>
                {:else}
                  <button class="small-btn ghost" onclick={() => (selected = d.date)}>View</button>
                {/if}
              </td>
            </tr>
          {:else}
            <tr><td colspan="6" class="muted small">No days match this filter.</td></tr>
          {/each}
        </tbody>
      </table>
    </div>
  {/if}
{/if}

<!-- Day detail -->
{#if selectedDay && !draft}
  <div class="scrim" role="presentation" onclick={() => (selected = null)}></div>
  <div class="drawer" role="dialog" aria-modal="true" aria-label="Day detail">
    <div class="row-between" style="margin-bottom:var(--s-2);">
      <div>
        <h2>{selectedDay.date}</h2>
        <StatusBadge state={selectedDay.integrity} size="sm" />
      </div>
      <button class="ghost small-btn" onclick={() => (selected = null)}>Close</button>
    </div>

    {#if selectedDay.journalOnly.length}
      <div class="banner integrity" style="margin-bottom:var(--s-2);">
        <span class="mono">◑</span>
        <div class="grow small">
          <strong>In the journal, missing from the structured log</strong>
          <p class="dim" style="margin-top:4px;">{selectedDay.journalOnly.join(", ")}</p>
          <p class="tiny muted" style="margin-top:4px;">The behavior happened. The write was lost.</p>
        </div>
      </div>
    {/if}
    {#if selectedDay.needsInput.length}
      <div class="banner attention" style="margin-bottom:var(--s-2);">
        <span class="mono">!</span>
        <div class="grow small">
          <strong>Only you can complete these</strong>
          <p class="dim" style="margin-top:4px;">{selectedDay.needsInput.join(", ")} — the journal states the event but not a time or dose.</p>
        </div>
      </div>
    {/if}

    <div class="section-title">Journal evidence</div>
    {#if evidence}
      <pre class="evidence">{evidence}</pre>
    {:else}
      <p class="small muted">No Dashboard lines on this day.</p>
    {/if}

    <div class="section-title" style="margin-top:var(--s-2);">Routines</div>
    <div class="stack-sm">
      {#each selectedDay.routines as r (r.id)}
        <div class="row-between small">
          <span>{r.label}</span>
          <StatusBadge state={r.state} size="sm" />
        </div>
      {/each}
    </div>

    {#if selectedDay.journalOnly.length || selectedDay.needsInput.length}
      <button class="primary" style="width:100%;margin-top:var(--s-2);"
              onclick={() => openBackfill(selectedDay.date)}>
        Repair this day
      </button>
    {/if}
  </div>
{/if}

<!-- Backfill -->
{#if draft}
  <div class="scrim" role="presentation" onclick={() => (draft = null)}></div>
  <div class="drawer" role="dialog" aria-modal="true" aria-label="Backfill">
    <div class="row-between" style="margin-bottom:var(--s-2);">
      <h2>Repair {draft.date}</h2>
      <button class="ghost small-btn" onclick={() => (draft = null)}>Cancel</button>
    </div>

    <p class="small dim" style="margin-bottom:var(--s-2);">
      Prefilled from the journal lines below. Everything saves as one commit.
    </p>

    <div class="stack">
      {#each draft.fields as f, i (f.field + i)}
        <div class="card" style="background:var(--surface-2);padding:var(--s-1) var(--s-2);">
          <div class="row-between" style="margin-bottom:6px;">
            <strong class="small">{f.label}</strong>
            <div class="row" style="gap:4px;">
              {#if f.isEstimate}<StatusBadge state="estimated" size="sm" />{/if}
              <button class="ghost small-btn tiny" onclick={() => removeField(i)}>Drop</button>
            </div>
          </div>

          {#if f.error}
            <p class="tiny" style="color:var(--warn);margin-bottom:6px;">{f.error} — mark it instead of guessing.</p>
          {:else}
            <p class="tiny mono dim" style="margin-bottom:6px;">{JSON.stringify(f.value)}</p>
          {/if}

          <div class="row" style="gap:4px;">
            {#each (["value", "skipped", "not_reported"] as const) as s}
              <button class="small-btn ghost tiny" class:primary={f.state === s}
                      disabled={s === "value" && !!f.error}
                      onclick={() => toggleFieldState(i, s)}>
                {s === "value" ? "Use value" : s === "skipped" ? "Skipped" : "Not reported"}
              </button>
            {/each}
          </div>

          {#if f.evidence}
            <p class="tiny muted mono" style="margin-top:6px;word-break:break-word;">{f.evidence}</p>
          {/if}
        </div>
      {:else}
        <p class="small muted">Nothing to repair on this day.</p>
      {/each}
    </div>

    <button class="primary" style="width:100%;margin-top:var(--s-2);" disabled={busy || !draft.fields.length}
            onclick={saveDraft}>
      {busy ? "Writing…" : `Save ${draft.fields.length} field${draft.fields.length === 1 ? "" : "s"} in one commit`}
    </button>
    <p class="tiny muted" style="margin-top:var(--s-1);">
      Journal prose is never modified. A new labelled mirror is appended and the structured record updated,
      both in the same commit, and re-read before this reports success.
    </p>
  </div>
{/if}

{#if toast}<div class="toast">{toast}</div>{/if}
