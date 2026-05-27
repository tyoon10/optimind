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

- **Slack** (current). Bot responds via `optimind-sdk/src/server.py`. Slack-flavored formatting enforced via `slack_format_hook`. **Status:** being deprecated as the primary surface (see §4.6) — likely retained only as a notification channel for scheduled jobs.

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

### Not yet built (prioritized after §4.6 + §8 decisions)

**Near-term, unblocks the new architecture:**
1. **`SessionStart` hook** in optimind that clones/pulls optimind-journal and sets `OPTIMIND_JOURNAL_PATH` — without this, CC mobile sessions can't see personal data.
2. **`.mcp.json`** at repo root so any CC session auto-registers the optimind MCP server (journal/state/preference tools).
3. **Dashboard MVP** — capture surface for sleep score, mode toggle, supplement checklist (per §7).
4. **Scheduled-jobs scaffolding** — `.github/workflows/` for the GHA jobs; a `routines/` directory for CC Routine prompts (per §8).
5. **Reflection pipeline** — `scripts/reflect.py` that the 22:00 Routine invokes; emits `MemoryAction` deltas applied via existing tools.

**Mid-term:**
- Calendar integration (read-only) for morning brief
- Anomaly detection thresholds (currently no threshold config)
- PENDING rule review queue in dashboard

**Deferred / removed:**
- Slack server as primary surface — see §10
- Wearable / voice input — see §10

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
**[INPUT NEEDED]**
> _When in your day do you imagine reaching for OptiMind? Morning planning? Mid-workout? End-of-day reflection? Reactive (when something goes wrong) or scheduled (daily check-in)?_

### 4.2 Interaction style
**[ANSWERED]**

- **Flexible / free-form input → CC mobile app.** Anything that's natural to express in language (logging "had 2 espresso shots and feeling jittery", reactive consults, weekly review questions).
- **Structured / standardized input → dashboard.** Anything with a constrained value space (sleep score 0–100, mode toggle, supplement checklist) where typed prose is slower and noisier than tapping a control.
- **Q&A, feedback, and validation → CC mobile app.** The conversational loop is mobile-first.

The rule of thumb: **mobile for language, dashboard for forms.** If a flow needs both (e.g. log a workout *with notes*), the dashboard captures the structured part and links to a mobile session for the prose.

### 4.3 Cadence
**[PARTIAL — periodicity will come from scheduled jobs, see §10]**
> _Beyond the scheduled jobs in §10, do you want any other proactive nudges (anomaly-triggered, deadline-triggered)?_

### 4.4 Friction tolerance
**[INPUT NEEDED]**
> _Acceptable taps to log a meal on the dashboard? Acceptable round-trip latency for a mobile question (3s? 10s? 30s)?_

### 4.5 Privacy posture
**[INPUT NEEDED]**
> _CC mobile sessions run in Anthropic-managed ephemeral containers; the SessionStart hook will clone optimind-journal into that container. Are you comfortable with personal data passing through that environment, or do you want a stricter posture (e.g., only synthetic / numeric data in the cloud; verbatim free-form text stays local)?_

### 4.6 Platform / runtime model
**[ANSWERED — has architectural implications, see §6.3]**

OptiMind is no longer a long-running server. Three runtime modes:

| Mode | Runs in | Triggers | Owns |
|---|---|---|---|
| **Interactive** | CC mobile app session | User opens the app | Logging, Q&A, consults, feedback |
| **Structured capture** | Dashboard (web) | User taps a control | Validated fields → writes to optimind-journal |
| **Scheduled** | GHA or CC Routines | Cron | Diagnostics, reminders, memory promotion (see §10) |

Each interactive session is **ephemeral**: a fresh container, fresh clone of optimind, fresh pull of optimind-journal, then the agent boots. There is no cross-session in-memory state. Everything durable lives in optimind-journal.

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
- Subagent delegation only when domain depth is needed

### 6.2 Existing principles (revise)
- ~~Slack formatting rules~~ → **Mobile-app markdown formatting.** Drop the `*bold*` / `•` Slack idioms. CC mobile renders standard markdown; `slack_format_hook` should be removed from the default hook set and kept only behind a flag for the (now-secondary) Slack notification channel.

