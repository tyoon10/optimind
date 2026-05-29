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

- **Claude mobile / web app — PRIMARY.** Interactive logging, Q&A, consults, and feedback run in a **cloud** Claude Code session connected to the `optimind-journal` GitHub repo. The agent reads/writes the journal, daily logs, profile, and state directly (built-in Read/Write/git) following `optimind-journal/CLAUDE.md` + the canonical schemas. **No local machine, no server, nothing running 24/7.**
  - Constraint (confirmed against the docs): cloud CC **cannot** read a repo's `.mcp.json` stdio tools or run `.claude/settings.json` hooks — those are CLI-only. So the structured-logging contract is encoded as **CLAUDE.md instructions + schemas**, not MCP tools, and there is **no `UserPromptSubmit`/`Stop` hook** in cloud (verbatim logging and git-sync are agent-followed per CLAUDE.md, not runtime-guaranteed).
- **Dashboard — structured capture.** A static PWA at `optimind/dashboard/` (Cloudflare Pages) that writes to `optimind-journal` via the **GitHub API** from the browser. Serverless — no backend.
- **Scheduled — CC Routines + GitHub Actions.** Morning brief / reflection / weekly review run as **cloud CC Routines**; deterministic jobs (decay, lint) run as **GHA**. Both are cloud; neither needs a local host.
- **Slack — REMOVED.** The user no longer uses Slack. `optimind-sdk/src/server.py` + `slack_format_hook` + `slack-bolt`, and the legacy `optimind/src/` v1 tree, are slated for deletion (see §10.3). Not a notification channel.
- **Local `claude` CLI — dev only.** The stdio MCP server (`.mcp.json` → `bin/optimind_mcp_server.py`) and the `SessionStart` bootstrap hook are for local development/testing. They are **not** on the production cloud path.

### Capabilities

> **Cloud-reality note (2026-05-28 replan):** the `mcp__optimind__*` tools and the `UserPromptSubmit`/`Stop` hooks below are the **local-CLI / reference** layer. They do **not** run in the cloud (primary) surface. In cloud, the same behaviors are achieved by the agent following `optimind-journal/CLAUDE.md` + writing files to match the schemas. `src/tools/*.py` (esp. `do_log_field`) is the **canonical reference algorithm** the CLAUDE.md instructions and the dashboard JS both mirror.

| Capability | Implementation |
|---|---|
| Multi-day journal read | `mcp__optimind__get_recent_journal`, `mcp__optimind__search_journal` |
| Verbatim user-input logging | `UserPromptSubmit` hook → `journal/YYYY-MM-DD.md` (runtime-guaranteed, not model-discretionary) |
| Agent-written log entries | `mcp__optimind__log_entry` (model-chosen content, with dedup) |
| State (mode + constraints + focus) | `get_state` / `set_state` over `state.json`; modes: `STANDARD`, `EXAM_MODE`, `DEEP_WORK`, `RECOVERY` |
| Preference rules | `get_rules` / `add_rule` / `delete_rule` over `user_profile.json`; PENDING semantics at confidence `< 0.5` |
| Structured daily logs | _not yet implemented — see §7.3 for proposed `daily/YYYY-MM-DD.json` artifact_ |
| Dashboard → journal mirror | _not yet implemented — see §7.5 dual-write contract_ |
| Today's protocol | _not yet implemented — see §7.4_ |
| Long-term memory promotion from logs | _partial — see §7.5 + §8.3 (reflection must read both journal AND daily files)_ |
| Subagent delegation | `nutritionist`, `scheduler`, `analyst` defined in `.claude/agents/` (generic) + override layer in optimind-journal |
| Web search | Enabled on main + nutritionist + analyst |
| Git sync of journal | `sync_hook` commits + pushes the optimind-journal repo after each turn |

### Not yet built (prioritized after §4.6 + §7 + §8 decisions)

**Near-term, unblocks the new architecture (in dependency order):**
1. **`schemas/daily_log.schema.json`** — formal schema for `daily/YYYY-MM-DD.json` (§7.3). Nothing else can land cleanly without this.
2. **Daily-log MCP tools with dual-write** — `get_daily`, `log_field` (sleep/meal/caffeine/routine/workout), `set_protocol`. **Every `log_field` write must also append a `Dashboard`-role line to `journal/<date>.md`** (§7.5). Read/write via `OPTIMIND_JOURNAL_PATH`.
3. **`SessionStart` hook** in optimind that clones/pulls optimind-journal and sets `OPTIMIND_JOURNAL_PATH` — without this, CC mobile sessions can't see personal data.
4. **`.mcp.json`** at repo root so any CC session auto-registers the optimind MCP server.
5. **Morning brief Routine** — generates today's `protocol` (§7.4). Validates the whole pipeline end-to-end before the dashboard ships.
6. **Dashboard MVP — "Today" view only** — protocol checklist + the four logging forms (sleep, meal/caffeine, routine, workout). Calls the dual-write tools from item 2. No trends, no rule mgmt yet.
7. **Scheduled-jobs scaffolding** — `.github/workflows/` for the GHA jobs; a `routines/` directory for CC Routine prompts (per §8).
8. **Reflection pipeline** — `scripts/reflect.py` that the 22:00 Routine invokes; reads **both** `journal/*.md` and `daily/*.json` (§7.5); emits `MemoryAction` deltas applied via existing tools.

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

OptiMind is **fully cloud-native** — no local machine, no server kept alive. Everything runs in Anthropic's cloud + GitHub.

