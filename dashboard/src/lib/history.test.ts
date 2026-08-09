import { describe, expect, it } from "vitest";
import { buildSummary, recentDates, routineLabel, shiftDate, type DayRecord } from "./history";
import { buildTrends, closedDays, rollupIntegrity, rollupRoutines } from "./analytics";
import { activeInsights, buildInsights } from "./insights";
import { dashboardFacts } from "./status";
import type { DailyLog } from "./daily";

const TODAY = "2026-01-15";

function rec(date: string, log: any, journal = ""): DayRecord {
  const doc: DailyLog | null = log === null ? null : {
    schema_version: "1.1", date, tz: "America/New_York",
    protocol: {
      generated_at: `${date}T05:55:00-04:00`, source: "rule_derived",
      items: [
        { id: "sunlight", expected_window: "06:00-06:20" },
        { id: "mg_stack", expected_window: "21:15-21:30" },
      ],
    },
    log,
  };
  return { date, doc, journal: journal || null, facts: journal ? dashboardFacts(journal) : [] };
}

const summary = (r: DayRecord, now = "23:00") => buildSummary(r, TODAY, now);

describe("day summary", () => {
  it("marks a journal-only day as a write defect, not missing behavior", () => {
    const s = summary(rec("2026-01-10", {}, "### 22:00 | Dashboard\n[routine.sunlight] done\n"));
    expect(s.integrity).toBe("journal_only");
    const sunlight = s.routines.find((r) => r.id === "sunlight")!;
    expect(sunlight.state).toBe("done");                    // NOT missing
    expect(sunlight.source).toBe("journal_confirmed");
  });

  it("keeps skipped and not_reported distinct on the checklist", () => {
    const s = summary(rec("2026-01-10", {
      routine: { sunlight: { status: "skipped" }, mg_stack: { status: "not_reported" } },
    }, "### 22:00 | Dashboard\n[routine.sunlight] SKIPPED\n[routine.mg_stack] not reported\n"));
    expect(s.routines.find((r) => r.id === "sunlight")!.state).toBe("skipped");
    expect(s.routines.find((r) => r.id === "mg_stack")!.state).toBe("not_reported");
  });

  it("reads the legacy done boolean from 1.0 records", () => {
    const s = summary(rec("2026-01-10", { routine: { sunlight: { done: true, time: "06:10" } } },
      "### 22:00 | Dashboard\n[routine.sunlight] done 06:10\n"));
    expect(s.routines.find((r) => r.id === "sunlight")!.state).toBe("done");
  });

  it("calls an unfired window scheduled today, missing once the day closes", () => {
    const live = buildSummary(rec(TODAY, {}), TODAY, "09:00");
    expect(live.routines.find((r) => r.id === "mg_stack")!.state).toBe("scheduled");

    const closed = buildSummary(rec("2026-01-10", {}), TODAY, "09:00");
    expect(closed.routines.find((r) => r.id === "mg_stack")!.state).toBe("missing");
  });

  it("does not mark a passed window scheduled later the same day", () => {
    const s = buildSummary(rec(TODAY, {}), TODAY, "23:00");
    expect(s.routines.find((r) => r.id === "sunlight")!.state).toBe("missing");
  });

  it("badges an estimated value differently from an observed one", () => {
    const s = summary(rec("2026-01-10", {
      metrics: { back_pain: { value: 2, scale: 5, note: "estimated from description" } },
    }, "### 22:00 | Dashboard\n[metrics.back_pain] 2/5\n"));
    expect(s.backPain.source).toBe("estimated");
  });

  it("computes focus as quality x hours and reports zero blocks as unknown", () => {
    const withFocus = summary(rec("2026-01-10", {
      metrics: { focus_morning: { value: 4, scale: 5, note: "120min — proofs" } },
    }));
    expect(withFocus.focus.score).toBe(8);
    expect(withFocus.focus.totalMinutes).toBe(120);

    expect(summary(rec("2026-01-10", {})).focus.source).toBe("unknown");
  });

  it("survives a corrupt daily file instead of crashing the view", () => {
    const s = summary(rec("2026-01-10", null, "### 22:00 | Dashboard\n[sleep.quality] 3/5\n"));
    expect(s.hasDaily).toBe(false);
    expect(s.integrity).toBe("journal_only");
  });
});

