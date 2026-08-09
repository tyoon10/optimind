// View models for every dashboard surface.
//
// Status logic lives here and in status.ts, never scattered through components,
// so a day cannot render as `missing` on Overview and `journal_only` in History.
// The vocabulary matches optimind-journal/scripts/optimind_core.py exactly —
// status.test.ts cross-checks both against the same real journal fixtures.

/** How the two records relate for a whole day. */
export type IntegrityStatus =
  | "matched"          // both records agree
  | "journal_only"     // the journal has it, the JSON lost it — a WRITE DEFECT
  | "structured_only"  // the JSON has it, the audit log never recorded it
  | "mixed"            // divergence in both directions
  | "needs_input"      // the journal line is incomplete; no rerun can fix it
  | "blackout"         // no turn occurred, nothing was captured
  | "no_data"          // turns occurred but produced no structured fact
  | "in_progress";     // the current NYC day — never counted as a miss

/** Outcome of one routine item. */
export type RoutineState =
  | "done"
  | "skipped"       // the user said they didn't — a real observation
  | "not_reported"  // nobody asked, or no answer came — NOT a miss
  | "missing"       // was due, the day closed, nothing was said
  | "not_due"       // not scheduled today
  | "scheduled"     // due later today
  | "unknown";

/** Whether a value can be trusted, and how it got here. */
export type SourceStatus =
  | "json_confirmed"      // in the structured record
  | "journal_confirmed"   // only in the journal — real, but the JSON lost it
  | "estimated"           // inferred from a description, not stated
  | "backfilled"          // reconstructed from journal evidence after the fact
  | "unknown";

export interface SourceRef {
  date: string;
  path: string;
  line?: number;
  time?: string;
}

export interface MetricSummary {
  value: number | null;
  scale?: number;
  unit?: string;
  source: SourceStatus;
  note?: string;
  time?: string;
}

export interface RoutineStatus {
  id: string;
  label: string;
  state: RoutineState;
  expectedWindow?: string;
  time?: string;
  source: SourceStatus;
  note?: string;
  count?: number;
}

export interface DaySummary {
  date: string;
  isToday: boolean;
  integrity: IntegrityStatus;
  /** Fields the journal has and the JSON lost — repairable by reconciliation. */
  journalOnly: string[];
  /** Fields the journal states incompletely — repairable only by the user. */
  needsInput: string[];
  structuredOnly: string[];
  routines: RoutineStatus[];
  sleep: { bedtime?: string; wake?: string; quality: MetricSummary };
  backPain: MetricSummary;
  focus: { totalMinutes: number; blocks: number; score: number; source: SourceStatus };
  /** Structured fields present, over fields the day had evidence for. */
  coverage: { captured: number; expected: number };
  userTurns: number;
  hasJournal: boolean;
  hasDaily: boolean;
}

export interface MetricPoint {
  date: string;
  value: number | null;   // null is a real gap — never interpolate it away
  source: SourceStatus;
  note?: string;
}

export interface TrendSeries {
  id: string;
  label: string;
  unit?: string;
  scale?: number;
  points: MetricPoint[];
  /** Days with a value, over closed days in the window. */
  coverage: { present: number; closed: number };
  direction: "up" | "down" | "flat" | "unknown";
  latest: number | null;
}

export type InsightKind = "integrity" | "measurement" | "safety" | "coverage";

export interface Insight {
  id: string;
  kind: InsightKind;
  priority: number;
  title: string;
  /** What was observed. Never a causal claim. */
  evidence: string;
  action?: { label: string; href?: string; date?: string };
  sources: SourceRef[];
}

/** One field being backfilled, with the journal evidence behind it. */
export interface BackfillField {
  field: string;
  label: string;
  value: unknown;
  state: "value" | "skipped" | "not_reported";
  evidence?: string;
  isEstimate: boolean;
  error?: string;
}

export interface BackfillDraft {
  date: string;
  fields: BackfillField[];
  errors: string[];
}
