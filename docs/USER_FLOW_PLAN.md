# OptiMind End-to-End User Flow Plan

> **Status:** Living draft. Sections marked **[INPUT NEEDED]** are awaiting user input. Sections marked **[GROUNDED]** are pre-filled from the codebase as of this commit and may be edited.
>
> **Audience:** This document is the baseline handoff for Claude Code (VS Code, multi-repo workspace: `tyoon10/optimind` + `optimind-journal`). When extending the product — building the dashboard, adding interaction surfaces, tuning system prompts — start here, not from the code alone.
>
> **How to use this doc:**
> 1. The user fills in **[INPUT NEEDED]** sections incrementally.
> 2. CC in VS Code reads §1–§4 to ground itself, then §5–§7 to derive concrete work.
> 3. Every feature, dashboard widget, or prompt change should trace back to a flow in §5 — if it doesn't, it's scope creep.

---

## 1. Why this document exists

Today OptiMind is a working agent runtime (Slack + Claude Agent SDK + journal repo). It has the right primitives — tools, subagents, a verbatim journal, a typed user_profile — but no *product spec*. The next phase (dashboard, richer prompts, new surfaces) needs to be driven by **what the user actually wants to do**, not by what's technically interesting to build.

This doc captures: the user's goals → desired interactions → end-to-end flows → derived requirements for the system prompt and dashboard. It's the contract between "what I want OptiMind to be" and "what gets built."

---

## 2. Current state (grounded)

**[GROUNDED — current as of branch `claude/funny-lovelace-zZXSP`]**

### Architecture (two repos, runtime-bound)

| Repo | Owns |
|---|---|
| `tyoon10/optimind` | Agent runtime, MCP tools, generic agent prompts, canonical schemas |
| `optimind-journal` | Personal data (`user_profile.json`, `state.json`, `journal/YYYY-MM-DD.md`), personal agent overrides |

Bound at runtime via `OPTIMIND_JOURNAL_PATH`. See `schemas/optimind_interface.md`.

### Surfaces

