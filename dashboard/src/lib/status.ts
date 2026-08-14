// Journal parsing + integrity classification.
//
// The TypeScript counterpart of optimind-journal/scripts/optimind_core.py. Both
// implement the same spec because both must survive independently: the Python
// engine gates the nightly Reflection and drives the Hermes plugin, this one
// runs in the browser against the GitHub API with no backend. status.test.ts
// pins them together against the same real journal text.
//
// The invariant that matters: an empty JSON field is NEVER evidence that
// something did not happen. If the journal has a Dashboard line for it, the
// write was lost.

import type { DailyLog, RoutineRecord } from "./daily";
import { routineStatus } from "./daily";
import type { IntegrityStatus, RoutineState, SourceStatus } from "./types";

export const LIST_KEYS = ["meals", "caffeine", "snacks", "workouts"] as const;
const LIST_ALIASES: Record<string, string> = { meal: "meals", snack: "snacks", workout: "workouts" };

// Dashboard fields that are planning context, not captured events. Counting
// these would report a permanent divergence on every day that has a protocol.
const NON_LOG_PREFIXES = new Set([
  "protocol", "tomorrow", "state", "profile", "note", "deep_work", "event",
]);

const ENTRY_RE = /^###\s+(\d{2}:\d{2})\s*\|\s*(.+?)\s*$/;
const FACT_RE = /^\[([A-Za-z_][A-Za-z0-9_.]*)\]\s*(.*)$/;

const NOT_REPORTED_RE = /not reported|not stated|unlogged|no answer/i;
const SKIP_RE = /^(skipped|not done|no)\b/i;
const DONE_RE = /^(done|true|yes|completed)\b/i;
const ESTIMATE_RE = /\best\.?\b|estimated|approx|~/i;

export interface JournalEntry {
  time: string;
  role: string;
  lines: string[];
}

export interface DashboardFact {
  time: string;
  field: string;
  raw: string;
  line: number;
}

/** Split a journal file into role-tagged entries. */
export function parseEntries(text: string): JournalEntry[] {
  const entries: JournalEntry[] = [];
  let current: JournalEntry | null = null;
  text.split("\n").forEach((line) => {
    const m = ENTRY_RE.exec(line);
    if (m) {
      current = { time: m[1], role: m[2], lines: [] };
      entries.push(current);
    } else if (current) {
      current.lines.push(line);
    }
  });
  return entries;
}

/**
 * `[field] value` lines from inside Dashboard blocks only.
 *
 * User entries legitimately contain bracketed text — `[attached cafe menu
 * photo]`, pasted timestamps — and a file-wide scan would promote those to
 * structured facts, inventing divergence that does not exist.
 */
export function dashboardFacts(text: string): DashboardFact[] {
  const facts: DashboardFact[] = [];
  let inDashboard = false;
  let time = "";
  text.split("\n").forEach((line, i) => {
    const m = ENTRY_RE.exec(line);
    if (m) {
      inDashboard = m[2].startsWith("Dashboard");
      time = m[1];
      return;
    }
    if (!inDashboard) return;
    const f = FACT_RE.exec(line.trim());
    if (f) facts.push({ time, field: f[1], raw: f[2].trim(), line: i + 1 });
  });
  return facts;
}

export function isLogField(field: string): boolean {
  return !NON_LOG_PREFIXES.has(field.split(".")[0]);
}

/** Fold journal field spellings onto their JSON projection key. */
export function normalizeField(field: string): string {
  const [head, ...rest] = field.split(".");
  if (LIST_ALIASES[head]) return LIST_ALIASES[head];
  if ((LIST_KEYS as readonly string[]).includes(head)) return head;
  return rest.length ? `${head}.${rest.join(".")}` : head;
}

/** Separate a value from a trailing parenthetical. */
export function splitQualifier(raw: string): [string, string | undefined] {
  const m = /^(.*?)\s*\(([^()]*)\)\s*$/.exec(raw);
  if (m && m[1].trim()) return [m[1].trim(), m[2].trim()];
  return [raw.trim(), undefined];
}

