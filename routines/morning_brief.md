# Morning Brief — OptiMind Routine

This is the **prompt for a scheduled cloud Claude Code Routine** (claude.ai scheduled
agent) connected to the **`optimind-journal`** repo, fired daily at **~05:55
America/New_York** (§8.2). Configure it as the Routine's prompt.

**Cloud runtime — no MCP tools, no hooks.** You operate on the repo with built-in
Read/Write/Bash/git only. The structured `daily/YYYY-MM-DD.json` shape, the dual-write
rules, and the snake_case-id / offset-timestamp conventions are defined in that repo's
**`CLAUDE.md` → Structured Logging** section — follow them exactly. Goal: generate
today's `protocol` and write a one-line `System` brief.

## Steps

1. **Resolve today's date in NYC.** Run `TZ='America/New_York' date '+%Y-%m-%d %H:%M %Z %A'`.
   Every time/date below is NYC-local — never bare UTC.

2. **Check for a pre-set override.** Read `daily/<date>.json` (if it exists). If it has a
   `protocol` whose `source` is `"mobile_override"`, the user set today's plan from the
   app — **do not regenerate**. Skip to step 6 (brief only).

3. **Gather inputs** (read the files directly):
   - `state.json` → `system_mode` + active constraints.
   - `user_profile.json` → rules with `topic` `scheduling` or `routine` (standing intent).
   - `journal/<last 1–2 days>.md` → recent context and any explicit override the user
     stated (e.g. "tomorrow skip the workout, I'm flying"). Honor it for today.

4. **Synthesize `protocol.items[]`** — each item `{id, expected_window, duration_min?, type?}`,
   `id` snake_case canonical (`sunlight`, `cold_shower`, `meditation`, `deep_work`, `workout`,
   `wind_down`, …). **Reshape sparse/incomplete inputs into a coherent, realistic day** rather
   than demanding complete data. If there's nothing useful and no override, start from the
   **default protocol** at the bottom of this file.

5. **Adjust for `system_mode`:**
   - `EXAM_MODE` → drop/shorten the workout, extend `deep_work`, protect sleep.
   - `DEEP_WORK` → more/longer focus blocks, minimize interruptions.
   - `RECOVERY` → lighter load, later start, more rest; no hard workout.
   - `STANDARD` → balanced. Respect active constraints (e.g. a fixed meeting time).

6. **Write the protocol into `daily/<date>.json`** (read → merge → write; shape per `CLAUDE.md`):
   set `protocol.generated_at` to the current NYC ISO-8601 timestamp **with offset** (e.g.
   `2026-05-28T05:55:00-04:00`, never `Z`), `protocol.source` to `mobile_override` (if you
   applied an explicit override) / `rule_derived` (from rules+state) / `default` (fell back),
   and `protocol.items` to your list. **Preserve any existing `log`.** Keep the file valid JSON,
   then re-read to confirm it parses. (Skip this write if step 2 found an existing `mobile_override`.)

7. **Write the brief** — append to `journal/<date>.md`:
   ```
   ### HH:MM | System
   <concise markdown summary of today's plan + the why: mode, key blocks, anything dropped/added>
   ```

8. **Commit** `daily/<date>.json` (if changed) and `journal/<date>.md` to `main`.

## Notes

- NYC-local times/date throughout (see `CLAUDE.md` → Timezone). Never bare UTC.
- Don't fabricate data you lack; reshape what's available and note assumptions in the brief.
- Idempotent: re-running regenerates a `rule_derived`/`default` protocol (overwrite is fine);
  **never overwrite a `mobile_override`.**

## Default protocol (day-one fallback)

Embedded so this Routine is self-contained in the cloud. Kept in sync with the canonical
`optimind/routines/default_protocol.json` (which the dashboard reuses as its empty-state default).

```json
{
  "items": [
    {"id": "sunlight", "expected_window": "06:30-07:30", "duration_min": 10},
    {"id": "cold_shower", "expected_window": "07:00-08:00"},
    {"id": "meditation", "expected_window": "07:30-08:00", "duration_min": 10},
    {"id": "deep_work", "expected_window": "09:30-12:00", "duration_min": 150},
    {"id": "workout", "expected_window": "17:00-18:30", "type": "strength"},
    {"id": "wind_down", "expected_window": "21:30-22:30"}
  ]
}
```
