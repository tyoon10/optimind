// Trends over a window of days.
//
// One rule governs everything here: a missing value stays missing. No
// interpolation, no carry-forward, no dropping gaps so a line looks continuous.
// A chart that smooths over four lost days is how the data layer's failure
// became invisible for a week.

import type { DaySummary, MetricPoint, SourceStatus, TrendSeries } from "./types";

/** Denominator for any coverage claim: closed days only, never today. */
export function closedDays(days: DaySummary[]): DaySummary[] {
  return days.filter((d) => !d.isToday);
}

function direction(points: MetricPoint[]): TrendSeries["direction"] {
  const vals = points.filter((p) => p.value != null).map((p) => p.value as number);
  if (vals.length < 3) return "unknown";
  const half = Math.floor(vals.length / 2);
  const mean = (a: number[]) => a.reduce((x, y) => x + y, 0) / a.length;
  const delta = mean(vals.slice(half)) - mean(vals.slice(0, half));
  if (Math.abs(delta) < 0.25) return "flat";
  return delta > 0 ? "up" : "down";
}

function series(
  id: string, label: string, days: DaySummary[],
  pick: (d: DaySummary) => { value: number | null; source: SourceStatus; note?: string },
  opts: { unit?: string; scale?: number } = {},
): TrendSeries {
  const ordered = [...days].sort((a, b) => a.date.localeCompare(b.date));
  const points: MetricPoint[] = ordered.map((d) => {
    const v = pick(d);
    return { date: d.date, value: v.value, source: v.source, note: v.note };
  });
  const closed = closedDays(ordered);
  const present = closed.filter((d) => pick(d).value != null).length;
  const withValue = points.filter((p) => p.value != null);
  return {
    id, label, unit: opts.unit, scale: opts.scale, points,
    coverage: { present, closed: closed.length },
    direction: direction(points),
    latest: withValue.length ? (withValue[withValue.length - 1].value as number) : null,
  };
}

export function buildTrends(days: DaySummary[]): TrendSeries[] {
  return [
    series("sleep_quality", "Sleep quality", days,
      (d) => ({ value: d.sleep.quality.value, source: d.sleep.quality.source, note: d.sleep.quality.note }),
      { scale: 5 }),
    series("back_pain", "Back pain", days,
      (d) => ({ value: d.backPain.value, source: d.backPain.source, note: d.backPain.note }),
      { scale: 5 }),
    series("focus_score", "Focus output", days,
      (d) => ({ value: d.focus.blocks ? d.focus.score : null, source: d.focus.source }),
      { unit: "q x h" }),
    series("coverage", "Record coverage", days,
      (d) => ({
        value: d.coverage.expected ? Math.round((d.coverage.captured / d.coverage.expected) * 100) : null,
        source: "json_confirmed",
      }),
      { unit: "%" }),
  ];
}

export interface RoutineRollup {
  id: string;
  label: string;
  done: number;
  skipped: number;
  notReported: number;
  missing: number;
  notDue: number;
  /** Closed days where the outcome is actually known. */
  confidence: number;
  dates: { done: string[]; missing: string[]; skipped: string[] };
}

/**
 * Per-routine counts, with every state kept separate.
 *
 * `done / (done + missing)` would be the tempting number, but it silently
 * treats `not_reported` as a failure. Compliance is reported against days where
 * the outcome is known, and the unknown count stays visible beside it.
 */
export function rollupRoutines(days: DaySummary[]): RoutineRollup[] {
  const closed = closedDays(days);
  const byId = new Map<string, RoutineRollup>();

  for (const day of closed) {
    for (const r of day.routines) {
      let row = byId.get(r.id);
      if (!row) {
        row = {
          id: r.id, label: r.label, done: 0, skipped: 0, notReported: 0,
          missing: 0, notDue: 0, confidence: 0,
          dates: { done: [], missing: [], skipped: [] },
        };
        byId.set(r.id, row);
      }
      if (r.state === "done") { row.done++; row.dates.done.push(day.date); }
      else if (r.state === "skipped") { row.skipped++; row.dates.skipped.push(day.date); }
      else if (r.state === "not_reported") row.notReported++;
      else if (r.state === "missing") { row.missing++; row.dates.missing.push(day.date); }
      else if (r.state === "not_due") row.notDue++;
    }
  }

  for (const row of byId.values()) {
    const known = row.done + row.skipped + row.missing;
    row.confidence = known + row.notReported ? known / (known + row.notReported) : 0;
  }
  return [...byId.values()].sort((a, b) => b.done + b.missing - (a.done + a.missing));
}

export interface IntegrityRollup {
  closed: number;
  matched: number;
  repairable: number;
  needsInput: number;
  blackout: number;
  repairableDates: string[];
  needsInputDates: string[];
}

export function rollupIntegrity(days: DaySummary[]): IntegrityRollup {
  const closed = closedDays(days);
  const repairableDates = closed
    .filter((d) => d.integrity === "journal_only" || d.integrity === "structured_only" || d.integrity === "mixed")
    .map((d) => d.date);
  const needsInputDates = closed.filter((d) => d.needsInput.length).map((d) => d.date);
  return {
    closed: closed.length,
    matched: closed.filter((d) => d.integrity === "matched").length,
    repairable: repairableDates.length,
    needsInput: needsInputDates.length,
    blackout: closed.filter((d) => d.integrity === "blackout").length,
    repairableDates,
    needsInputDates,
  };
}
