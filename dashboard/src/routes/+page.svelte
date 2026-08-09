<script lang="ts">
  // Today — capture first.
  //
  // The first thing on screen is what today still needs, as a live checklist.
  // Integrity sits below it: important, but it is about yesterday, and the
  // screen you open at 05:40 should be about right now.
  import { onMount } from "svelte";
  import { isAuthed, login, repoRef, clearToken } from "$lib/auth";
  import { logFields, type FieldWrite } from "$lib/writeDaily";
  import { todayNYC, nowHHMM } from "$lib/daily";
  import { buildSummary, recentDates, loadSummaries, refreshDay, clearCache } from "$lib/history";
  import { rollupIntegrity } from "$lib/analytics";
  import StatusBadge from "$lib/components/StatusBadge.svelte";
  import CaptureDrawer from "$lib/components/CaptureDrawer.svelte";
  import type { CaptureSpec } from "$lib/capture";
  import type { DaySummary, RoutineState } from "$lib/types";

  let authed = $state(false);
  let loading = $state(true);
  let busy = $state(false);
  let err = $state<string | null>(null);
  let toast = $state<string | null>(null);

  let today = $state(todayNYC());
  let now = $state(nowHHMM());
  let day = $state<DaySummary | null>(null);
  let week = $state<DaySummary[]>([]);
  let capture = $state<CaptureSpec | null>(null);

  const CAPTURES: Record<string, CaptureSpec> = {
    morning: {
      title: "Morning log",
      hint: "The three integers the rest of the day's gating rides on.",
      fields: [
        { field: "sleep.bedtime", label: "Bedtime", kind: "time" },
        { field: "sleep.wake_time", label: "Wake time", kind: "time" },
        { field: "sleep.quality", label: "Sleep quality (1–5)", kind: "score", placeholder: "3" },
      ],
    },
    back_pain: {
      title: "Back pain",
      hint: "Gates strength work at 2/5 or below.",
      fields: [{ field: "metrics.back_pain", label: "Score (1–5)", kind: "score", placeholder: "2" }],
    },
    focus: {
      title: "Focus block",
      hint: "Quality plus minutes. Σ(quality × hours) is computed from these.",
      fields: [
        { field: "metrics.focus_morning", label: "Quality (1–5)", kind: "score", placeholder: "4" },
        { field: "__minutes", label: "Minutes", kind: "number", placeholder: "120" },
      ],
    },
    meal: {
      title: "Meal",
      grouped: true,
      groupField: "meal",
      fields: [{ field: "items", label: "What you ate", kind: "text", placeholder: "eggs, tomatoes, yogurt" }],
    },
    caffeine: {
      title: "Caffeine",
      grouped: true,
      groupField: "caffeine",
      fields: [
        { field: "amount_mg", label: "Amount (mg)", kind: "number", placeholder: "95" },
        { field: "source", label: "Source", kind: "text", placeholder: "black coffee + L-theanine" },
      ],
    },
    workout: {
      title: "Workout",
      grouped: true,
      groupField: "workout",
      fields: [
        { field: "duration_min", label: "Minutes", kind: "number", placeholder: "40" },
        { field: "type", label: "Type", kind: "text", placeholder: "strength" },
      ],
    },
  };

  onMount(async () => {
    authed = isAuthed();
    if (authed) await load();
    loading = false;
  });

  async function load() {
    err = null;
    try {
      today = todayNYC();
      now = nowHHMM();
      const rec = await refreshDay(repoRef(), today);
      day = buildSummary(rec, today, now);
      week = await loadSummaries(repoRef(), recentDates(today, 7), today, now);
    } catch (e) {
      err = (e as Error).message;
    }
  }

  function flash(m: string) {
    toast = m;
    setTimeout(() => (toast = null), 2600);
  }

  async function save(writes: FieldWrite[]) {
    busy = true;
    err = null;
    try {
      // The focus form collects minutes separately so it can ride metrics.note.
      const minutes = writes.find((w) => w.field === "__minutes")?.value;
      const cleaned = writes
        .filter((w) => w.field !== "__minutes")
        .map((w) =>
          w.field.startsWith("metrics.")
            ? {
                ...w,
                value: {
                  value: Number(w.value), scale: 5,
                  ...(minutes ? { note: `${minutes}min` } : {}),
                },
              }
            : w,
        );

      const res = await logFields(repoRef(), cleaned, today);
      capture = null;
      flash(`Saved ${res.fields.length} field${res.fields.length > 1 ? "s" : ""} — both records verified`);
      clearCache();
      await load();
    } catch (e) {
      err = (e as Error).message;
    } finally {
      busy = false;
    }
  }

  async function markRoutine(id: string, state: "done" | "skipped") {
    await save([{ field: `routine.${id}`, value: { status: state, time: nowHHMM() }, time: nowHHMM() }]);
  }

  const captured = $derived(day ? day.routines.filter((r) => isCaptured(r.state)).length : 0);
  const trackable = $derived(day ? day.routines.filter((r) => r.state !== "not_due").length : 0);
  const integrity = $derived(rollupIntegrity(week));

  function isCaptured(s: RoutineState) {
    return s === "done" || s === "skipped" || s === "not_reported";
  }

  function glyphFor(s: RoutineState) {
    return { done: "✓", skipped: "–", not_reported: "?", missing: "○", scheduled: "◷", not_due: "·", unknown: "?" }[s];
  }
  function classFor(s: RoutineState) {
    if (s === "done") return "is-done";
    if (s === "missing") return "is-missing";
    if (s === "scheduled") return "is-scheduled";
    return "";
  }
