# Nightly Reflection — OptiMind Routine

Prompt for a scheduled cloud Claude Code Routine connected to **`optimind-journal`**,
fired daily at **~22:00 America/New_York** (§8.2). Configure it as the Routine's prompt.

**Cloud runtime — no MCP tools, no hooks.** Operate on the repo via Read/Write/Bash/git.
This repo's `CLAUDE.md` (Structured Logging + Timezone) and `comprehensive_memory.md` are
your context. Goal: turn the last week of logs into **proposed preference-rule updates**
in `user_profile.json`, conservatively, with PENDING semantics.

## Inputs

- `journal/<last 7 days>.md` — `User` + `Dashboard` lines are ground truth (what the user
  said / logged); `Agent`/`System` lines are what the system did.
- `daily/<last 14 days>.json` — quantitative trends (sleep quality moving average, caffeine
  timing distribution, routine-compliance rate, workout frequency).
- `user_profile.json` — existing rules (topics: nutrition, scheduling, profile, environment,
  …) with `schema_version`, each rule `{topic, rule, source, created_at, updated_at, confidence}`.

## Method

1. Resolve the NYC date (see `CLAUDE.md` → Timezone).
2. Read the inputs above. Pull only what you need.
3. Detect **repeated** signals, not one-offs. Require an **N-of-M threshold** before proposing
   anything: e.g. a behavior/preference observed on **≥3 of the last 7 days** (or a clear
   explicit statement). A single observation is an observation, not a rule.
4. For each candidate, emit a `MemoryAction`:
   - `add` — a new rule (`source: "agent_learned"`, `created_at`/`updated_at` = now NYC offset).
   - `reinforce` — bump an existing rule's `updated_at` and confidence (repeated signal).
   - `revise` / `delete` — when the user explicitly contradicts or revokes a standing rule.

## Confidence + PENDING (do not over-reach)

- New machine-learned rules start **below 0.5 → PENDING** (machine-readable but not yet
  authoritative). Reinforcement can raise confidence toward/above 0.5 over repeated cycles.
- **Never auto-promote a single observation to an authoritative (≥0.5) rule.** Promotions that
  cross 0.5 should be surfaced for the user's review (PENDING queue), not applied silently.
- Never override an explicit user rule without surfacing the conflict.

## Apply + audit

1. Validate `user_profile.json`'s `schema_version` (currently `1.0`); if it mismatches, **stop**
   and write a `System` note rather than guessing. (Canonical schema: `optimind/schemas/
   user_profile.schema.json` — not in this repo; the rule shape above is the self-contained copy.)
2. Apply safe (PENDING, &lt;0.5) deltas directly to `user_profile.json`; keep valid JSON; re-read to confirm.
3. Append a `### HH:MM | System` entry to `journal/<date>.md` summarizing **what you proposed,
   what you applied, and what you queued for review**, with the evidence (which days / counts).
4. Commit `user_profile.json` (if changed) + `journal/<date>.md`.

## Notes

- **Dry-run first:** until told otherwise, do NOT mutate `user_profile.json` — only write the
  `System` summary of what you *would* change. Flip to apply-mode once the proposals look right
  for ≥1 week (§10.5 acceptance gate).
- Reflection reads **both** journal (qualitative) and daily (quantitative) — a rule can be
  supported by "user said 'cutting afternoon coffee'" *and* "caffeine after 14:00 on 5/7 days".