| Mode | Runs in | Triggers | Owns | Tooling |
|---|---|---|---|---|
| **Interactive** | **Cloud CC session connected to `optimind-journal`** | User opens the Claude mobile/web app | Logging, Q&A, consults, feedback | Built-in Read/Write/git + `CLAUDE.md` instructions + schemas. **No MCP tools, no hooks** (cloud constraint). |
| **Structured capture** | Dashboard PWA (Cloudflare Pages, static) | User taps a control | Validated fields → `optimind-journal` via GitHub API | Browser + Octokit; serverless |
| **Scheduled** | CC Routines (cloud) + GHA | Cron | Morning brief, reflection, weekly review (Routines); decay/lint (GHA) | Routines: same as Interactive (file-I/O). GHA: deterministic scripts |

Key consequences of the cloud constraint (confirmed against the Agent SDK + Claude Code docs):
- **`.mcp.json` stdio servers and `.claude/settings.json` hooks are CLI-only** — they do not run in cloud. The interactive agent has only built-in tools + `CLAUDE.md`.
- **The structured-logging "tools" are CLAUDE.md instructions**, not `log_field`/`set_protocol` MCP calls. The Python tools (`src/tools/*.py`) remain the **reference implementation + tests + local-CLI tooling**, and the basis for a future remote-HTTP MCP server *if* hosting is ever wanted (explicitly deferred — it would reintroduce a 24/7 host).
- **No runtime-guaranteed verbatim logging or auto-sync in cloud** (those were `UserPromptSubmit`/`Stop` hooks). In cloud they are agent-followed per `CLAUDE.md`. If a hard verbatim guarantee is later required, it needs the CLI/hook path or a server — out of scope for the cloud-only v1.

Each interactive session is **ephemeral**: a fresh cloud container with the `optimind-journal` repo, then the agent boots from `CLAUDE.md`. No cross-session in-memory state — everything durable lives in `optimind-journal` (committed to GitHub).

---

## 5. End-to-end flows **[INPUT NEEDED — partially seeded]**

> _For each flow: name it, list the trigger, the steps from user POV, the success outcome, and the failure mode. Aim for 5–10 concrete flows; we'll prioritize from there._
>
> _The flows below are seeds — examples of the kind of thing to define. Replace, reorder, delete, expand._

### Flow A: Morning brief & protocol generation **[GROUNDED — partial]**
- **Trigger:** 05:55 ET CC Routine runs (before user wakes).
- **Steps (system):**
  1. Routine reads `state.json`, `user_profile.json` rules tagged `scheduling` / `routine`, last 24h `journal/*.md`, any mobile_override from yesterday's session.
  2. Generates `protocol.items[]` for today's `daily/<date>.json` (per §7.4).
  3. Writes a `System` entry to today's journal: one-line summary + a link/anchor to the daily file.
- **Steps (user, ~06:30):**
  1. Opens dashboard "Today" view → sees protocol as an ordered checklist with time windows.
  2. (Optional) Reads brief markdown on mobile if they want narrative + reasoning.
- **Success:** Protocol exists by wake; user has a single screen showing today's plan within 5 seconds of opening dashboard.
- **Failure mode:** Routine didn't run (no protocol) → dashboard shows default; mark it visually so user knows it's not personalized. Protocol exists but is generic / ignores recent journal context → tune the Routine's reading scope, not the prompt.