</script>

<svelte:head><title>Today — OptiMind</title></svelte:head>

{#if loading}
  <div class="card"><p class="muted">Loading…</p></div>
{:else if !authed}
  <div class="card stack">
    <h1>OptiMind</h1>
    <p class="dim">Connect GitHub to read and write your private journal.</p>
    <button class="primary" onclick={() => login()}>Connect GitHub</button>
  </div>
{:else}
  <header class="row-between" style="margin-bottom:var(--s-2);">
    <div>
      <h1>Today</h1>
      <p class="small muted mono">{today} · {now}</p>
    </div>
    <a class="btn ghost small-btn" href="/history">Review 7 days</a>
  </header>

  {#if err}
    <div class="banner safety" style="margin-bottom:var(--s-2);">
      <span class="mono" aria-hidden="true">!</span>
      <div class="grow">
        <strong>Write failed</strong>
        <p class="small dim" style="margin-top:4px;">{err}</p>
        <p class="tiny muted" style="margin-top:4px;">Nothing was reported as logged. Both records are unchanged.</p>
      </div>
    </div>
  {/if}

  <!-- 1. What today still needs. -->
  <section class="card">
    <div class="row-between" style="margin-bottom:var(--s-2);">
      <h2>{captured} of {trackable} captured</h2>
      <StatusBadge state={day?.integrity ?? "unknown"} size="sm" />
    </div>

    <div class="check-grid">
      <button class="check {day?.sleep.quality.value != null ? 'is-done' : 'is-missing'}"
              onclick={() => (capture = CAPTURES.morning)}>
        <span class="glyph">{day?.sleep.quality.value != null ? "✓" : "○"}</span>
        <span class="label">Morning log</span>
        <span class="meta">
          {day?.sleep.wake ?? "—"}{day?.sleep.quality.value != null ? ` · q${day.sleep.quality.value}` : ""}
        </span>
      </button>

      <button class="check {day?.backPain.value != null ? 'is-done' : 'is-missing'}"
              onclick={() => (capture = CAPTURES.back_pain)}>
        <span class="glyph">{day?.backPain.value != null ? "✓" : "○"}</span>
        <span class="label">Back pain</span>
        <span class="meta">{day?.backPain.value != null ? `${day.backPain.value}/5` : "—"}</span>
      </button>

      <button class="check {day?.focus.blocks ? 'is-done' : 'is-missing'}"
              onclick={() => (capture = CAPTURES.focus)}>
        <span class="glyph">{day?.focus.blocks ? "✓" : "○"}</span>
        <span class="label">Focus block</span>
        <span class="meta">{day?.focus.blocks ? `Σ ${day.focus.score}` : "unmeasured"}</span>
      </button>

      {#each day?.routines.filter((r) => r.state !== "not_due") ?? [] as r (r.id)}
        <button class="check {classFor(r.state)} {r.source === 'journal_confirmed' ? 'is-journal' : ''}"
                onclick={() => markRoutine(r.id, r.state === "done" ? "skipped" : "done")}
                title={r.note ?? r.expectedWindow ?? ""}>
          <span class="glyph">{r.source === "journal_confirmed" ? "◑" : glyphFor(r.state)}</span>
          <span class="label">{r.label}</span>
          <span class="meta">{r.time ?? r.expectedWindow ?? ""}</span>
        </button>
      {/each}
    </div>

    <div class="row wrap" style="margin-top:var(--s-2);">
      <button class="small-btn" onclick={() => (capture = CAPTURES.meal)}>+ Meal</button>
      <button class="small-btn" onclick={() => (capture = CAPTURES.caffeine)}>+ Caffeine</button>
      <button class="small-btn" onclick={() => (capture = CAPTURES.workout)}>+ Workout</button>
    </div>
  </section>

  <!-- 2. Integrity, below the fold of today's work. -->
  {#if integrity.repairable || integrity.needsInput}
    <a class="banner integrity" href="/history" style="margin-top:var(--s-2);">
      <span class="mono" aria-hidden="true">◑</span>
      <div class="grow">
        <strong>
          {#if integrity.repairable}
            {integrity.repairable} day{integrity.repairable > 1 ? "s" : ""} recorded in the journal but missing from the structured log
          {:else}
            {integrity.needsInput} day{integrity.needsInput > 1 ? "s" : ""} need a value only you can supply
          {/if}
        </strong>
        <p class="small dim" style="margin-top:4px;">
          {[...integrity.repairableDates, ...integrity.needsInputDates].join(", ")}
          — the data exists in prose. This is a record defect, not a behavior gap.
        </p>
      </div>
      <span class="mono muted" aria-hidden="true">→</span>
    </a>
  {/if}

  <section class="card" style="margin-top:var(--s-2);">
    <div class="section-title">Last 7 days</div>
    <div class="strip">
      {#each [...week].reverse() as d (d.date)}
        <a class="strip-cell" href="/history?date={d.date}" data-state={d.integrity}
           title="{d.date} — {d.integrity}">
          <span class="glyph" aria-hidden="true">
            {d.integrity === "matched" ? "✓" : d.integrity === "in_progress" ? "●"
              : d.integrity === "blackout" || d.integrity === "no_data" ? "—"
              : d.integrity === "needs_input" ? "!" : "◑"}
          </span>
          <span>{d.date.slice(8)}</span>
        </a>
      {/each}
    </div>
    <p class="tiny muted" style="margin-top:var(--s-1);">
      {integrity.matched}/{integrity.closed} closed days consistent.
      Colour is paired with a glyph — ✓ matched, ◑ journal only, ! needs you, — no entry.
    </p>
  </section>

  <div class="row" style="margin-top:var(--s-3);">
    <button class="ghost small-btn" onclick={() => { clearToken(); authed = false; }}>Sign out</button>
  </div>
{/if}

{#if capture}
  <CaptureDrawer spec={capture} {now} {busy}
                 onsubmit={save} onclose={() => (capture = null)} />
{/if}

{#if toast}<div class="toast">{toast}</div>{/if}