export function isEstimate(raw: string): boolean {
  return ESTIMATE_RE.test(raw);
}

/**
 * Map a routine mirror value onto an outcome.
 * `skipped` and `not_reported` stay distinct: the first is something the user
 * told us, the second is that nobody asked. Treating them alike reports
 * failures that never happened.
 */
export function routineStateFromRaw(raw: string): RoutineState {
  const [value] = splitQualifier(raw);
  if (NOT_REPORTED_RE.test(raw)) return "not_reported";
  if (SKIP_RE.test(value)) return "skipped";
  if (DONE_RE.test(value)) return "done";
  return "unknown";
}

/** `3/5` -> [3, 5]; `3` -> [3, undefined]. */
export function parseScore(raw: string): [number | null, number | undefined] {
  const [value] = splitQualifier(raw);
  const m = /^\s*(\d+(?:\.\d+)?)\s*(?:\/\s*(\d+))?/.exec(value);
  if (!m) return [null, undefined];
  return [parseFloat(m[1]), m[2] ? parseInt(m[2], 10) : undefined];
}

/** The facts the JSON projection holds; arrays yield their entry count. */
export function structuredKeys(doc: DailyLog | null): Record<string, number> {
  const out: Record<string, number> = {};
  const log = doc?.log;
  if (!log) return out;
  for (const k of Object.keys(log.sleep ?? {})) out[`sleep.${k}`] = 1;
  for (const group of ["routine", "metrics"] as const) {
    for (const k of Object.keys((log as any)[group] ?? {})) out[`${group}.${k}`] = 1;
  }
  for (const k of LIST_KEYS) {
    const n = ((log as any)[k] ?? []).length;
    if (n) out[k] = n;
  }
  return out;
}

const LEADING_TIME = /^~?\s*([01]?\d|2[0-3]):[0-5]\d/;

/**
 * Split one array mirror line into the entries it actually describes.
 *
 * The writer sometimes batches a whole category onto one line —
 * `[meals] 08:30 breakfast; 13:30 salad; 19:00 salmon` is three meals, not one.
 * Counting lines instead of entries reported those as lost writes.
 *
 * Semicolons inside parentheses do NOT separate entries: `15:00 60mg matcha
 * (native L-theanine; AFTER 14:00 cutoff)` is a single drink. Counting bare
 * times would be wrong too — `18:30-19:30 walk` is a range and
 * `time corrected 09:30 -> 10:30` is one correction.
 */
export function splitEntries(raw: string): string[] {
  const parts: string[] = [];
  let depth = 0;
  let buf = "";
  for (const ch of raw) {
    if (ch === "(") depth++;
    else if (ch === ")") depth = Math.max(0, depth - 1);
    if (ch === ";" && depth === 0) {
      parts.push(buf);
      buf = "";
    } else {
      buf += ch;
    }
  }
  parts.push(buf);

  // Only segments that OPEN with a timestamp are separate entries.
  const timed = parts.map((p) => p.trim()).filter((p) => LEADING_TIME.test(p));
  return timed.length ? timed : [raw.trim()];
}

/** The same key space from Dashboard mirror lines. */
export function journalKeys(facts: DashboardFact[]): Record<string, number> {
  const out: Record<string, number> = {};
  for (const f of facts) {
    if (!isLogField(f.field)) continue;
    const k = normalizeField(f.field);
    const n = (LIST_KEYS as readonly string[]).includes(k) ? splitEntries(f.raw).length : 1;
    out[k] = (out[k] ?? 0) + n;
  }
  return out;
}

