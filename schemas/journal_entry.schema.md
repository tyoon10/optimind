# Journal Entry Format Specification

Canonical format spec for the daily journal files written and read by OptiMind.

> **Why this exists:** the Analyst subagent does multi-day pattern detection by `grep`-ing keywords across files. If keywords drift between sessions (e.g. "cold shower" vs "cold rinse", "deep work" vs "deepwork"), the agent silently misses data. This spec locks the keyword vocabulary in.

## File layout

- **Path:** `<journal_root>/YYYY-MM-DD.md`
- **`journal_root`** is resolved from the `OPTIMIND_JOURNAL_PATH` environment variable. See [`optimind_interface.md`](./optimind_interface.md).
- **One file per day.** Date is the user's *local* date (US/Eastern by default), never bare UTC.
- **Append-only within a day.** Existing entries are never edited or reordered by the agent.

## Entry format

Each entry is a markdown H3 header followed by free-form content:

```markdown
### HH:MM | <role>
<content>
```

- `HH:MM` — 24-hour local time, in the same timezone as the filename.
- `<role>` — one of: `User`, `Agent`, `System`.
- `<content>` — free-form markdown. The agent SHOULD use the grep-signal keywords below for any structured observation.

## Grep-signal keyword table

The following lowercased keywords are the **authoritative vocabulary** the Analyst greps for. New entries SHOULD use these spellings exactly. Synonyms are explicitly forbidden — if a new concept appears, add it to this table first, don't invent a variant.

| Domain        | Canonical keyword | Forbidden synonyms                |
|---------------|-------------------|-----------------------------------|
| Sleep         | `sleep score`     | `sleep quality`, `sleep rating`   |
| Sleep         | `bedtime`         | `lights out`, `to bed`            |
| Sleep         | `wake time`       | `woke up`, `wakeup`               |
| Nutrition     | `caffeine`        | `coffee`, `espresso`, `tea`       |
| Nutrition     | `meal`            | `food`, `ate`, `lunch`/`dinner`*  |
| Nutrition     | `supplement`      | `vitamin`, `pill`                 |
| Movement      | `workout`         | `exercise`, `training`, `gym`     |
| Movement      | `cold shower`     | `cold rinse`, `cold exposure`     |
| Movement      | `sauna`           | `heat exposure`                   |
| Focus         | `deep work`       | `deepwork`, `focused work`        |
| Focus         | `flow state`      | `in the zone`                     |
| Mood          | `mood`            | `feeling`, `vibe`                 |
| Mood          | `energy`          | `tiredness`, `fatigue`            |
| Mode          | `EXAM_MODE`       | (uppercase, exact)                |
| Mode          | `DEEP_WORK`       | (uppercase, exact)                |
| Mode          | `RECOVERY`        | (uppercase, exact)                |
| Mode          | `STANDARD`        | (uppercase, exact)                |

\* `lunch` / `dinner` are allowed *in addition to* `meal` (they're useful timing signals), but every food entry must contain `meal` so the Analyst's `meal` query returns it.

## Example

```markdown
### 07:42 | User
Slept 7h. sleep score 84. Skipped caffeine. Doing deep work block 8–11.

### 07:43 | Agent
Logged. Switching to DEEP_WORK mode for the morning.

### 12:15 | User
meal: chicken + rice + greens. energy good. no caffeine yet — holding the line.
```

## Validation

There is no JSON validator for these files (they're markdown), but `scripts/lint_journal.py` (TODO) SHOULD flag any forbidden synonyms found in the file's content. The schema and lint are advisory; the file is still parsed as plain text.