### 6.3 New principles (from §4.6 ephemeral runtime)
- **Re-orient from journal, not from memory.** Every session starts cold. The system prompt must include an explicit step: "before reasoning, read today's journal and `state.json`." Don't assume continuity with the previous turn unless the journal proves it.
- **State.json is the only durable mode handle.** If the user said "I'm in EXAM_MODE" three sessions ago, that only persists because `set_state` was called. Never rely on session-resume — `opts.resume = session_id` is not a substitute for state.
- **Log verbatim before reasoning.** The `UserPromptSubmit` hook (already shipped) guarantees this; the system prompt should not duplicate the responsibility ("the runtime has already logged your input").
- **Dashboard writes are authoritative.** When the dashboard logs a structured value (e.g. `sleep_score: 84`), the model must treat that as ground truth even if the user later says something different conversationally. Conflicts surface as a question, not a silent override.
- **No long-running assumptions.** Don't say "I'll check on this in an hour" — there is no "I" between sessions. Anything periodic happens via §10 scheduled jobs.

### 6.4 To-be-derived from goals & flows
- _[e.g., "always end a reactive consult with a verification step the user can do in <10 minutes"]_
- _[e.g., "never propose more than 3 changes in a single response — chunk into follow-ups"]_
- _[e.g., "morning brief is read-only by default; never auto-write a new rule before noon"]_

---

## 7. Derived dashboard requirements **[INPUT NEEDED + seeded]**

> _A dashboard is a different surface than chat. Decide what it's for: at-a-glance review? Data entry? Tweaking rules? All three?_

### 7.1 Purpose
**[ANSWERED — capture-first; review/management secondary]**

Per §4.2, the dashboard's primary job is **standardized input** — the things mobile chat does poorly:
- [x] **Capture surface (primary)** — sliders, dropdowns, checklists, photos. Logs structured values directly to optimind-journal (sleep score, meal composition, supplement checklist, mode toggle).
- [x] **Mode + state control** — single-tap EXAM_MODE / DEEP_WORK / RECOVERY; constraint chips.
- [x] **Rule management** — resolve PENDING rules surfaced by scheduled reflection (§10); see / promote / archive durable rules.
- [ ] **Review surface (secondary)** — trends, journal browser. Useful but not the reason to build the dashboard; mobile + Analyst subagent can cover most read needs initially.

The dashboard does **not** host conversational Q&A. Anything that wants prose goes to mobile.

### 7.2 Candidate views (seeded — keep, drop, add)
- **Today** — current state badge, today's journal so far, calendar context, top-3 plan
- **Trends** — sleep, energy, focus, caffeine, workouts plotted over 30/90 days
- **Rules** — sortable list with confidence + last reinforced; PENDING quarantine area
- **Journal browser** — date picker, grep box, role filter (User/Agent/System)
- **Memory diff** — pending Analyst-proposed rule changes with one-tap apply/reject

### 7.3 Tech choices **[PARTIAL]**
**Constraints implied by §4.6:**
- Must be reachable from the same device as the mobile app (so: web, not a desktop-only app).
- Reads and writes the same files in optimind-journal that the agent uses (`user_profile.json`, `state.json`, `journal/YYYY-MM-DD.md`) — through a thin API or direct repo commits.
- Auth: single-user; whatever's simplest (GitHub OAuth piggybacking on the repo's existing PAT, or a static token).

**[INPUT NEEDED] — pick a deployment shape:**
- **Option A: GitHub Pages + GHA writeback.** Static site reads the journal repo via the GitHub API; form submissions trigger a GHA that commits to optimind-journal. Zero servers, free hosting, slight latency on writes (~30s for the action to run).
- **Option B: Tiny FastAPI backend in optimind-sdk + Vercel/Fly frontend.** Reuses the existing Python codebase and tool functions. Sub-second writes. Needs a deployed service.
- **Option C: Anthropic-hosted artifact / Streamlit.** Lowest code; weakest control over UX.

Recommendation pending §4 inputs; **default leaning is Option A** unless you want sub-second feedback on dashboard writes.

---

## 8. Scheduled jobs (out-of-band) **[ANSWERED — partial]**

Per §4.6, all proactive / periodic behavior is owned here, not by any interactive session.