### Flow B: In-the-moment logging **[ANSWERED]**
- **Trigger:** Event happens (woke up, ate, finished workout, took supplement).
- **Steps:**
  - **Structured (default):** Dashboard → tap the relevant row in "Today" → form prefilled with `time = now` → adjust + submit. API dual-writes (§7.5): `daily/<date>.json` (structured) + `journal/<date>.md` `Dashboard`-role mirror.
  - **Flexible (when structured doesn't fit):** Open CC mobile → "logged: cold shower 7:35, felt foggy after". Session writes verbatim to `journal/<date>.md` (UserPromptSubmit hook) AND parses the structured part into `daily/<date>.json` via a `log_field` tool.
- **System reads:** existing `daily/<date>.json` for dedup; rules for validation (e.g., "caffeine after 2 PM" rule → warn).
- **System writes:** see Steps above; if validation surfaces a rule deviation, an `Agent` journal entry capturing it.
- **Long-term memory:** Both paths feed the nightly reflection (§7.5, §8.3) — no orphan inputs.
- **Success:** Structured log < 3 taps; flexible log < 10s including the rule-check feedback.
- **Failure mode:** Form has too many required fields → user abandons. Mitigation: every field is optional except the one being logged.

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
**[ANSWERED]**

Two responsibilities, equal weight:

**(a) Easy structured logging.** Tap-driven entry for the things that are tedious to type:

| Domain | Fields |
|---|---|
| Sleep | `bedtime`, `wake_time`, `sleep_quality` (0–10 or label) |
| Nutrition | `meal` (time + items), `caffeine` (time + amount), `snack` (time + items) |
| Routine checklist | `sunlight_exposure`, `cold_shower`, `meditation` (each: done/skipped + optional time + optional duration) |
| Workout | `time`, `duration`, `type` (strength / cardio / mobility / other), optional notes |

These are daily-resetting fields with a fixed schema — exactly the kind of capture that doesn't fit a chat interface. See §7.4 for the underlying data model.

**(b) Display and monitor today's protocol.** A single "Today" view that shows the user what they're supposed to do, in what order, and tracks completion as logs come in. The protocol is:
- **Generated** from current goals (§3), durable rules tagged `scheduling`, and `state.json` mode.
- **Overridable** for today via CC mobile (e.g., "skip workout — I'm sick"). Overrides persist only for today's `daily/<date>.json`.
- **Default** when no override exists: a baseline derived from rules.

The protocol view IS the dashboard home. Logging happens inline against it: each row is "expected → actual" and the user taps a row to log completion.

Rule of thumb: **rules describe intent; protocol describes today's plan; daily log describes what happened.** Three artifacts, three timescales.

### 7.2 Views (refined)

**Primary — the home screen, used daily:**
- **Today** — current state badge (mode + constraints), today's protocol as a checklist (expected vs actual per item), inline log capture for sleep / meals / caffeine / routine / workout. Time-of-day ordering: morning routine at top, evening at bottom.

**Secondary — used weekly or on-demand:**
- **Trends** — sleep, energy, caffeine, workouts plotted over 30 / 90d (data sourced from `daily/*.json`).
- **Rules** — sortable list with confidence + `updated_at`; PENDING review queue at top with one-tap approve / reject (per §8.3).

**Tertiary — power users / debugging:**
- **Journal browser** — date picker, grep, role filter (User / Agent / System).
- **Memory diff** — full Analyst-proposed deltas with rationale.

### 7.3 Data model — `daily/YYYY-MM-DD.json` **[NEW ARTIFACT — proposed]**

A new file per day in optimind-journal, alongside the verbatim `journal/YYYY-MM-DD.md`. Holds the structured dashboard input plus today's protocol. Will need a new schema (`schemas/daily_log.schema.json`) before implementation.

Proposed shape (illustrative — to be ratified in the schema):

```json
{
  "schema_version": "1.0",
  "date": "2026-05-27",
  "tz": "America/New_York",
  "protocol": {
    "generated_at": "2026-05-27T05:55:00-04:00",
    "source": "default | mobile_override | rule_derived",
    "items": [
      {"id": "sunlight",   "expected_window": "06:30-07:30", "duration_min": 10},
      {"id": "cold_shower","expected_window": "07:00-08:00"},
      {"id": "meditation", "expected_window": "07:30-08:00", "duration_min": 10},
      {"id": "workout",    "expected_window": "08:00-09:30", "type": "strength"},
      {"id": "deep_work",  "expected_window": "09:30-12:00", "duration_min": 150}
    ]
  },
  "log": {
    "sleep":   {"bedtime": "23:14", "wake_time": "06:42", "quality": 7},
    "meals":   [{"time": "08:30", "items": "eggs, oats, blueberries"}],
    "caffeine":[{"time": "08:14", "amount_mg": 95, "source": "espresso"}],
    "snacks":  [],
    "routine": {
      "sunlight":   {"done": true,  "time": "07:10", "duration_min": 12},
      "cold_shower":{"done": true,  "time": "07:35"},
      "meditation": {"done": false}
    },
    "workouts":[{"time": "08:05", "duration_min": 50, "type": "strength"}]
  }
}
```

Why a separate file (not front-matter on the markdown journal or new fields in user_profile.json):

- **Different timescale.** journal is append-only verbatim; user_profile is durable; daily is daily-resetting structured. Mixing them violates the role contract (§ journal_entry.schema.md).
- **Different writer.** journal is written by the runtime + verbatim hook; user_profile by rule tools; daily by the dashboard API + a few targeted tools.
- **Different reader.** Trends and protocol-monitoring read `daily/*.json` directly without parsing markdown.

The journal still gets a one-line `System` summary when a daily log is finalized — preserving the audit-log property.

### 7.4 The "protocol for the day" concept **[NEW — proposed]**

A derived plan, regenerated each morning:

| Input | Role |
|---|---|
| `user_profile.json` rules tagged `scheduling` or `routine` | Standing intent (e.g., "morning sunlight within 30min of wake") |
| `state.json` mode + constraints | Mode-shaping (EXAM_MODE → drop workout, extend deep work) |
| Goals from §3 | Long-horizon shaping (training plan, sleep targets) |
| Calendar (future integration) | Hard time windows |
| Mobile override from yesterday's CC mobile chat | "Tomorrow skip workout, I'm flying" |

Generation owner: the **morning brief Routine** (§8.2) writes `protocol` into today's `daily/<date>.json` at ~05:55 ET. Dashboard reads that file when the user opens it.

Override mechanism: the user tells CC mobile "today, skip X and add Y". The session writes an override into `daily/<date>.json` (the next morning's Routine sees `source: mobile_override` and respects it). If the dashboard shows protocol items, completed/incomplete state lives in `log.routine.*` — completion is logged when the user taps a checkbox or when the agent matches a journal entry.

If nothing has been generated and no override exists, the dashboard falls back to a hard-coded **default protocol** (basic morning + evening anchors) so the dashboard is never empty on day one.

### 7.5 Long-term memory: ensuring every log reaches `user_profile.json` **[ANSWERED]**

The concern: dashboard inputs that only land in `daily/<date>.json` would never feed the rule-promotion pipeline, because reflection (§8.3) reads the journal. Closing this gap requires two contracts, both runtime-enforced:

**(1) Dual-write on every structured field write (`log_field`), regardless of surface.** Each write goes to *both*:
- `daily/YYYY-MM-DD.json` — the structured record (authoritative for numeric values).
- `journal/YYYY-MM-DD.md` — a mirror line under role `Dashboard` (canonical audit log).

The mirror format is fixed: `[<field>] <value>` (one line per field written). Defined in `schemas/journal_entry.schema.md`. The `log_field` tool performs both writes — neither is optional — so the guarantee holds whether the field was captured by the dashboard API, by the chat agent calling `log_field`, or by any future surface. The `Dashboard` role marks *structured capture*, not the dashboard surface specifically (decision 2026-05-28). This means **the journal alone is sufficient to reconstruct what the user logged**, regardless of surface.

**(2) Reflection reads both sources.** The nightly reflection Routine (§8.2) reads:
- `journal/*.md` (last 7d) — for verbatim user input, agent reasoning, system events. Provides context and natural-language signal.
- `daily/*.json` (last 14d) — for quantitative trends (sleep quality moving average, caffeine timing distribution, routine compliance rate). Provides numeric signal.

Both feed the same output: a list of `MemoryAction` deltas applied to `user_profile.json`.

**The unified promotion path (works identically for mobile + dashboard inputs):**

```
              ┌─────────────────┐         ┌────────────────────┐
mobile ──────▶│ journal/<d>.md  │────┐    │                    │
              │ (User role)     │    │    │  Reflection        │      ┌─────────────────────┐
              └─────────────────┘    │    │  Routine (nightly) │      │  user_profile.json  │
                                     ├───▶│                    │─────▶│  rules (durable)    │
              ┌─────────────────┐    │    │  reads journal/    │      │                     │
dashboard ───▶│ daily/<d>.json  │    │    │  AND daily/        │      │  PENDING (< 0.5)    │
              │ (structured)    │────┤    │                    │      └─────────────────────┘
              └─────────────────┘    │    └────────────────────┘                │
                       ▲             │                                          │
                       │             │                                          ▼
              ┌─────────────────┐    │                                  ┌───────────────┐
              │ journal/<d>.md  │◀───┘                                  │ Dashboard     │
              │ (Dashboard role)│                                       │ PENDING queue │
              │ — mirror write  │                                       │ (one-tap      │
              └─────────────────┘                                       │  approve/rej) │
                                                                        └───────────────┘
```

What this gives:
- **No orphan inputs.** Every keystroke and every tap is in the journal and (if structured) the daily file. Reflection sees all of it.
- **Single audit log.** "What did the user do at 8am?" is one grep against `journal/*.md`, never two.
- **Quantitative + qualitative signal in the same pipeline.** "User logged caffeine after 14:00 on 5 of last 7 days" (from `daily/*.json`) and "User said 'I'm trying to cut afternoon coffee'" (from `journal/*.md`) can both inform the same PENDING rule.
- **Surface-agnostic.** Adding a third surface later (voice, wearable) just means another writer that produces journal entries; reflection doesn't change.

What it does NOT do:
- Auto-promote dashboard data into durable rules without reflection. Single observations are still observations, not rules — the N-of-M threshold from §8.3 still applies.
- Override the user. Promotions ≥ 0.5 confidence still surface in the PENDING queue for one-tap review.

### 7.6 Tech choices **[ANSWERED — recommendation pending 4 open decisions]**

**Workflow anchor.** The dashboard's primary loop is event capture from a phone, 10–30 times a day, often one-handed and on the move:

```
unlock → tap home-screen icon → see today's protocol
→ tap "caffeine" → time prefilled to now → adjust → submit
→ confirmation flashes → close. < 5s, < 4 taps.
```

Three things determine whether this works in practice: **write latency** (< ~1s to feel snappy), **mobile-native UX** (installable PWA, native time pickers, no full-page reruns), and **offline reliability** (subway case must not drop writes).

**Axes of choice.** Every option is a combination of:
- Frontend type — static SPA vs server-rendered.
- Where writes go — direct GitHub API vs backend wrapping the existing MCP tools.
- Hosting — static (Pages/Cloudflare), serverless container (Fly/Railway), self-hosted, or app-store native.
- Auth — GitHub OAuth, PAT in localStorage, shared secret to backend, or zero-trust gating.

#### Options compared

| # | Stack | Latency | Ops burden | UX | Reuses Python tools | Fit |
|---|---|---|---|---|---|---|
| **1** | **Static PWA + GitHub API (no backend)** — SvelteKit + Octokit, Cloudflare Pages, GitHub OAuth | 400–800 ms / write (two PUTs) | None — git is the infra | Native PWA feel | No (re-implements dual-write in JS) | **Recommended v1** |
| **2** | **Static PWA + tiny FastAPI backend** — same frontend; backend wraps existing MCP tools, persistent clone of optimind-journal, batched commits | Sub-100 ms | One small service to keep up (Fly/Railway free tier sleeps; ~$5/mo always-on) | Same as 1, snappier | **Yes** — single source of truth for write logic | **Migrate target when needs exceed 1** |
| 3 | **Streamlit / Reflex / Gradio** — Python-only, server-rerun on each interaction | ~1–2 s | Low (managed cloud) | Poor on mobile, not PWA-installable | Yes | Prototype-only; do not ship |
| 4 | **Local PWA + Tailscale (self-hosted)** — option 2 stack, backend on Mac or Pi | <50 ms on LAN, dead off-network | Highest — need a 24/7 host | Same as 2 | Yes | Only if you already run a home server |
| 5 | **Native iOS/Android (Expo/RN)** — true native app | Sub-100 ms | App-store overhead, build pipeline | Best possible (widgets, lock-screen, push) | Via backend | Defer; PWA is 90% there at 10% effort |

#### Recommendation

**Start with Option 1. Migrate to Option 2 when you have a reason.**

Why Option 1 first:
- Matches the operational model you've already chosen (git-as-infrastructure, no long-running server). Adding a backend pulls focus from product work.
- 400–800 ms is fine for tap-and-close logging. The slowness only matters for UX you're not building (real-time sliders, sub-second analytics).
- Validates the entire flow (mobile UX, dual-write, schema correctness) without infra. If a field is wrong, you find out without paying a deployment tax.
- Sunk cost near zero. If it doesn't work after two weeks of real use, the frontend ports unchanged to Option 2 — only the write target changes.

Migration triggers (when to move to Option 2):
- You want features needing server compute (meal-photo OCR, Apple Health pull, embeddings).
- The two-PUT latency or the commit-log noise becomes an irritant.
- You want one backend serving dashboard + Routines + notifications.

#### Stack picks for Option 1

| Concern | Pick | Why |
|---|---|---|
| Framework | **SvelteKit** (static adapter) | Small bundle, strong PWA story, less ceremony than Next |
| Styling | **Tailwind** + a small mobile component lib (Radix headless) | Mobile-first without fighting a design system |
| Git ops | **Octokit (GitHub REST)** in the browser | Two PUTs per submission; avoids `isomorphic-git` bundle weight |
| Auth | **GitHub OAuth (PKCE)** scoped to optimind-journal | No shared secret, no server needed |
| Hosting | **Cloudflare Pages** | Faster than GH Pages, free, easy custom domain |
| PWA | **vite-plugin-pwa** | Service worker → offline + home-screen install |
| Offline queue | **Dexie (IndexedDB)** | Queue writes when offline, flush on reconnect |

Avoid in v1: Next.js App Router (overkill), Remix, any backend, ORMs, auth libraries beyond Octokit, paid component libraries.

#### Open decisions (block kickoff)

1. **Commit-log hygiene.** Accept the noisy git log (one commit per submission) or add a nightly GHA on optimind-journal that squashes the day's daily-log commits into one? *Lean: accept v1, add squash later if it bothers you.*
2. **OAuth vs PAT.** GitHub OAuth PKCE is the right answer; a long-lived PAT in localStorage saves ~1 dev day. Single-user, your risk. *Lean: PAT for v0, swap to OAuth before any real use.*
3. **Domain.** Custom subdomain (`optimind.<your-domain>`) vs `.pages.dev`? Affects OAuth callback config. *Lean: `.pages.dev` for v0; custom when domain matters.*
4. **Offline policy.** Service worker + Dexie queue from day one, or require connectivity in v1? *Lean: build offline from day one — subway-logging is a core use case and bolting it on later is expensive.*

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
| Daily 05:55 ET | Morning brief + protocol generation | CC Routine | last 24h journal, state, rules tagged `scheduling`/`routine`, mobile_override from yesterday | `daily/<date>.json` `protocol` block; journal `System` entry: brief markdown |
| Daily 22:00 ET | Reflection (PENDING candidates) | CC Routine (Analyst subagent) | last 7d journal | `user_profile.json` PENDING rules (confidence < 0.5) |
| Sunday 18:00 ET | Weekly trend report | CC Routine (Analyst) | last 14d journal | journal `System` entry: report; notification → mobile |
| Hourly | Anomaly check | GHA (deterministic) | today's journal + thresholds in user_profile | notification on threshold breach |
| Nightly 03:00 ET | Rule decay timer | GHA | `user_profile.json` `updated_at` fields | lower confidence on rules unreinforced > 60d; archive > 90d |
| Daily 04:00 ET | Schema lint | GHA | journal/*.md, user_profile.json | fail the build if non-canonical keywords appear (per `schemas/journal_entry.schema.md`) |

> **Cloud-native note (replan):** all "CC Routine" jobs run in the **cloud** (claude.ai scheduled agents) connected to `optimind-journal`, doing **file-I/O** per `CLAUDE.md` — no local host. GHA jobs run on GitHub's runners. The `notification → mobile` cells are superseded: reminders are **dashboard-pull** (the Routine writes a `System` brief / anomaly note; the user sees it on next open). No push channel until proven necessary (§9, §11).

### 8.3 Memory-update pipeline (concrete)

This is the journal → memory loop, mapped to the schedule above. The data-flow diagram and dual-write contract live in §7.5; this is the temporal sequence:

1. **Capture** (interactive, all day):
   - Mobile → `UserPromptSubmit` hook writes `User`-role line to `journal/<d>.md` (verbatim).
   - Dashboard → API dual-writes to `daily/<d>.json` (structured) **and** `journal/<d>.md` as `Dashboard`-role line (mirror). Both writes are atomic per submission.
2. **Reflect** (22:00 Routine) — Analyst reads **both** `journal/*.md` (last 7d) and `daily/*.json` (last 14d). Emits `MemoryAction` deltas. Auto-applies at PENDING confidence (< 0.5); queues anything ≥ 0.5 for human review.
3. **Surface** (dashboard, async) — PENDING list appears as a review queue. User taps approve/reject; approval bumps confidence ≥ 0.5.
4. **Reinforce** (next Reflect cycle) — repeated observation bumps `updated_at` and confidence on existing rules.
5. **Decay** (03:00 GHA) — rules unreinforced for 60d → confidence drop; 90d → archive.

The journal is the audit log throughout — every job's apply/reject action writes a `System` entry, and every dashboard submission is mirrored as a `Dashboard` entry.

### 8.4 [INPUT NEEDED]
- Confirm or adjust the schedule in §8.2.
- Reminder channel: Slack DM, email, mobile push (Pushover / ntfy / Apple Push), or just write to the dashboard and rely on the user opening it?

---

## 9. Open questions / decisions log

> _Append as we go. Each entry: date, question, decision, rationale._

- **2026-05-27** — Primary surface? → **CC mobile (flexible) + dashboard (structured)** — User input; Slack server deprecated as primary.
- **2026-05-27** — Periodic work owner? → **GHA for deterministic, CC Routines for agentic** — User input.
- **2026-05-27** — Where does structured daily data live? → **New `daily/YYYY-MM-DD.json` file in optimind-journal, separate from the verbatim journal markdown** — Different timescale, writer, and reader from the existing artifacts (§7.3).
- **2026-05-27** — How is today's plan represented? → **`protocol` block inside `daily/<date>.json`, generated each morning by the brief Routine, overridable via mobile chat** — §7.4. Three-tier semantics: rules = intent, protocol = today's plan, log = actual.
- **2026-05-27** — How do dashboard logs reach long-term memory? → **Dual-write on every submission (`daily/<date>.json` structured + `journal/<date>.md` `Dashboard`-role mirror); reflection reads both** — §7.5. Closes the orphan-input gap; journal remains the canonical audit log across all surfaces.
- **2026-05-28** — Dashboard tech stack? → **Option 1 first (static PWA + GitHub API), migrate to Option 2 (FastAPI backend) when triggered by latency, server-compute needs, or consolidation** — §7.6. Stack: SvelteKit static + Tailwind + Octokit + Cloudflare Pages + vite-plugin-pwa + Dexie offline queue + GitHub OAuth (PKCE).
- **2026-05-28** — §7.6 sub-decisions → **commit-log hygiene: accept noise v1; OAuth vs PAT: PAT only for a throwaway local spike, OAuth (PKCE) before it touches the phone; domain: `.pages.dev` v0; offline: DEFERRED to iteration 2** (connectivity-required for the first validation spike; keep the write path queue-shaped so the SW+Dexie queue is a clean retrofit). Offline flipped from §7.6's "day one" lean per the user's min-build stance.
- **2026-05-28** — Dashboard repo placement → **`optimind/dashboard/` subdir** (user). Keeps the dashboard reading the canonical schemas directly (single source, no drift); accepts mixed Node/Python toolchain in one repo. Split into its own repo later only if deploy coupling annoys.
- **2026-05-28** — `schemas/user_profile.schema.json` was silently dropped from the initial commit by the `*.json` gitignore rule. → **Added explicit gitignore negations for schema/config JSON; force-committed the file; documented the gotcha in §10.7 and CLAUDE.md** — Prevents the same silent drop for `daily_log.schema.json`, `.mcp.json`, and the dashboard `package.json` on the build list.
- **2026-05-28** — Is the `Dashboard` journal role tied to the dashboard *surface*? → **No — `Dashboard` marks any structured `log_field` write, regardless of surface (dashboard API, chat agent calling `log_field`, or a future surface).** Redefined the role contract in `journal_entry.schema.md` and generalized §7.5(1). Rationale: `log_field` is a single surface-agnostic tool that does the dual-write; once CC mobile sessions gain the tool (Tasks 3–4) the agent should call it whenever the user states a structured fact, so chat-logged data reaches the `daily/*.json` trends layer and reflection — not only dashboard taps. Tagging the mirror by surface would fragment the contract and orphan chat-logged structured data. The agent directive lives in `optimind-sdk/CLAUDE.md` (Tools Available).
- **2026-05-28** — How is the journal bootstrapped at session start, and how do the MCP tools reach a fresh `claude` CLI session? → **Corrected the Task 3/4 approach after confirming against the Agent SDK + Claude Code docs: (i) `SessionStart` is NOT a Python Agent SDK callback hook (TypeScript-only, like `SessionEnd`); (ii) an in-process `create_sdk_mcp_server` CANNOT be exposed via `.mcp.json`.** Therefore Task 3 = a `.claude/settings.json` `SessionStart` *shell* hook (picked up via the existing `setting_sources=["project"]`) that clones/pulls the journal and writes the resolved path to `$CLAUDE_ENV_FILE`, plus a startup `ensure_journal()` for the SDK-app process (sets `os.environ` before first tool call). Task 4 = a *standalone* stdio MCP server (built on the `mcp` package, importing the existing tool logic) launched by `.mcp.json` — not the in-process SDK server. Env reaches the MCP server process via the `.mcp.json` `env` block. NOTE: `$CLAUDE_ENV_FILE` only affects Bash tool calls, not the MCP server's process env — hence the `.mcp.json` `env` block is the real path-delivery mechanism for the tools.
- **2026-05-28** — Live verification caught the chat agent logging a free-text caffeine value (no mg), producing a schema-invalid `{time, value}` entry (`amount_mg` required, extra `value` key forbidden). → **Keep `daily_log.schema.json` strict; strengthen agent guidance instead of relaxing the schema.** The `log_field` tool descriptions (`src/tools/daily.py` + `src/mcp_server.py`) and `optimind-sdk/CLAUDE.md` now instruct the agent to ALWAYS pass a structured object for event categories and to ESTIMATE the numeric field (e.g. `amount_mg`) from the source when the user doesn't state it. Rationale: preserves the dashboard's structured-data guarantee and keeps the daily file schema-valid; the chat path leans on the agent's estimates (flagged as estimates via `source`). The standalone MCP server's tool description is the channel that actually reaches a CLI session, so it must carry the same guidance as the SDK `@tool`.
- **2026-05-28 — REPLAN (cloud-native).** User's primary interface is now the **Claude mobile/web app (cloud CC) connected to `optimind-journal`**; they want zero local-machine / zero-24/7-host operation, and have stopped using Slack. Confirmed against the docs: **cloud CC cannot read `.mcp.json` stdio tools or run `.claude/settings.json` hooks** (CLI-only), and loads only the repo-root `CLAUDE.md`. → **Re-center the architecture on cloud file-I/O:** the interactive agent and scheduled Routines do the structured dual-write themselves (Read/Write/git) guided by `optimind-journal/CLAUDE.md` + the schemas. The Python tools (Tasks 2/4) and the SessionStart hook (Task 3) are **CLI/dev-only + the canonical reference**, not the production path. A **remote-HTTP MCP server is explicitly deferred** (it would reintroduce a 24/7 host). Capture = cloud CC (chat) + dashboard PWA (GitHub API); scheduled = CC Routines + GHA; data = GitHub. Consequence to track: verbatim `User`-line logging and git-sync are **no longer runtime-guaranteed** in cloud (they were hooks) — now agent-followed per `CLAUDE.md`.
- **2026-05-28** — Reminder channel (§8.4) → **dashboard-pull (active check), no notification infra.** The morning-brief Routine writes the `protocol` + a `System` brief; the dashboard surfaces it; the user checks in. No push, no Slack (removed), no new dependency. Revisit a push channel only if adherence data shows it's needed (§11).
- **2026-05-28** — Slack → **REMOVED** (user hasn't used it in a while). Delete the active surface (`optimind-sdk/src/server.py`, `hooks/slack_format_hook.py`, Slack tokens in `config.py`, `slack-bolt` dep, Slack refs in `agent.py`/`subagents`) and the legacy v1 tree (`optimind/src/`). Tracked as a build task (§10.3).
- **2026-05-27** — Slack server fate? → **~~Deprecate as primary; keep as optional notification channel~~ Superseded: removed entirely (see 2026-05-28 Slack → REMOVED).**
- **2026-05-27** — Dashboard deployment shape? → _pending §7.3 input_
- **2026-05-27** — Reminder channel? → _pending §8.4 input_
- **2026-05-27** — Privacy posture for cloud-ephemeral sessions handling personal data? → _pending §4.5 input_

---

## 10. Handoff to local development (CC in VS Code)

This section is the working guide for the next session that opens both repos in VS Code. Read §2 + §7 + §8 first; then this is the execution plan.

### 10.1 Workspace setup

1. **Clone both repos side-by-side** under a single VS Code workspace (e.g., `~/code/optimind/` and `~/code/optimind-journal/`). The workspace file references both.
2. **Set `OPTIMIND_JOURNAL_PATH`** in `~/code/optimind/optimind-sdk/.env` pointing at the local optimind-journal checkout.
3. **Install deps** for optimind-sdk: `pip install -r optimind-sdk/requirements.txt`. Confirm `python -c "from src.config import journal_root; print(journal_root())"` returns the journal path.
4. **Confirm the merged state** is on `main` for both repos. The current open branch (`claude/funny-lovelace-zZXSP`) carries planning + verbatim-hook + this doc — fold to `main` once reviewed.

### 10.2 Branching strategy

Each task in §10.3 is one feature branch + one PR. Branch names: `feat/<short-name>` for both repos when a task spans them. Use git worktrees if you want CC sessions on different tasks in parallel without thrashing the working tree.

### 10.3 Task order (build list from §2, expanded)

**Reshaped by the 2026-05-28 cloud-native replan.** The production path (interactive + Routines) is **file-I/O driven by `optimind-journal/CLAUDE.md` + the schemas** — cloud CC has no MCP tools or hooks. So the **keystone is Task A** (encode the contract in the journal's CLAUDE.md). Tasks 1–2 are the canonical reference + local-CLI layer; Tasks 3–4 are CLI/dev-only; Task 5 needs a file-I/O reframe.

| # | Task | Status | Repo / notes |
|---|---|---|---|
| **A** | **Port the structured-logging + dual-write contract into `optimind-journal/CLAUDE.md`** — the cloud agent's "tools." On a structured fact: write `daily/<date>.json` (schema-valid, **estimating numeric fields** from given info), append the `### HH:MM \| Dashboard\n[<field>] <value>` mirror line, and commit. Also codify the `User`/`Agent`/`System`/`Dashboard` line conventions. Mirrors `do_log_field`. | **NEW — keystone, do first** | optimind-journal. Replaces MCP tools on the cloud primary path. |
| 1 | `daily_log.schema.json` + test | ✅ PR #5 | The contract the cloud agent writes against. |
| 2 | `daily.py` dual-write + pure core | ✅ PR #6 | Now the **reference algorithm + tests + local CLI**, not the cloud runtime. |
| 2b | `log_field` structured-value guidance | ✅ PR #10 | Estimate numeric fields / reshape incomplete input. Same guidance feeds Task A. |
| 3 | `SessionStart` bootstrap | ✅ PR #8 — **CLI/dev-only** | Not on the cloud path; local clone/pull convenience. |
| 4 | `.mcp.json` + stdio MCP server | ✅ PR #9 — **CLI/dev-only** | Not on the cloud path; basis for a future remote-HTTP MCP server *iff* hosting is ever wanted (deferred). |
| 5 | Morning-brief Routine | ◑ PR #11 — **needs reframe** | A cloud Routine has no `set_protocol` tool → reframe `routines/morning_brief.md` to **write the `protocol` into `daily/<date>.json` via file-I/O** + a `System` brief line. |
| **S** | **Remove Slack** | NEW | Delete `optimind-sdk/src/server.py`, `hooks/slack_format_hook.py`, Slack tokens in `config.py`, `slack-bolt` dep, Slack refs in `agent.py`/`subagents`; and the legacy `optimind/src/` v1 tree. |
| 6 | Dashboard MVP — `optimind/dashboard/` | next | Static PWA (SvelteKit + Cloudflare Pages). **GitHub-API dual-write in an isolated `writeDaily.ts`** (mirrors `do_log_field`). Connectivity-required v1 (offline deferred to iteration 2). "Today" = protocol checklist + sleep/meal/caffeine/workout forms. |
| 7 | Scheduled jobs | after A, 5 | **CC Routines** (cloud) for morning-brief / reflection / weekly review; **GHA** for decay + schema-lint. No push infra (reminders = dashboard-pull). |
| 8 | Reflection pipeline | after 2, 7 | Reads 7d journal + 14d daily; emits `MemoryAction`s applied to `user_profile.json`. Runs as a cloud Routine (Analyst). Dry-run first. |

### 10.4 Parallel-agent strategy

In VS Code you can run multiple CC sessions side-by-side. Useful pairings:

- **Session A (this repo):** Task 1 (schema) → Task 2 (MCP tools). Sequential.
- **Session B (after A finishes task 2):** Task 3 (SessionStart hook) + Task 4 (.mcp.json). Independent; can interleave.
- **Session C (new dashboard repo):** Task 6 (dashboard MVP). Starts the moment Task 2 merges. Can ship before tasks 3/5 land — stub the protocol with hard-coded JSON for local dev.
- **Session D (when 5+6 are stable):** Task 7 (workflows) + Task 8 (reflection script).

### 10.5 Acceptance gates per task

Before merging any task PR:

- **Tasks 1–2:** unit tests around dual-write and schema validation pass; manually inspect a real `daily/<date>.json` write *and* the corresponding `journal/<date>.md` mirror line.
- **Tasks 3–4:** open a fresh CC session in a tmpdir clone of optimind; verify `OPTIMIND_JOURNAL_PATH` resolves and MCP tools appear without manual config.
- **Task 5:** run the Routine prompt against a fixture journal (cp 7 days of fake markdown into a temp journal repo); inspect the generated protocol.
- **Task 6:** install PWA on phone; complete the 5-second tap-and-close flow for each of the 4 logging forms; verify dual-write actually committed to optimind-journal.
- **Tasks 7–8:** dry-run mode shows reasonable proposals against your real journal for ≥1 week before flipping to auto-apply.

### 10.6 What to confirm with the user (you, in chat) before kickoff

Before VS Code CC starts task 1, decide:

- §3 goals (shapes the Morning brief Routine's prompt)
- §7.6 open decisions: PAT-vs-OAuth, custom domain or `.pages.dev`, offline-from-day-one or not, accept commit-log noise or add squash
- §8.4 reminder channel
- Whether the dashboard lives in a new `optimind-dashboard` repo (cleaner separation) or in `optimind/dashboard/` (simpler ops)

Once those answers are in §9 (decisions log), VS Code CC has everything it needs.

### 10.7 Repo gotchas / conventions

Lessons captured from setup so they don't recur:

- **`.gitignore` blanket-ignores `*.json`.** This protects personal data, but it silently swallows schema/config JSON too. Negations are in place for `schemas/*.json`, `.mcp.json`, `package.json`, `tsconfig.json`. **Before committing any new tracked JSON** (e.g. `schemas/daily_log.schema.json` in Task 1, `.mcp.json` in Task 4, the dashboard's `package.json` in Task 6), run `git check-ignore <path>`; if it prints the path, add a negation to `.gitignore` first. `git add` gives no error when it skips an ignored file — always confirm with `git status` that the file actually staged. (This bit us once: `user_profile.schema.json` was dropped from the initial commit and only caught on re-clone.)
- **The runtime resolves data via `OPTIMIND_JOURNAL_PATH`, never hard-coded paths.** Any new tool or hook that touches journal/profile/state must use `src.config.journal_root()`, not a `BASE_DIR/data` path. See `optimind-sdk/CLAUDE.md` → Runtime binding.
- **Timestamps carry the user's offset, never bare UTC `Z`.** Enforced in `user_profile.schema.json` and `journal_entry.schema.md`.
- **The two repos bind at runtime, not build time.** Don't add a hard dependency from optimind on optimind-journal's location; everything flows through the env var and the schemas.

---

## 11. Out of scope (for now)

> _Things we've explicitly deferred. Write them down so they don't keep coming back as "wait, should we…?"_

- **Voice input** — defer until mobile + dashboard prove the flow.
- **Wearable integration** — manual logging first, automate only after the manual habit sticks.
- **Multi-user** — single user; no auth complexity beyond a personal token.
- **Slack** — removed entirely (the user no longer uses it). Not a surface, not a notification channel. Existing Slack code is slated for deletion (§10.3 Task S).
- **Remote / hosted MCP server** — would let cloud CC use the Python tools directly, but requires a 24/7 host. The cloud path uses file-I/O via `CLAUDE.md` instead. Revisit only if tool-guaranteed writes (vs. agent-followed) become necessary.
- **Push notifications** — reminders are dashboard-pull for now. Add a push channel only if adherence data shows it's needed.
- **Runtime-guaranteed verbatim logging in cloud** — was a `UserPromptSubmit` hook (CLI-only). In cloud it's agent-followed per `CLAUDE.md`; a hard guarantee would need the CLI/hook path or a server.