- **Slack** (today's only interface). Bot responds via `optimind-sdk/src/server.py`. Slack-flavored formatting enforced via `slack_format_hook`.

### Capabilities

| Capability | Implementation |
|---|---|
| Multi-day journal read | `mcp__optimind__get_recent_journal`, `mcp__optimind__search_journal` |
| Verbatim user-input logging | `UserPromptSubmit` hook → `journal/YYYY-MM-DD.md` (runtime-guaranteed, not model-discretionary) |
| Agent-written log entries | `mcp__optimind__log_entry` (model-chosen content, with dedup) |
| State (mode + constraints + focus) | `get_state` / `set_state` over `state.json`; modes: `STANDARD`, `EXAM_MODE`, `DEEP_WORK`, `RECOVERY` |
| Preference rules | `get_rules` / `add_rule` / `delete_rule` over `user_profile.json`; PENDING semantics at confidence `< 0.5` |
| Subagent delegation | `nutritionist`, `scheduler`, `analyst` defined in `.claude/agents/` (generic) + override layer in optimind-journal |
| Web search | Enabled on main + nutritionist + analyst |
| Git sync of journal | `sync_hook` commits + pushes the optimind-journal repo after each turn |

### Not yet built

- Dashboard / non-Slack surface
- Out-of-band reflection (current reflector runs on Stop, sees one turn)
- Memory promotion pipeline (PENDING → durable based on cross-day reinforcement)
- Decay / archival of stale rules
- Multi-device / voice / mobile-native input
- Calendar or wearable integrations

---

## 3. User goals **[INPUT NEEDED]**

> _Provide the top 3–7 outcomes you're trying to achieve by using OptiMind. Be concrete — "sleep better" is a category; "wake up before 7 AM five days a week without an alarm" is a goal._

### 3.1 Primary goals

1. _[goal 1 — what does success look like in 90 days?]_
2. _[goal 2]_
3. _[goal 3]_

### 3.2 Secondary goals
- _[nice-to-haves]_

### 3.3 Anti-goals
> _What you explicitly do not want OptiMind to become (e.g., "not a chat companion," "not a calendar app," "no gamification")._
- _[anti-goal 1]_

### 3.4 Time horizon
> _Are these goals for the next month, quarter, year? Does OptiMind need to "graduate" you off itself at some point, or is it permanent infrastructure?_

---

## 4. How you want to use the product **[INPUT NEEDED]**

### 4.1 When and where
> _When in your day do you imagine reaching for OptiMind? Morning planning? Mid-workout? End-of-day reflection? Reactive (when something goes wrong) or scheduled (daily check-in)? Phone vs laptop?_

### 4.2 Interaction style
> _Conversational (paragraphs back and forth)? Telegraphic ("logged: 2 espresso, 7am")? Voice? Mostly read-only (consume dashboard, rarely type)? Mixed — e.g., dashboard for review, Slack for capture?_

### 4.3 Cadence
> _How often do you want OptiMind to talk to you proactively? Daily morning brief? Weekly trend report? Only on anomalies (sleep score crashed; missed three workouts)? Never — purely on demand?_

### 4.4 Friction tolerance
> _What's the max latency you'll tolerate for a response? How many taps to log a meal? Is "open Slack, type, send" already too much, or fine?_

### 4.5 Privacy posture
> _Does any data leave your devices? Cloud OK for code (optimind), local-only for data (optimind-journal)? Are there topics you'd never want logged verbatim?_

---

## 5. End-to-end flows **[INPUT NEEDED — partially seeded]**

> _For each flow: name it, list the trigger, the steps from user POV, the success outcome, and the failure mode. Aim for 5–10 concrete flows; we'll prioritize from there._
>
> _The flows below are seeds — examples of the kind of thing to define. Replace, reorder, delete, expand._

### Flow A: Morning brief
- **Trigger:** _[Push at 7:00? User opens Slack first thing? Dashboard load?]_
- **Steps:** _[What does the user see / do?]_
- **System reads:** last 24h journal, state.json, today's calendar (if integrated), user_profile rules tagged `scheduling`
- **System writes:** today's journal opens with a System entry; possibly a state mode change
- **Success:** _[user has a clear top-3 plan within 90 seconds]_
- **Failure mode:** _[what does a broken version look like? Stale data? Generic advice? Overwhelm?]_

### Flow B: In-the-moment logging
- **Trigger:** _[Just ate, just finished a workout, just took a supplement]_
- **Steps:** _[Voice? Typed shorthand? Photo? What's the minimum input?]_
- **System reads:** existing journal for dedup, relevant rules for validation
- **System writes:** journal entry, possibly an `add_rule` PENDING candidate
- **Success:** _[<5 seconds, no friction, confirmation visible]_
- **Failure mode:** _[friction high enough that user stops logging]_

### Flow C: Reactive consultation
- **Trigger:** _[3 PM energy crash, headache, can't focus, sleep tracker shows 5h]_
- **Steps:** _[User describes symptom; system traces upstream]_
- **System reads:** last 3–7 days journal, relevant rules, state
- **System writes:** journal entry capturing the consult; possibly a state mode change
- **Success:** _[upstream cause identified or 2–3 high-probability hypotheses with verification steps]_

### Flow D: Weekly trend review
- **Trigger:** _[Sunday 6 PM? User asks? Auto-generated?]_
- **Steps:** _[Analyst runs; surfaces report]_
- **System reads:** last 7–14 days journal, all rules, state history
- **System writes:** weekly report entry; PENDING rule promotions/decays
- **Success:** _[user spots 1–2 patterns they didn't see in the moment]_

### Flow E: Mode switch (proactive or user-initiated)
- **Trigger:** _[Exam coming up; injury; vacation; travel; deep-work week]_
- **Steps:** _[User mentions context OR system detects from journal]_
- **System reads:** existing constraints, calendar (if any), rules
- **System writes:** state.json (mode + constraints + focus), journal entry noting the switch
- **Success:** _[subsequent advice is mode-aware without re-prompting]_

### Flow F: _[YOUR FLOW — add as many as you want]_

---

## 6. Derived system-prompt requirements **[GROUNDED — will update as §3–§5 fill in]**

> _Once goals + flows are specified, this section converts them to concrete edits in `optimind-sdk/CLAUDE.md` and `.claude/agents/*.md`._

### 6.1 Existing principles (keep)
- Holistic reasoning (cross-domain trace)
- Evidence-based (Huberman/Attia/Walker consensus, no fads)
- Disciplined coach tone (not cheerleader)
- Slack formatting rules
- Subagent delegation only when domain depth is needed

### 6.2 To-be-derived from goals & flows
- _[e.g., "always end a reactive consult with a verification step the user can do in <10 minutes"]_
- _[e.g., "never propose more than 3 changes in a single response — chunk into follow-ups"]_
- _[e.g., "morning brief is read-only by default; never auto-write a new rule before noon"]_

---

## 7. Derived dashboard requirements **[INPUT NEEDED + seeded]**

> _A dashboard is a different surface than chat. Decide what it's for: at-a-glance review? Data entry? Tweaking rules? All three?_

### 7.1 Purpose (pick one or rank)
- [ ] **Review surface** — read-only, see trends and state at a glance
- [ ] **Capture surface** — fast logging that Slack can't do well (sliders, photos, voice)
- [ ] **Rule management** — see / edit / promote / archive rules; resolve PENDING
- [ ] **Mode + state control** — toggle EXAM_MODE etc. without typing
- [ ] **Audit log** — verbatim journal browser with grep

### 7.2 Candidate views (seeded — keep, drop, add)
- **Today** — current state badge, today's journal so far, calendar context, top-3 plan
- **Trends** — sleep, energy, focus, caffeine, workouts plotted over 30/90 days
- **Rules** — sortable list with confidence + last reinforced; PENDING quarantine area
- **Journal browser** — date picker, grep box, role filter (User/Agent/System)
- **Memory diff** — pending Analyst-proposed rule changes with one-tap apply/reject

### 7.3 Tech choices **[INPUT NEEDED]**
> _Web (deployed where)? Desktop app? Lives inside Slack? Mobile-first? Static export from the journal repo (e.g., a GitHub Pages site that rebuilds nightly)?_

---

## 8. Open questions / decisions log

> _Append as we go. Each entry: date, question, decision, rationale._

- **YYYY-MM-DD** — _[question]_ → _[decision]_ — _[why]_

---

## 9. Out of scope (for now)

> _Things we've explicitly deferred. Write them down so they don't keep coming back as "wait, should we…?"_

- _[e.g., voice input — defer until Slack + dashboard prove the flow]_
- _[e.g., wearable integration — manual logging first, automate only after the manual habit sticks]_
