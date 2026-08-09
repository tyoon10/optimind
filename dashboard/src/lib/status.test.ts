// Contract test: this classifier and the Python one must agree.
//
// Both read schemas/integrity_cases.json. If the two implementations ever
// drift, a day would render `missing` in one surface and `journal_only` in
// another — the same confusion the whole build exists to remove.

import { describe, expect, it } from "vitest";
import cases from "../../../schemas/integrity_cases.json";
import { classifyDay, dashboardFacts, isResolvable, normalizeField, parseScore, routineStateFromRaw, splitQualifier } from "./status";
import type { DailyLog } from "./daily";

function docFor(c: any): DailyLog | null {
  if (!c.daily) return null;
  return { schema_version: "1.1", date: c.date, tz: "America/New_York", ...c.daily };
}

describe("shared integrity contract", () => {
  for (const c of cases.cases) {
    it(`${c.name} — ${c.why}`, () => {
      const r = classifyDay(docFor(c), c.journal, c.date, cases.today);
      expect(r.status).toBe(c.expect.status);
      expect(r.journalOnly.sort()).toEqual([...c.expect.journal_only].sort());
      expect(r.structuredOnly.sort()).toEqual([...c.expect.structured_only].sort());
      expect(r.needsInput.sort()).toEqual([...c.expect.needs_input].sort());
    });
  }
});

describe("journal parsing", () => {
  it("reads facts only from Dashboard blocks", () => {
    const facts = dashboardFacts(
      "### 09:38 | User\n[attached photo] hi\n\n### 09:40 | Dashboard\n[sleep.quality] 3/5\n",
    );
    expect(facts.map((f) => f.field)).toEqual(["sleep.quality"]);
  });

  it("keeps the line number so the UI can cite its evidence", () => {
    const facts = dashboardFacts("### 09:40 | Dashboard\n[sleep.quality] 3/5\n");
    expect(facts[0].line).toBe(2);
    expect(facts[0].time).toBe("09:40");
  });

  it("folds singular field spellings onto the array key", () => {
    expect(normalizeField("meal.breakfast")).toBe("meals");
    expect(normalizeField("workout")).toBe("workouts");
    expect(normalizeField("routine.zinc")).toBe("routine.zinc");
  });
});

describe("value interpretation", () => {
  it("splits a trailing qualifier", () => {
    expect(splitQualifier("done (overcast)")).toEqual(["done", "overcast"]);
    expect(splitQualifier("07:00")).toEqual(["07:00", undefined]);
  });

  it("parses scores with and without a scale", () => {
    expect(parseScore("3/5")).toEqual([3, 5]);
    expect(parseScore("2")).toEqual([2, undefined]);
  });

  it("keeps skipped and not_reported distinct", () => {
    expect(routineStateFromRaw("SKIPPED")).toBe("skipped");
    expect(routineStateFromRaw("not reported")).toBe("not_reported");
    expect(routineStateFromRaw("done at 19:30")).toBe("done");
  });

  it("flags lines the schema cannot represent", () => {
    const f = (field: string, raw: string) => ({ time: "22:00", field, raw, line: 1 });
    expect(isResolvable(f("meals", "08:50 eggs"))).toBe(true);
    expect(isResolvable(f("meals", "morning: eggs"))).toBe(false);
    expect(isResolvable(f("caffeine", "09:05 espresso ~65mg"))).toBe(true);
    expect(isResolvable(f("caffeine", "09:10 coffee, amount not stated"))).toBe(false);
  });
});