describe("ranges", () => {
  it("walks dates backwards across a month boundary", () => {
    expect(recentDates("2026-01-02", 3)).toEqual(["2026-01-02", "2026-01-01", "2025-12-31"]);
    expect(shiftDate("2026-03-01", -1)).toBe("2026-02-28");
  });

  it("uses closed days as the denominator, never today", () => {
    const days = [summary(rec("2026-01-14", {})), buildSummary(rec(TODAY, {}), TODAY, "09:00")];
    expect(closedDays(days)).toHaveLength(1);
  });
});

describe("trends", () => {
  const days = [
    summary(rec("2026-01-12", { sleep: { quality: 3 } })),
    summary(rec("2026-01-13", {})),                          // a real gap
    summary(rec("2026-01-14", { sleep: { quality: 4 } })),
  ];

  it("preserves gaps instead of interpolating them", () => {
    const s = buildTrends(days).find((t) => t.id === "sleep_quality")!;
    expect(s.points.map((p) => p.value)).toEqual([3, null, 4]);
  });

  it("reports coverage against closed days", () => {
    const s = buildTrends(days).find((t) => t.id === "sleep_quality")!;
    expect(s.coverage).toEqual({ present: 2, closed: 3 });
  });

  it("returns the last real value as latest, not the last slot", () => {
    const s = buildTrends([...days, summary(rec("2026-01-14", {}))])
      .find((t) => t.id === "sleep_quality")!;
    expect(s.latest).toBe(4);
  });
});

describe("routine rollup", () => {
  it("counts every state separately rather than collapsing to a ratio", () => {
    const days = [
      summary(rec("2026-01-12", { routine: { sunlight: { status: "done" } } })),
      summary(rec("2026-01-13", { routine: { sunlight: { status: "skipped" } } })),
      summary(rec("2026-01-14", { routine: { sunlight: { status: "not_reported" } } })),
    ];
    const row = rollupRoutines(days).find((r) => r.id === "sunlight")!;
    expect(row).toMatchObject({ done: 1, skipped: 1, notReported: 1 });
    expect(row.confidence).toBeCloseTo(2 / 3);
  });

  it("keeps the dates behind each count for drill-down", () => {
    const days = [summary(rec("2026-01-12", { routine: { sunlight: { status: "done" } } }))];
    expect(rollupRoutines(days).find((r) => r.id === "sunlight")!.dates.done).toEqual(["2026-01-12"]);
  });
});

describe("insights", () => {
  const journalOnly = summary(rec("2026-01-12", {}, "### 22:00 | Dashboard\n[sleep.quality] 3/5\n"));

  it("ranks integrity repair above everything else", () => {
    const items = buildInsights([journalOnly], TODAY);
    expect(items[0].kind).toBe("integrity");
  });

  it("says focus is unmeasured, never that it was zero", () => {
    const days = ["2026-01-12", "2026-01-13", "2026-01-14"].map((d) => summary(rec(d, { sleep: { quality: 3 } })));
    const focus = buildInsights(days, TODAY).find((i) => i.id === "measure-focus")!;
    expect(focus.title).toMatch(/unmeasured, not zero/);
    expect(focus.evidence).toMatch(/unknown, not 0/);
  });

  it("never shows more than three at once", () => {
    const many = Array.from({ length: 9 }, (_, i) =>
      summary(rec(`2026-01-0${i + 1}`, {}, "### 22:00 | Dashboard\n[sleep.quality] 3/5\n")));
    expect(activeInsights(buildInsights(many, TODAY), TODAY, {})).toHaveLength(3);
  });

  it("honours dismiss and snooze without touching the repository", () => {
    const all = buildInsights([journalOnly], TODAY);
    expect(activeInsights(all, TODAY, { "integrity-repair": { dismissed: true } })).toHaveLength(0);
    expect(activeInsights(all, TODAY, { "integrity-repair": { snoozedUntil: "2026-01-20" } })).toHaveLength(0);
    expect(activeInsights(all, TODAY, { "integrity-repair": { snoozedUntil: "2026-01-14" } })).toHaveLength(1);
  });

  it("labels routine ids for humans", () => {
    expect(routineLabel("mg_stack")).toBe("Magnesium");
    expect(routineLabel("some_new_thing")).toBe("Some new thing");
  });
});
