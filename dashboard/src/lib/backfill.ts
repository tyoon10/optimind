// Turning journal evidence into a backfill draft.
//
// The rule that shapes everything: prefill only what the evidence supports. A
// suggestion the journal does not state must arrive marked as an estimate and
// require an explicit confirmation, because six months from now an inferred
// 12:30 lunch is indistinguishable from a measured one.

import { isResolvable, normalizeField, parseScore, routineStateFromRaw, splitQualifier, type DashboardFact } from "./status";
import { routineLabel } from "./history";
import type { FieldWrite } from "./writeDaily";
import type { BackfillDraft, BackfillField } from "./types";

const TIME_RE = /\b([01]?\d|2[0-3]):([0-5]\d)\b/;
const MG_RE = /~?\s*(\d+(?:\.\d+)?)\s*mg/i;

/** Caffeine defaults from the capture contract — offered, never auto-applied. */
const CAFFEINE_HINTS: Array<[RegExp, number]> = [
  [/cold brew/i, 205],
  [/espresso|latte|cappuccino|americano/i, 65],
  [/black coffee|drip|brewed|iced coffee|coffee/i, 95],
  [/matcha|green tea|black tea|\btea\b/i, 47],
];

function estimateMg(text: string): number | undefined {
  return CAFFEINE_HINTS.find(([re]) => re.test(text))?.[1];
}

function parseTime(raw: string): string | undefined {
  const m = TIME_RE.exec(raw);
  return m ? `${m[1].padStart(2, "0")}:${m[2]}` : undefined;
}

function labelFor(field: string): string {
  if (field.startsWith("routine.")) return routineLabel(field.slice(8));
  return {
    "sleep.bedtime": "Bedtime", "sleep.wake_time": "Wake time", "sleep.quality": "Sleep quality",
    "metrics.back_pain": "Back pain", meals: "Meal", snacks: "Snack",
    caffeine: "Caffeine", workouts: "Workout",
  }[field] ?? field;
}

/**
 * Build a draft from the Dashboard lines a day's JSON never received.
 *
 * `missingKeys` comes from the integrity classification, so the draft covers
 * exactly the fields that diverged — never the whole day.
 */
export function draftFromEvidence(
  date: string, facts: DashboardFact[], missingKeys: string[],
): BackfillDraft {
  const wanted = new Set(missingKeys.map((k) => k.replace(/\[\d+\]$/, "")));
  const fields: BackfillField[] = [];

  for (const fact of facts) {
    const key = normalizeField(fact.field);
    if (!wanted.has(key)) continue;

    const [value, qualifier] = splitQualifier(fact.raw);
    const resolvable = isResolvable(fact);
    const evidence = `[${fact.field}] ${fact.raw}`;
    const base = { field: key, label: labelFor(key), evidence, state: "value" as const };

    if (key.startsWith("routine.")) {
      const st = routineStateFromRaw(fact.raw);
      fields.push({
        ...base,
        value: { status: st, ...(parseTime(value) ? { time: parseTime(value) } : {}), ...(qualifier ? { note: qualifier } : {}) },
        state: st === "not_reported" ? "not_reported" : st === "skipped" ? "skipped" : "value",
        isEstimate: false,
      });
      continue;
    }

    if (key === "sleep.quality") {
      const [n] = parseScore(fact.raw);
      fields.push({ ...base, value: n, isEstimate: false, error: n == null ? "no readable score" : undefined });
      continue;
    }

    if (key.startsWith("sleep.")) {
      fields.push({ ...base, value: parseTime(value), isEstimate: false });
      continue;
    }

    if (key.startsWith("metrics.")) {
      const [n, scale] = parseScore(fact.raw);
      fields.push({
        ...base,
        value: n == null ? null : { value: n, ...(scale ? { scale } : {}), ...(qualifier ? { note: qualifier } : {}) },
        isEstimate: false,
      });
      continue;
    }

    if (key === "meals" || key === "snacks") {
      const time = parseTime(value);
      fields.push({
        ...base,
        value: { time, items: value.replace(TIME_RE, "").trim().replace(/^[,:]\s*/, "") },
        isEstimate: !resolvable,
        error: time ? undefined : "the journal never states a time",
      });
      continue;
    }

    if (key === "caffeine") {
      const time = parseTime(value);
      const stated = MG_RE.exec(fact.raw);
      const mg = stated ? Number(stated[1]) : estimateMg(fact.raw);
      fields.push({
        ...base,
        value: { time, amount_mg: mg, source: value.replace(TIME_RE, "").replace(MG_RE, "").trim().replace(/^[,:]\s*/, "") },
        isEstimate: !stated,
        error: time ? undefined : "the journal never states a time",
      });
      continue;
    }

    if (key === "workouts") {
      const time = parseTime(value);
      const mins = /(\d+)\s*min/i.exec(value);
      fields.push({
        ...base,
        value: { time, ...(mins ? { duration_min: Number(mins[1]) } : {}), source: value.replace(TIME_RE, "").trim() },
        isEstimate: !resolvable,
        error: time ? undefined : "the journal never states a time",
      });
    }
  }

  return { date, fields, errors: [] };
}

/** Validate, then flatten a draft into writes for ONE pair commit. */
export function draftToWrites(draft: BackfillDraft): { writes: FieldWrite[]; errors: string[] } {
  const writes: FieldWrite[] = [];
  const errors: string[] = [];

  for (const f of draft.fields) {
    if (f.error) {
      errors.push(`${f.label}: ${f.error}`);
      continue;
    }
    if (f.state === "not_reported" || f.state === "skipped") {
      writes.push({ field: f.field, value: { status: f.state }, time: undefined });
      continue;
    }
    const v: any = f.value;
    if (v == null || (typeof v === "object" && Object.values(v).every((x) => x == null))) {
      errors.push(`${f.label}: no value`);
      continue;
    }
    if (f.field === "sleep.quality" && (typeof v !== "number" || v < 1 || v > 5)) {
      errors.push(`${f.label}: must be 1–5`);
      continue;
    }
    if ((f.field === "meals" || f.field === "caffeine" || f.field === "workouts") && !v.time) {
      errors.push(`${f.label}: needs a time`);
      continue;
    }
    if (f.field === "caffeine" && (v.amount_mg == null || Number.isNaN(v.amount_mg))) {
      errors.push(`${f.label}: needs an amount in mg`);
      continue;
    }

    const note = f.isEstimate
      ? [v?.note, "estimated during backfill"].filter(Boolean).join("; ")
      : v?.note;

    writes.push({
      field: f.field,
      value: typeof v === "object" ? { ...v, ...(note ? { note } : {}) } : v,
      time: typeof v === "object" ? v.time : undefined,
    });
  }

  return { writes, errors };
}
