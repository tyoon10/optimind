// Pure daily-log logic — the TS mirror of optimind-sdk/src/tools/daily.py (do_log_field).
// Kept free of network/Svelte so it can be unit-tested. Shape = daily_log.schema.json.

export const SCHEMA_VERSION = "1.0";
export const TZ_NAME = "America/New_York";

// Event categories are arrays (append); everything else is a scalar/object set.
const LIST_KEYS = new Set(["meals", "caffeine", "snacks", "workouts"]);
const LIST_ALIASES: Record<string, string> = { meal: "meals", snack: "snacks", workout: "workouts" };

export interface ProtocolItem {
  id: string;
  expected_window?: string;
  duration_min?: number;
  type?: string;
}
export interface DailyLog {
  schema_version: string;
  date: string;
  tz: string;
  protocol?: { generated_at: string; source: string; items: ProtocolItem[] };
  log?: {
    sleep?: { bedtime?: string; wake_time?: string; quality?: number };
    meals?: Array<{ time: string; items: string }>;
    snacks?: Array<{ time: string; items: string }>;
    caffeine?: Array<{ time: string; amount_mg: number; source?: string }>;
    routine?: Record<string, { done: boolean; time?: string; duration_min?: number }>;
    workouts?: Array<{ time: string; duration_min?: number; type?: string }>;
  };
}

/** Today's date in America/New_York (matches the journal filename). */
export function todayNYC(now: Date = new Date()): string {
  // en-CA gives YYYY-MM-DD; timeZone forces NYC regardless of the runtime's zone.
  return new Intl.DateTimeFormat("en-CA", { timeZone: TZ_NAME }).format(now);
}

/** Current HH:MM in NYC (24h). */
export function nowHHMM(now: Date = new Date()): string {
  return new Intl.DateTimeFormat("en-GB", {
    timeZone: TZ_NAME, hour: "2-digit", minute: "2-digit", hourCycle: "h23",
  }).format(now);
}

/** ISO-8601 timestamp in NYC WITH numeric offset (never bare 'Z') — schema-valid for protocol.generated_at. */
export function nowOffsetISO(now: Date = new Date()): string {
  const parts = Object.fromEntries(
    new Intl.DateTimeFormat("en-US", {
      timeZone: TZ_NAME, hourCycle: "h23", timeZoneName: "longOffset",
      year: "numeric", month: "2-digit", day: "2-digit",
      hour: "2-digit", minute: "2-digit", second: "2-digit",
    }).formatToParts(now).map((p) => [p.type, p.value]),
  );
  const offset = (parts.timeZoneName as string).replace("GMT", "") || "+00:00"; // e.g. "-04:00"
  return `${parts.year}-${parts.month}-${parts.day}T${parts.hour}:${parts.minute}:${parts.second}${offset}`;
}

export function newDoc(date: string): DailyLog {
  return { schema_version: SCHEMA_VERSION, date, tz: TZ_NAME };
}

function listKey(field: string): string | null {
  const head = (field.startsWith("log.") ? field.slice(4) : field).split(".")[0];
  const norm = LIST_ALIASES[head] ?? head;
  return LIST_KEYS.has(norm) ? norm : null;
}

function setPath(obj: Record<string, any>, parts: string[], value: unknown): void {
  let cur = obj;
  for (const p of parts.slice(0, -1)) {
    if (typeof cur[p] !== "object" || cur[p] === null) cur[p] = {};
    cur = cur[p];
  }
  cur[parts[parts.length - 1]] = value;
}

/**
 * Apply one field to the daily doc, mirroring daily.py:apply_field.
 * Event categories append (with `time` injected if absent); scalars/routine are path-sets.
 * Returns the value as stored, so the journal mirror reflects the JSON exactly.
 */
export function applyField(doc: DailyLog, field: string, value: any, time: string): any {
  const f = field.startsWith("log.") ? field.slice(4) : field;
  const log = (doc.log ??= {}) as Record<string, any>;
  const lk = listKey(field);
  if (lk) {
    let entry = value && typeof value === "object" ? { ...value } : { value };
    if (time && !("time" in entry)) entry = { time, ...entry };
    (log[lk] ??= []).push(entry);
    return entry;
  }
  setPath(log, f.split("."), value);
  return value;
}

/** Human, greppable rendering for the journal mirror line (mirrors daily.py:render_value). */
export function renderValue(value: any): string {
  if (typeof value === "boolean") return value ? "true" : "false";
  if (Array.isArray(value)) return value.map(renderValue).join(" ");
  if (value && typeof value === "object") return Object.values(value).map(renderValue).join(" ");
  return String(value);
}

/** The Dashboard mirror line appended to journal/<date>.md (mirrors append_dashboard_line). */
export function mirrorLine(time: string, field: string, rendered: string): string {
  return `\n### ${time} | Dashboard\n[${field}] ${rendered}\n`;
}