/** A mirror line the schema cannot represent — no time, or no dose. */
export function isResolvable(fact: DashboardFact): boolean {
  const key = normalizeField(fact.field);
  const [value] = splitQualifier(fact.raw);
  const hasTime = /\b([01]?\d|2[0-3]):[0-5]\d\b/.test(value);
  if (key === "meals" || key === "snacks" || key === "workouts") return hasTime;
  if (key === "caffeine") return hasTime && /~?\s*\d+(?:\.\d+)?\s*mg/i.test(fact.raw);
  if (key.startsWith("routine.")) return routineStateFromRaw(fact.raw) !== "unknown";
  if (key === "sleep.quality") {
    const [n] = parseScore(fact.raw);
    return n !== null && n >= 1 && n <= 5;
  }
  if (key.startsWith("sleep.")) return hasTime;
  if (key.startsWith("metrics.")) return parseScore(fact.raw)[0] !== null;
  return false;
}

export interface IntegrityResult {
  status: IntegrityStatus;
  journalOnly: string[];
  structuredOnly: string[];
  needsInput: string[];
  matched: string[];
}

/**
 * Compare the two representations of one day.
 *
 * Arrays compare by count — a meal has no stable identity, so three mirror
 * lines against one stored entry means two facts were lost.
 */
export function classifyDay(
  doc: DailyLog | null, journalText: string | null, date: string, today: string,
): IntegrityResult {
  const facts = journalText ? dashboardFacts(journalText) : [];
  const jkeys = journalKeys(facts);
  const skeys = structuredKeys(doc);

  const unresolvable: Record<string, number> = {};
  for (const f of facts) {
    if (!isLogField(f.field) || isResolvable(f)) continue;
    const k = normalizeField(f.field);
    const n = (LIST_KEYS as readonly string[]).includes(k) ? splitEntries(f.raw).length : 1;
    unresolvable[k] = (unresolvable[k] ?? 0) + n;
  }

  const journalOnly: string[] = [];
  const structuredOnly: string[] = [];
  const needsInput: string[] = [];
  const matched: string[] = [];

  for (const key of [...new Set([...Object.keys(jkeys), ...Object.keys(skeys)])].sort()) {
    const jn = jkeys[key] ?? 0;
    const sn = skeys[key] ?? 0;
    const un = unresolvable[key] ?? 0;
    if (jn && sn) matched.push(key);

    if ((LIST_KEYS as readonly string[]).includes(key)) {
      const deficit = jn - sn;
      if (deficit > 0) {
        const blocked = Math.min(un, deficit);
        const repairable = deficit - blocked;
        if (repairable) journalOnly.push(sn || blocked ? `${key}[${repairable}]` : key);
        if (blocked) needsInput.push(`${key}[${blocked}]`);
      } else if (sn > jn) {
        structuredOnly.push(jn ? `${key}[${sn - jn}]` : key);
      }
    } else if (jn && !sn) {
      (un ? needsInput : journalOnly).push(key);
    } else if (sn && !jn) {
      structuredOnly.push(key);
    }
  }

  const userTurns = journalText
    ? parseEntries(journalText).filter((e) => e.role.startsWith("User")).length
    : 0;

  let status: IntegrityStatus;
  if (date >= today) status = "in_progress";
  else if (!Object.keys(jkeys).length && !Object.keys(skeys).length) {
    status = userTurns === 0 ? "blackout" : "no_data";
  } else if (journalOnly.length && structuredOnly.length) status = "mixed";
  else if (journalOnly.length) status = "journal_only";
  else if (structuredOnly.length) status = "structured_only";
  else if (needsInput.length) status = "needs_input";
  else status = "matched";

  return { status, journalOnly, structuredOnly, needsInput, matched };
}

/** True when this day should count against the integrity gate. */
export function isRepairable(r: IntegrityResult, date: string, today: string): boolean {
  return date < today && (r.journalOnly.length > 0 || r.structuredOnly.length > 0);
}

/** Where a routine value came from, for the UI's provenance badge. */
export function sourceOf(record: RoutineRecord | undefined, journalHasIt: boolean): SourceStatus {
  if (record) return record.note && ESTIMATE_RE.test(record.note) ? "estimated" : "json_confirmed";
  return journalHasIt ? "journal_confirmed" : "unknown";
}

export { routineStatus };
