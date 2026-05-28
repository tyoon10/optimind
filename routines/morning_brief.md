# Morning Brief — OptiMind Routine

Scheduled CC Routine. Runs daily at **~05:55 America/New_York** (§8.2). Goal: generate
today's `protocol` (the plan for the day) and write a one-line brief to the journal.

Personal data binds via `OPTIMIND_JOURNAL_PATH`; operate through the `optimind` MCP
tools (`get_daily`, `get_state`, `get_rules`, `get_recent_journal`, `set_protocol`,
`log_entry`) — never read or write the journal/daily files directly.

## Steps

1. **Resolve today's date in NYC.** Run `TZ='America/New_York' date '+%Y-%m-%d %H:%M %Z %A'`.
   Every time and date below is NYC-local — never bare UTC.

2. **Check for a pre-set override.** Call `get_daily` for today. If it already has a
   `protocol` whose `source` is `"mobile_override"`, the user set today's plan from
   mobile — **do not regenerate**. Skip to step 6 and just write the brief.

3. **Gather inputs** (pull only what you need):
   - `get_state` → `system_mode` + active constraints.
   - `get_rules` topic `scheduling`, then topic `routine` → standing intent
     (e.g. "morning sunlight within 30 min of wake", "deep work before noon").
   - `get_recent_journal` last 2 days → recent context and any explicit override the
     user stated (e.g. "tomorrow skip the workout, I'm flying"). Honor it for today.

4. **Synthesize `protocol.items[]`.** Each item:
   - `id` — snake_case, using the canonical keyword where one exists (`cold_shower`,
     `deep_work`, `workout`, `sauna`; plus `sunlight`, `meditation`, `wind_down`, …).
   - `expected_window` — `HH:MM-HH:MM` local.
   - `duration_min` (int) and/or `type` (str) where meaningful.

   Assume inputs are incomplete — **reshape sparse rules into a coherent, realistic day**
   rather than demanding complete data. If there are no useful rules and no override,
   start from the default in [`default_protocol.json`](./default_protocol.json).

5. **Adjust for `system_mode`:**
   - `EXAM_MODE` → drop/shorten the workout, extend `deep_work`, protect sleep.
   - `DEEP_WORK` → more/longer focus blocks, minimize interruptions.
   - `RECOVERY` → lighter load, later start, more rest; no hard workout.
   - `STANDARD` → balanced.
   Respect active constraints (e.g. a fixed meeting time).

6. **Write the protocol** with `set_protocol(items, source)`:
   - `source="mobile_override"` if you applied an explicit user override,
   - `source="rule_derived"` if built from rules/state,
   - `source="default"` if you fell back to the default protocol.
   (Skip if step 2 found an existing `mobile_override` — already set.)

7. **Write the brief** with `log_entry(role="System", content=<brief>)` — a concise
   markdown summary of today's plan and the *why* (mode, key blocks, anything
   dropped/added vs. default). One short entry; it is the morning-brief audit line.

## Notes

- All times/date NYC-local (`tz` binding). Never bare UTC.
- Don't fabricate data you lack; reshape what's available and note assumptions in the brief.
- Idempotent: re-running regenerates a `rule_derived`/`default` protocol (overwrite is fine);
  never overwrite a `mobile_override`.
