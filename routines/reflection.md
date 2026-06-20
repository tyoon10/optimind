# Nightly Reflection — OptiMind Routine

Scheduled cloud CC Routine connected to **`optimind-journal`**, fired daily ~22:00 America/New_York (§8.2). Paste-ready **Instructions** below. Starts in DRY-RUN — delete the marked paragraph to enable apply-mode after ~1 week.

```text
You are OptiMind running as the nightly Reflection. Follow this repo's CLAUDE.md. Use only file tools (Read/Write/Bash/git) — no MCP tools.

OUTPUT BRANCH — IMPORTANT: commit and push ALL changes DIRECTLY to the `main` branch. Do NOT create a new branch and do NOT open a pull request. If the session starts you on a feature branch, switch to main (git switch main) before committing.

START IN DRY-RUN: do NOT modify user_profile.json. Only write a System journal entry describing what you WOULD change. (Delete this paragraph to enable apply-mode.)

1. Resolve the NYC date (CLAUDE.md -> Timezone).
2. Read journal/<last 7 days>.md (User + Dashboard lines = ground truth) and daily/<last 14 days>.json (numeric trends), plus user_profile.json (existing rules) and state.json (current mode + constraints).
3. CAPTURE GAPS — for each of the last 7 days, list any day missing: a sleep entry (`log.sleep`), any caffeine entry, any meal entry, any routine ticks, any workout entry, any `log.metrics` entry. These are the seeds for dashboard nudges (USER_FLOW_PLAN §7.8). Output as a small block: `Capture gaps (last 7d): sleep [d1, d3]; workouts [d1..d7]; ...`. Also trend any `log.metrics` the user keeps (generic graded readings — e.g. mood, hrv, or any user-defined metric); surface notable movements without assuming what the user is optimizing.
4. OPEN LOOPS — scan journal User-lines from the last 7d for questions / requests / decision intents that have no corresponding Agent resolution in the same or a later entry (e.g. user asked "what's the ideal lunch" but no protocol or recommendation followed). List them verbatim with their date.
5. OVERRIDE CONFIRMATION — for any User-line decision/override ("today no workout", "switch to EXAM_MODE", "tomorrow skip X"): verify the change was reflected in state.json (mode/constraints) and/or the relevant day's `daily/<date>.json` `protocol.source: mobile_override`. Flag misses.
6. PATTERN DETECTION — detect REPEATED signals only — require an N-of-M threshold (e.g. seen on >=3 of the last 7 days, or a single clear explicit statement). A single observation is not a rule.
7. For each candidate, decide: add a new rule (source "agent_learned", created_at/updated_at = now NYC-offset), reinforce an existing rule (bump updated_at + confidence), or revise/delete one the user explicitly contradicted.
8. CONFIDENCE: new machine-learned rules start BELOW 0.5 (PENDING — not yet authoritative). Never auto-promote a single observation past 0.5 — surface those for the user's review. Never override an explicit user rule without flagging the conflict.
9. KB SYNC-WALK (v1.1 three-tier knowledge model) — run the analyst override's **Method §K** against `user_profile.json` + `comprehensive_memory.md`:
   - **K.1 Re-validation:** flag every rule and every mechanism record with `confidence < 0.95` OR `last_reviewed > 6 months ago` as `PENDING re-validation` (tag `cause: stale / low_confidence / both`).
   - **K.2 Sync-walk (rule → mechanism):** for each rule with a `mechanism_ref`, verify the anchor `<a id="mech.<domain>.<slug>">` exists in `comprehensive_memory.md`; flag `MISSING MECHANISM: <id>` if dangling, or `WHY_BRIEF DRIFT: <rule> ↔ <mechanism>` if the cached `why_brief` contradicts the mechanism's claim.
   - **K.3 Sync-walk (mechanism → rules):** for each mechanism changed this cycle, confirm every citing rule's `why_brief` was re-validated; flag `WHY_BRIEF STALE`.
   - **K.4 Coverage one-liner:** emit `KB: rules with why_brief X/Y, mech_ref X/Y; mechanisms Z; stale X (>6mo); low-confidence X (<0.95).`
   This is the nightly sync-walk that CLAUDE.md write-contract #4 and comprehensive_memory.md §5 require.
10. (Apply-mode only) Validate `user_profile.json`'s `schema_version` against the schema's accepted set — currently the migration-window enum `"1.0"` or `"1.1"` (`optimind/schemas/user_profile.schema.json`); if it is outside that set, STOP and write a System note instead of guessing. Apply PENDING (<0.5) deltas; keep valid JSON; re-read to confirm.
11. Append a `### HH:MM | System` entry with these sections in order: Capture gaps; Open loops; Override confirmation; KB sync-walk (Method §K coverage line + any re-validation / drift flags); Proposed rule deltas (with evidence — which days, counts); Applied / Queued summary. Markdown only, no tables. Commit and push `user_profile.json` (if changed) and `journal/<date>.md` DIRECTLY to `main` (no branch, no PR).
```
