# Weekly Review — OptiMind Routine

Prompt for a scheduled cloud Claude Code Routine connected to **`optimind-journal`**,
fired **Sundays ~18:00 America/New_York** (§8.2). Configure it as the Routine's prompt.

**Cloud runtime — no MCP tools, no hooks.** Operate on the repo via Read/Write/Bash/git.
This repo's `CLAUDE.md` + `comprehensive_memory.md` are your context. Goal: a concise,
honest weekly trend report written into the journal (the user reads it on next open —
reminders are dashboard-pull, no push).

## Inputs

- `daily/<last 14 days>.json` — the numbers: sleep (bedtime/wake/quality), caffeine
  (timing + mg), routine-compliance (done vs protocol), workouts, meals.
- `journal/<last 7–14 days>.md` — context, mood/energy notes, open loops, what the user said.
- `user_profile.json` — standing rules, to judge adherence against intent.

## Method

1. Resolve the NYC date (see `CLAUDE.md` → Timezone); state the week range (Mon–Sun).
2. Compute simple trends from `daily/*.json` — e.g. avg sleep quality and its 7-vs-prior-7
   delta, median bedtime/wake, caffeine count + how often after 14:00, routine-compliance %,
   workout count. Use whatever's present; **don't fabricate** missing days — say "no data".
3. Cross-read the journal for the *why* behind the numbers (travel, deadlines, mode changes).

## Output — a `System` report in the journal

Append a `### HH:MM | System` entry to `journal/<date>.md` with:
- **Wins** — what improved vs. the prior week (with the numbers).
- **Drift** — what slipped, and the likely upstream cause (holistic reasoning — a focus dip is
  often a sleep dip).
- **Open loops** — unresolved items the user mentioned.
- **One suggested focus** for the coming week (single, concrete, tied to a goal/rule).

Keep it tight and skimmable — markdown, no tables (renders cleanly in any viewer). Then commit.

## Notes

- NYC-local dates/times (see `CLAUDE.md` → Timezone). Never bare UTC.
- Read-mostly: this Routine writes only the `System` report; it does **not** change rules
  (that's the nightly Reflection Routine) or the protocol (that's the morning brief).
- No notification — the report waits in the journal/dashboard for the user's next check-in.
