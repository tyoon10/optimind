// Range loading and day summaries.
//
// Bounded and cached on purpose: the journal is a private repo reached over the
// GitHub API, and fetching 90 days of Markdown on first paint would burn the
// rate limit and stall the first render. Recent days load first; older windows
// load on demand and stay cached for the session.

import { getFile, type RepoRef } from "./github";
import { routineStatus, type DailyLog, type RoutineRecord } from "./daily";
import { classifyDay, dashboardFacts, isLogField, normalizeField, splitQualifier, type DashboardFact } from "./status";
import type { DaySummary, MetricSummary, RoutineState, RoutineStatus, SourceStatus } from "./types";

export interface DayRecord {
  date: string;
  doc: DailyLog | null;
  journal: string | null;
  facts: DashboardFact[];
}

const cache = new Map<string, DayRecord>();

export function clearCache(): void {
  cache.clear();
}

export function shiftDate(date: string, days: number): string {
  const d = new Date(`${date}T12:00:00Z`);
  d.setUTCDate(d.getUTCDate() + days);
  return d.toISOString().slice(0, 10);
}

/** The last `n` dates ending at `end`, most recent first. */
export function recentDates(end: string, n: number): string[] {
  return Array.from({ length: n }, (_, i) => shiftDate(end, -i));
}

async function loadDay(ref: RepoRef, date: string): Promise<DayRecord> {
  const hit = cache.get(date);
  if (hit) return hit;
  const [d, j] = await Promise.all([
    getFile(ref, `daily/${date}.json`).catch(() => ({ text: null, sha: null })),
    getFile(ref, `journal/${date}.md`).catch(() => ({ text: null, sha: null })),
  ]);
  let doc: DailyLog | null = null;
  try {
    doc = d.text ? (JSON.parse(d.text) as DailyLog) : null;
  } catch {
    doc = null; // a corrupt file is a real state; render it as absent, don't crash
  }
  const rec: DayRecord = {
    date, doc, journal: j.text, facts: j.text ? dashboardFacts(j.text) : [],
  };
  cache.set(date, rec);
  return rec;
}

/** Load a set of dates with bounded concurrency. */
export async function loadRange(
  ref: RepoRef, dates: string[], concurrency = 6,
): Promise<DayRecord[]> {
  const out: DayRecord[] = [];
  for (let i = 0; i < dates.length; i += concurrency) {
    out.push(...await Promise.all(dates.slice(i, i + concurrency).map((d) => loadDay(ref, d))));
  }
  return out;
}

/** Today's record, always refetched — it changes while you are looking at it. */
export async function refreshDay(ref: RepoRef, date: string): Promise<DayRecord> {
  cache.delete(date);
  return loadDay(ref, date);
}

const ROUTINE_LABELS: Record<string, string> = {
  morning_log: "Morning log", sunlight: "Sunlight", cold_shower: "Cold shower",
  workout: "Workout", supplements_breakfast: "AM supplements", am_supplements: "AM supplements",
  creatine: "Creatine", meditation: "Meditation", caffeine: "Caffeine", deep_work: "Deep work",
  lunch: "Lunch", dinner: "Dinner", zinc: "Zinc", zinc_dinner: "Zinc (dinner)",
  mg_stack: "Magnesium", magnesium_bedtime: "Magnesium", wind_down: "Wind-down",
  lights_out: "Lights out", post_lunch_walk: "Post-lunch walk", reading_block: "Reading",
};

export function routineLabel(id: string): string {
  return ROUTINE_LABELS[id] ?? id.replace(/_/g, " ").replace(/^./, (c) => c.toUpperCase());
}

/** Minutes past midnight, for deciding whether a window has passed. */
function minutes(hhmm: string): number {
  const [h, m] = hhmm.split(":").map(Number);
  return h * 60 + m;
}

/**
 * Resolve one routine's outcome.
 *
 * The important branch is the last one: on a day still in progress, an item
 * whose window has not arrived is `scheduled`, not `missing`. Marking it
 * missing at 09:00 for a 21:15 magnesium dose is how a checklist teaches you
 * to ignore it.
 */
function resolveRoutine(
  id: string, record: RoutineRecord | undefined, journalFact: DashboardFact | undefined,
  expectedWindow: string | undefined, isToday: boolean, nowHHMM: string,
): RoutineStatus {
  const base = { id, label: routineLabel(id), expectedWindow };
  const stored = routineStatus(record);

  if (stored) {
    return {
      ...base, state: stored as RoutineState, time: record?.time,
      note: record?.note, count: record?.count,
      source: record?.note && /est\.?|estimated|approx/i.test(record.note) ? "estimated" : "json_confirmed",
    };
  }

  if (journalFact) {
    // In the journal but not the JSON: real, but the structured write lost it.
    const [value] = splitQualifier(journalFact.raw);
    const state: RoutineState = /not reported|not stated/i.test(journalFact.raw)
      ? "not_reported"
      : /^(skipped|not done)/i.test(value) ? "skipped" : "done";
    return { ...base, state, source: "journal_confirmed", note: "in journal only — structured write lost it" };
  }

  if (!expectedWindow) return { ...base, state: "not_due", source: "unknown" };
  if (isToday) {
    const end = expectedWindow.includes("-") ? expectedWindow.split("-")[1] : expectedWindow;
    if (minutes(nowHHMM) < minutes(end)) return { ...base, state: "scheduled", source: "unknown" };
  }
  return { ...base, state: "missing", source: "unknown" };
}

