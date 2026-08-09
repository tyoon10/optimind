// Deterministic insight ranking. No model in the loop, no causal claims.
//
// Three rules keep this from becoming another reminder stream:
//   1. At most three active items. A list of nine is a list of none.
//   2. Data-capture items are visually and semantically distinct from health
//      items — "we don't know" must never look like "you failed".
//   3. Language stays observational. `observed`, `coverage`, `open loop` —
//      never "because", never "caused".

import { rollupIntegrity, rollupRoutines, closedDays } from "./analytics";
import type { DaySummary, Insight } from "./types";

const MAX_ACTIVE = 3;

/** Priority bands. Lower sorts first. */
const P = { integrity: 10, safety: 20, measurement: 30, coverage: 40 };

export function buildInsights(days: DaySummary[], today: string): Insight[] {
  const out: Insight[] = [];
  const closed = closedDays(days);
  const integrity = rollupIntegrity(days);

  // 1. Integrity first: until the record is trustworthy, every other number
  //    below is measured against an unknown denominator.
  if (integrity.repairable) {
    const d = integrity.repairableDates;
    out.push({
      id: "integrity-repair",
      kind: "integrity",
      priority: P.integrity,
      title: `${d.length} day${d.length > 1 ? "s" : ""} recorded in the journal but missing from the structured log`,
      evidence: `${d.join(", ")} — the data exists in prose. This is a write defect, not a behavior gap.`,
      action: { label: "Repair", href: "/history?filter=journal_only", date: d[0] },
      sources: d.map((date) => ({ date, path: `journal/${date}.md` })),
    });
  }

  if (integrity.needsInput) {
    const d = integrity.needsInputDates;
    out.push({
      id: "integrity-confirm",
      kind: "integrity",
      priority: P.integrity + 5,
      title: `${d.length} day${d.length > 1 ? "s" : ""} with a partial record only you can complete`,
      evidence: `${d.join(", ")} — the journal states the event but not a time or dose the record needs.`,
      action: { label: "Confirm", href: "/history?filter=needs_input", date: d[0] },
      sources: d.map((date) => ({ date, path: `journal/${date}.md` })),
    });
  }

  // 2. Safety gates. Reported as an open loop, never as a diagnosis.
  const latestPain = [...closed].reverse().find((d) => d.backPain.value != null);
  if (latestPain && (latestPain.backPain.value as number) > 2) {
    out.push({
      id: "safety-pain-gate",
      kind: "safety",
      priority: P.safety,
      title: "Back-pain reading above the strength gate",
      evidence: `Last recorded ${latestPain.backPain.value}/5 on ${latestPain.date}. The protocol gates strength work at 2/5 or below.`,
      action: { label: "Log today's reading", date: today },
      sources: [{ date: latestPain.date, path: `daily/${latestPain.date}.json` }],
    });
  }

  // 3. Measurement dark. Says the metric is unmeasured — NOT that it was zero.
  const focusDays = closed.filter((d) => d.focus.blocks > 0).length;
  if (closed.length >= 3 && focusDays === 0) {
    out.push({
      id: "measure-focus",
      kind: "measurement",
      priority: P.measurement,
      title: "Focus output is unmeasured, not zero",
      evidence: `No focus_* metric in the last ${closed.length} closed days. Σ(quality × hours) cannot be computed — the number is unknown, not 0.`,
      action: { label: "Log a focus block", date: today },
      sources: [],
    });
  }

  // 4. Low-coverage routines, ranked by how much is genuinely unknown.
  const weakest = rollupRoutines(days)
    .filter((r) => r.missing >= 3 && r.done === 0)
    .sort((a, b) => b.missing - a.missing)[0];
  if (weakest) {
    out.push({
      id: `coverage-${weakest.id}`,
      kind: "coverage",
      priority: P.coverage,
      title: `${weakest.label} has no confirmed record in this window`,
      evidence: `${weakest.missing} closed day${weakest.missing > 1 ? "s" : ""} with no entry` +
        (weakest.notReported ? `, plus ${weakest.notReported} where it was never asked about.` : "."),
      action: { label: "Review", href: "/routines" },
      sources: weakest.dates.missing.slice(0, 3).map((date) => ({ date, path: `daily/${date}.json` })),
    });
  }

  return out.sort((a, b) => a.priority - b.priority);
}

const DISMISS_KEY = "optimind_nudge_state";

interface NudgeState {
  [id: string]: { dismissed?: boolean; snoozedUntil?: string };
}

/**
 * Nudge state lives in localStorage, never in the repo.
 *
 * Dismissing a card is a UI preference, not a health record. Persisting it to
 * the journal would put a commit in an audit log whose whole value is that
 * every entry means something happened.
 */
export function readNudgeState(): NudgeState {
  try {
    return JSON.parse(localStorage.getItem(DISMISS_KEY) ?? "{}");
  } catch {
    return {};
  }
}

export function writeNudgeState(state: NudgeState): void {
  try {
    localStorage.setItem(DISMISS_KEY, JSON.stringify(state));
  } catch {
    /* private browsing — the nudge simply reappears next session */
  }
}

export function dismissNudge(id: string): void {
  const s = readNudgeState();
  s[id] = { ...s[id], dismissed: true };
  writeNudgeState(s);
}

export function snoozeNudge(id: string, until: string): void {
  const s = readNudgeState();
  s[id] = { ...s[id], snoozedUntil: until };
  writeNudgeState(s);
}

/** Apply dismiss/snooze, then cap at three. The cap is the whole point. */
export function activeInsights(all: Insight[], today: string, state = readNudgeState()): Insight[] {
  return all
    .filter((i) => {
      const s = state[i.id];
      if (!s) return true;
      if (s.dismissed) return false;
      return !s.snoozedUntil || s.snoozedUntil <= today;
    })
    .slice(0, MAX_ACTIVE);
}
