import { describe, it, expect } from "vitest";
import {
  applyField, renderValue, mirrorLine, newDoc, todayNYC, nowOffsetISO, type DailyLog, mirrorBlock } from "./daily";

describe("applyField (mirrors do_log_field)", () => {
  it("appends caffeine as an event with time injected", () => {
    const doc = newDoc("2026-05-28");
    const written = applyField(doc, "caffeine", { amount_mg: 95, source: "espresso" }, "08:14");
    expect(doc.log!.caffeine).toEqual([{ time: "08:14", amount_mg: 95, source: "espresso" }]);
    expect(written).toEqual({ time: "08:14", amount_mg: 95, source: "espresso" });
  });

  it("appends (not overwrites) repeated events", () => {
    const doc = newDoc("2026-05-28");
    applyField(doc, "caffeine", { amount_mg: 95 }, "08:14");
    applyField(doc, "caffeine", { amount_mg: 60 }, "13:30");
    expect(doc.log!.caffeine).toHaveLength(2);
  });

  it("routes singular 'meal' to the meals array", () => {
    const doc = newDoc("2026-05-28");
    applyField(doc, "meal", { items: "eggs, oats" }, "08:30");
    expect(doc.log!.meals).toEqual([{ time: "08:30", items: "eggs, oats" }]);
  });

  it("sets scalar sleep fields by dotted path", () => {
    const doc = newDoc("2026-05-28");
    applyField(doc, "sleep.wake_time", "06:42", "06:42");
    applyField(doc, "sleep.quality", 4, "06:42");
    expect(doc.log!.sleep).toEqual({ wake_time: "06:42", quality: 4 });
  });

  it("sets routine items as an object map", () => {
    const doc = newDoc("2026-05-28");
    applyField(doc, "routine.cold_shower", { done: true, time: "07:35" }, "07:35");
    expect(doc.log!.routine!.cold_shower).toEqual({ done: true, time: "07:35" });
  });
});

describe("rendering", () => {
  it("renders dict values space-joined; bool as true/false", () => {
    expect(renderValue({ time: "08:14", amount_mg: 95, source: "espresso" })).toBe("08:14 95 espresso");
    expect(renderValue(true)).toBe("true");
    expect(renderValue("06:42")).toBe("06:42");
  });

  it("formats the Dashboard mirror line", () => {
    expect(mirrorLine("08:14", "caffeine", "08:14 95 espresso"))
      .toBe("\n### 08:14 | Dashboard\n[caffeine] 08:14 95 espresso\n");
  });
});

describe("NYC time helpers", () => {
  it("todayNYC is YYYY-MM-DD", () => {
    expect(todayNYC(new Date("2026-05-28T12:00:00Z"))).toMatch(/^\d{4}-\d{2}-\d{2}$/);
  });
  it("nowOffsetISO carries a numeric offset, never bare Z", () => {
    const ts = nowOffsetISO(new Date("2026-05-28T12:00:00Z"));
    expect(ts.endsWith("Z")).toBe(false);
    expect(ts).toMatch(/[+-]\d{2}:\d{2}$/);
  });
});

// --- mirror rendering (fixes found by the first real 8/11 repair) -------------

describe("mirror rendering", () => {
  it("renders a graded reading as 2/5, not '2 5'", () => {
    // The first production repair wrote `[metrics.back_pain] 2 5`, breaking the
    // convention every historical line uses and the analyst agent's greps.
    expect(renderValue({ value: 2, scale: 5 })).toBe("2/5");
    expect(renderValue({ value: 1, scale: 5, note: "estimated" })).toBe("1/5 estimated");
  });

  it("leaves non-graded objects joined as before", () => {
    expect(renderValue({ status: "done", time: "19:00" })).toBe("done 19:00");
    expect(renderValue({ time: "08:14", amount_mg: 65, source: "espresso" })).toBe("08:14 65 espresso");
  });

  it("puts a whole submission in ONE Dashboard block", () => {
    // Nine fields previously produced nine `### HH:MM | Dashboard` headers.
    const block = mirrorBlock("16:42", [
      { field: "sleep.bedtime", rendered: "23:30" },
      { field: "sleep.quality", rendered: "1" },
      { field: "metrics.back_pain", rendered: "2/5" },
    ]);
    expect(block.match(/### 16:42 \| Dashboard/g)).toHaveLength(1);
    expect(block).toContain("[sleep.bedtime] 23:30\n[sleep.quality] 1\n[metrics.back_pain] 2/5");
  });

  it("labels a past-dated write as a backfill", () => {
    const block = mirrorBlock("16:42", [{ field: "sleep.quality", rendered: "1" }], true);
    expect(block).toContain("| Dashboard (backfill)");
  });
});