function metricFrom(
  doc: DailyLog | null, id: string, facts: DashboardFact[],
): MetricSummary {
  const m = doc?.log?.metrics?.[id];
  if (m) {
    return {
      value: m.value, scale: m.scale, time: m.time, note: m.note,
      source: m.note && /est\.?|estimated/i.test(m.note) ? "estimated" : "json_confirmed",
    };
  }
  const fact = facts.find((f) => normalizeField(f.field) === `metrics.${id}`);
  if (fact) {
    const [value] = splitQualifier(fact.raw);
    const n = parseFloat(value);
    return {
      value: Number.isFinite(n) ? n : null, scale: 5,
      source: "journal_confirmed", note: "in journal only — structured write lost it",
    };
  }
  return { value: null, source: "unknown" };
}

/** Σ(quality × hours) across the day's focus_* metrics. */
function focusFrom(doc: DailyLog | null): DaySummary["focus"] {
  const metrics = doc?.log?.metrics ?? {};
  const blocks = Object.entries(metrics).filter(([k]) => k.startsWith("focus_"));
  let totalMinutes = 0;
  let score = 0;
  for (const [, m] of blocks) {
    const mins = parseInt(/(\d+)\s*min/i.exec(m.note ?? "")?.[1] ?? "0", 10);
    totalMinutes += mins;
    score += (m.value ?? 0) * (mins / 60);
  }
  return {
    totalMinutes, blocks: blocks.length,
    score: Math.round(score * 100) / 100,
    source: blocks.length ? "json_confirmed" : "unknown",
  };
}

export function buildSummary(rec: DayRecord, today: string, nowHHMM: string): DaySummary {
  const integrity = classifyDay(rec.doc, rec.journal, rec.date, today);
  const isToday = rec.date === today;
  const log = rec.doc?.log;

  const protocolIds = (rec.doc?.protocol?.items ?? []).map((i) => i.id);
  const loggedIds = Object.keys(log?.routine ?? {});
  const journalRoutineIds = rec.facts
    .filter((f) => isLogField(f.field) && normalizeField(f.field).startsWith("routine."))
    .map((f) => normalizeField(f.field).slice("routine.".length));
  const ids = [...new Set([...protocolIds, ...loggedIds, ...journalRoutineIds])];

  const routines = ids.map((id) =>
    resolveRoutine(
      id,
      log?.routine?.[id],
      rec.facts.find((f) => normalizeField(f.field) === `routine.${id}`),
      rec.doc?.protocol?.items?.find((i) => i.id === id)?.expected_window,
      isToday, nowHHMM,
    ),
  );

  const sleepFact = (k: string) => rec.facts.find((f) => normalizeField(f.field) === `sleep.${k}`);
  const quality = log?.sleep?.quality;
  const qualityFact = sleepFact("quality");

  const captured = Object.keys({ ...integrity.matched.reduce((a, k) => ({ ...a, [k]: 1 }), {}) }).length;
  const expected = captured + integrity.journalOnly.length + integrity.needsInput.length;

  return {
    date: rec.date,
    isToday,
    integrity: integrity.status,
    journalOnly: integrity.journalOnly,
    needsInput: integrity.needsInput,
    structuredOnly: integrity.structuredOnly,
    routines,
    sleep: {
      bedtime: log?.sleep?.bedtime ?? (sleepFact("bedtime") ? splitQualifier(sleepFact("bedtime")!.raw)[0] : undefined),
      wake: log?.sleep?.wake_time ?? (sleepFact("wake_time") ? splitQualifier(sleepFact("wake_time")!.raw)[0] : undefined),
      quality: quality != null
        ? { value: quality, scale: 5, source: "json_confirmed" }
        : qualityFact
          ? { value: parseFloat(splitQualifier(qualityFact.raw)[0]) || null, scale: 5, source: "journal_confirmed" }
          : { value: null, scale: 5, source: "unknown" },
    },
    backPain: metricFrom(rec.doc, "back_pain", rec.facts),
    focus: focusFrom(rec.doc),
    coverage: { captured, expected },
    userTurns: rec.journal ? (rec.journal.match(/^###\s+\d{2}:\d{2}\s*\|\s*User/gm) ?? []).length : 0,
    hasJournal: rec.journal !== null,
    hasDaily: rec.doc !== null,
  };
}

export async function loadSummaries(
  ref: RepoRef, dates: string[], today: string, nowHHMM: string,
): Promise<DaySummary[]> {
  return (await loadRange(ref, dates)).map((r) => buildSummary(r, today, nowHHMM));
}