### 8.1 GHA vs CC Routines — when to use which

| Job type | Runs in | Why |
|---|---|---|
| Deterministic data work (schema validation, journal lint, rule decay timer, file rotation) | **GHA** | No model call needed; cheap, reliable, free tier. Pure Python + git. |
| Agentic work (Analyst reflection, anomaly diagnostics, weekly trend report, PENDING rule proposals) | **CC Routines** | Needs full MCP tools + subagent access + the canonical agent prompts. Running this as a raw Anthropic API call would mean rebuilding the runtime. |
| Notifications / reminders | **GHA → channel** | The session runtime doesn't push. GHA writes a notification (Slack DM, email, mobile push) on schedule or on a condition file changing. |

### 8.2 Initial schedule (seeded — adjust)

| Schedule | Job | Runs in | Reads | Writes |
|---|---|---|---|---|
| Daily 06:00 ET | Morning brief generator | CC Routine | last 24h journal, state, rules tagged `scheduling`, today's calendar (if integrated) | journal `System` entry: brief markdown |
| Daily 22:00 ET | Reflection (PENDING candidates) | CC Routine (Analyst subagent) | last 7d journal | `user_profile.json` PENDING rules (confidence < 0.5) |
| Sunday 18:00 ET | Weekly trend report | CC Routine (Analyst) | last 14d journal | journal `System` entry: report; notification → mobile |
| Hourly | Anomaly check | GHA (deterministic) | today's journal + thresholds in user_profile | notification on threshold breach |
| Nightly 03:00 ET | Rule decay timer | GHA | `user_profile.json` `updated_at` fields | lower confidence on rules unreinforced > 60d; archive > 90d |
| Daily 04:00 ET | Schema lint | GHA | journal/*.md, user_profile.json | fail the build if non-canonical keywords appear (per `schemas/journal_entry.schema.md`) |

### 8.3 Memory-update pipeline (concrete)

This is the journal → memory loop we discussed, mapped to the schedule above:

1. **Capture** (interactive, all day) — verbatim `User` entries via the `UserPromptSubmit` hook; structured `dashboard` entries via the dashboard's API.
2. **Reflect** (22:00 Routine) — Analyst reads the last 7 days, emits a list of `MemoryAction` deltas. Auto-applies at PENDING confidence; queues anything ≥ 0.5 for human review.
3. **Surface** (dashboard, async) — PENDING list appears as a review queue. User taps approve/reject; approval bumps confidence ≥ 0.5.
4. **Reinforce** (next Reflect cycle) — repeated observation bumps `updated_at` and confidence.
5. **Decay** (03:00 GHA) — rules unreinforced for 60d → confidence drop; 90d → archive.

The journal is the audit log throughout — every job's apply/reject action writes a `System` entry.

### 8.4 [INPUT NEEDED]
- Confirm or adjust the schedule in §8.2.
- Reminder channel: Slack DM, email, mobile push (Pushover / ntfy / Apple Push), or just write to the dashboard and rely on the user opening it?

---

## 9. Open questions / decisions log

> _Append as we go. Each entry: date, question, decision, rationale._

- **2026-05-27** — Primary surface? → **CC mobile (flexible) + dashboard (structured)** — User input; Slack server deprecated as primary.
- **2026-05-27** — Periodic work owner? → **GHA for deterministic, CC Routines for agentic** — User input.
- **2026-05-27** — Slack server fate? → **Deprecate as primary; keep as optional notification channel** — Implied by mobile-first.
- **2026-05-27** — Dashboard deployment shape? → _pending §7.3 input_
- **2026-05-27** — Reminder channel? → _pending §8.4 input_
- **2026-05-27** — Privacy posture for cloud-ephemeral sessions handling personal data? → _pending §4.5 input_

---

## 10. Out of scope (for now)

> _Things we've explicitly deferred. Write them down so they don't keep coming back as "wait, should we…?"_

- **Voice input** — defer until mobile + dashboard prove the flow.
- **Wearable integration** — manual logging first, automate only after the manual habit sticks.
- **Multi-user** — single user; no auth complexity beyond a personal token.
- **Slack-first features** — Slack is now a notification channel, not a UX surface. No new Slack-specific behavior.
