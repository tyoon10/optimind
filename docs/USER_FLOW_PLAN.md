# OptiMind End-to-End User Flow Plan

> **Status:** Living draft. Sections marked **[INPUT NEEDED]** are awaiting user input. Sections marked **[GROUNDED]** are pre-filled from the codebase as of this commit and may be edited.
>
> **Audience:** This document is the baseline handoff for anyone extending OptiMind across the two repos (`tyoon10/optimind` + `optimind-journal`). When extending the product — building the dashboard, adding interaction surfaces, tuning system prompts — start here, not from the code alone. Two orientation reminders that govern everything below: (1) the **live runtime is cloud Claude Code** on the `optimind-journal` repo — the `optimind-sdk/` Python app is the reference implementation, not the production path; (2) the **active system prompt is `optimind-journal/CLAUDE.md`** — that is where runtime-behavior edits land (§6, §4.8).
>
> **How to use this doc:**
> 1. The user fills in **[INPUT NEEDED]** sections incrementally.
> 2. CC in VS Code reads §1–§4 to ground itself, then §5–§7 to derive concrete work.
> 3. Every feature, dashboard widget, or prompt change should trace back to a flow in §5 — if it doesn't, it's scope creep.

---

## 1. Why this document exists

OptiMind is a **cloud-native** personal-assistant system: an ephemeral Claude Code mobile/cloud session reading and writing a private journal repo (`optimind-journal`), three scheduled cloud Routines, and a static dashboard PWA — no Slack, no server, no 24/7 host. It has the right primitives — a verbatim journal, structured daily logs, a typed `user_profile`, a three-tier knowledge model (§6.6) — and this doc is its *product spec of record*: the living design doc that any new work (dashboard, prompts, new surfaces) traces back to.

This doc captures: the user's goals → desired interactions → end-to-end flows → derived requirements for the system prompt and dashboard. It's the contract between "what I want OptiMind to be" and "what gets built."

> **Architecture lineage.** OptiMind began (v1–v2, Jan–Feb 2026) as a Gemini 3 Flash + LangChain + FastAPI + Slack-Bolt server. v3 (2026-03) migrated to the Claude Agent SDK. **4.0.0 (2026-05-31)** removed Slack and all long-running server scaffolding and re-centered the runtime on cloud Claude Code + the journal repo. **4.1.0 (2026-06-07)** added the three-tier knowledge model (§6.6). The pre-4.0.0 design comparisons that motivated the file-as-memory choice survive as bannered historical records in this `docs/` folder (`ARCHITECTURE_COMPARISON.md`, `ISSUEOPS_EVALUATION.md`, `logging_interface_analysis.md`). See `CHANGELOG.md` for the full record.

---

## 2. Current state (grounded)

**[GROUNDED — current as of 4.1.0]**

### Architecture (two repos)

| Repo | Visibility | Owns |
|---|---|---|
| `tyoon10/optimind` (this repo) | Public | **The system** — canonical `schemas/`, paste-ready `routines/` prompts, generic `.claude/agents/`, the `dashboard/` PWA, the `optimind-sdk/` Python reference implementation, and this design doc |
| `optimind-journal` | Private | **The data** — `CLAUDE.md` (the active cloud system prompt), `user_profile.json`, `state.json`, `comprehensive_memory.md`, `journal/YYYY-MM-DD.md`, `daily/YYYY-MM-DD.json`, personal `.claude/agents/` overrides |

The two bind at **runtime**, two different ways depending on path:
- **Cloud (primary):** the Claude Code session is launched directly on the `optimind-journal` checkout; the journal repo's own `CLAUDE.md` + `.claude/agents/` drive it. No env-var indirection — the session *is* in the journal repo.
- **Local SDK / CLI (reference):** the `optimind-sdk/` Python app discovers the journal via the `OPTIMIND_JOURNAL_PATH` environment variable and applies LSP-style override resolution (base `optimind/.claude/agents/` + journal override layer). See `schemas/optimind_interface.md`.

### Surfaces

- **Claude mobile / web app — PRIMARY.** Interactive logging, Q&A, consults, and feedback run in a **cloud** Claude Code session connected to the `optimind-journal` GitHub repo. The agent reads/writes the journal, daily logs, profile, and state directly (built-in Read/Write/git) following `optimind-journal/CLAUDE.md` + the canonical schemas. **No local machine, no server, nothing running 24/7.**
  - Constraint (confirmed against the docs): cloud CC **cannot** read a repo's `.mcp.json` stdio tools or run `.claude/settings.json` hooks — those are CLI-only. So the structured-logging contract is encoded as **CLAUDE.md instructions + schemas**, not MCP tools, and there is **no `UserPromptSubmit`/`Stop` hook** in cloud (verbatim logging and git-sync are agent-followed per CLAUDE.md, not runtime-guaranteed).
- **Dashboard — structured capture.** A static PWA at `optimind/dashboard/` (Cloudflare Pages) that writes to `optimind-journal` via the **GitHub API** from the browser. Serverless — no backend.
- **Scheduled — CC Routines + GitHub Actions.** Morning brief / reflection / weekly review run as **cloud CC Routines**; deterministic jobs (decay, lint) run as **GHA**. Both are cloud; neither needs a local host.
- **Slack — REMOVED (4.0.0).** The Slack server, `slack_format_hook`, the `slack-bolt` dependency, and the legacy `optimind/src/` v1 tree were deleted in the 4.0.0 cloud-native pivot. Slack is not a surface and not a notification channel.
- **Local `claude` CLI — dev/reference only.** The stdio MCP server (`.mcp.json`) and the `SessionStart` bootstrap hook exist in `optimind-sdk/` for local development/testing of the reference implementation. They are **not** on the production cloud path — cloud sessions cannot load `.mcp.json` stdio tools or run `.claude/settings.json` hooks (CLI-only).

### Capabilities

> **How to read this table.** Two columns, two paths. The **cloud path (primary)** column is how the live system actually does each thing: the agent follows `optimind-journal/CLAUDE.md` + the canonical schemas, using only built-in Read/Write/git tools — **no MCP tools, no hooks** (those are CLI-only and don't run in cloud). The **SDK reference column** is the `optimind-sdk/` Python implementation — the *canonical reference algorithm* + local-CLI tooling that the CLAUDE.md instructions and the dashboard JS both mirror. It is not the production runtime. The single thing to internalize: **in cloud, these behaviors are agent-followed contracts in CLAUDE.md, not runtime-guaranteed hooks.**

| Capability | Cloud path (primary, live) | SDK / local-CLI reference |
|---|---|---|
| Multi-day journal read | Built-in `Read` / `Grep` over `journal/*.md` per the turn-start read levels (§6.5) | `get_recent_journal`, `search_journal` tools |
| Verbatim user-input logging | Agent-followed contract: CLAUDE.md "How to Log" mandates the verbatim `### HH:MM \| User` line before reasoning. **Agent-followed, not runtime-guaranteed.** | `UserPromptSubmit` hook → `journal/*.md` (runtime-guaranteed in the CLI path) |
| Agent-written log entries | Agent writes `### HH:MM \| Agent` entries per CLAUDE.md format | `log_entry` tool (model-chosen content, with dedup) |
| State (mode + constraints + focus) | Agent Reads/Writes `state.json`; modes e.g. `STANDARD`, `EXAM_MODE`, `DEEP_WORK`, `RECOVERY` | `get_state` / `set_state` |
| Preference rules | Agent Reads/Writes `user_profile.json` rules; PENDING semantics at confidence `< 0.5`; schema-validated | `get_rules` / `add_rule` / `delete_rule` |
| Structured daily logs | ✅ Shipped — `daily/YYYY-MM-DD.json` (§7.3), schema `schemas/daily_log.schema.json`; agent dual-writes per CLAUDE.md "Structured Logging" | `daily.py` (`do_log_field`) — reference dual-write algorithm |
| Dashboard → journal mirror | ✅ Shipped — every structured write also appends a `### HH:MM \| Dashboard` mirror line to `journal/*.md` (§7.5 dual-write) | `do_log_field` performs both writes |
| Today's protocol | ✅ Shipped — Morning Brief Routine writes the `protocol` block into `daily/<date>.json` (§7.4) | — |
| Three-tier knowledge model | ✅ Shipped (4.1.0) — rules carry `why_brief` + `mechanism_ref`; mechanism records live in `comprehensive_memory.md`; sync-walk on Reflection (§6.6) | `mechanism.schema.json`; analyst/scheduler/nutritionist override patterns |
| Long-term memory promotion from logs | ✅ Shipped — nightly Reflection Routine reads both `journal/*.md` and `daily/*.json` (§7.5 + §8.3) | — |
| Subagent delegation | `nutritionist` / `scheduler` / `analyst` in `optimind-journal/.claude/agents/` (the cloud session loads the journal's agents directly) | generic base layer in `optimind/.claude/agents/` + LSP override resolution |
| Web search | Enabled on the main agent + nutritionist + analyst | same |
| Git sync of journal | Agent-followed contract: CLAUDE.md "Critical write contracts" mandates commit + push to `main` after each turn. **Agent-followed, not runtime-guaranteed.** | `sync_hook` (Stop) commits + pushes (runtime-guaranteed in the CLI path) |

### Built and shipped since the original plan

Everything in the original "near-term unblock" list has landed (see §10.3 for the task ledger and PRs): `daily_log.schema.json`, the dual-write algorithm (`daily.py`), the three Routines, the dashboard MVP, the Reflection pipeline. **4.1.0 added the three-tier knowledge model** (§6.6) on top. The remaining open work is dashboard polish + analytics (sleep/workout forms, trends, the PENDING rule-review queue) — see the §10.3 task table, items 9–15.

**Mid-term (still open):**
- Calendar integration (read-only) for morning brief
- Anomaly detection thresholds (currently no threshold config)
- PENDING rule review queue in dashboard (§10.3 item 14)

**Deferred / removed:**
- Slack server (removed in 4.0.0) — see §10/§11
- Wearable / voice input — see §11
- Remote / hosted MCP server (would reintroduce a 24/7 host) — see §11

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
**[ANSWERED — refined 2026-05-29 from input audit]**

Rule of thumb: **mobile for language, dashboard for forms.** Refined by an audit of ~60 days of `### HH:MM | User` lines (2026-05-29). Seven input categories were observed; each maps to the surface where it has the least friction and the cleanest downstream wiring.

| Category (~freq) | Surface | Why |
|---|---|---|
| Routine completion ("cold shower — done") (~20%) | Dashboard tap | Binary, repeating; one tap mirrors to `log.routine.<id>` + Dashboard line. |
| Structured events — caffeine, meal, sleep numbers, workout (~35%) | Dashboard form (preset > typed value) | Numeric capture; user almost never volunteers mg/duration — presets map to numbers. |
| Sleep / state — numeric (bed, wake, quality 1–5) (part of ~15%) | Dashboard slider | Foundational metric; currently zero structured capture is the biggest data gap. |
| Sleep / state — narrative ("felt heavy, no alarm") (part of ~15%) | Notes field on the sleep form, or chat | Subjective context worth keeping; goes in the same submit. |
| Q&A consult ("build a protocol", "evaluate adding X") (~10%) | CC mobile chat | Needs `user_profile.json` rules + recent context; this is the agent's job. |
| Decisions / overrides ("today no workout") (~5%) | Chat captures intent → dashboard banners the result | Chat regenerates `protocol` (`source: mobile_override`) and may flip `state.json` mode; dashboard reflects. |
| Backfill / catch-up (batched recap of missed days) (~5%, **high friction**) | CC mobile chat | One message parses into many writes — forms would require 8+ submits. |
| Reflective / open loops ("what's the ideal lunch") (~10%) | CC mobile chat | Free-form; the Reflection routine picks them up as `User`-line signal. |

Audit observations the forms must respect:
1. **You almost never volunteer numbers.** Caffeine = "coffee", not "95mg". Meals = ingredient names, not macros. → Presets + agent inference, not free-number entry.
2. **Sleep is foundational but unstructured.** → Highest-leverage new dashboard capture.
3. **Friction is in catch-up, not real-time.** → Forms can't fix it; chat backfill + dashboard nudges can.

If a flow genuinely needs both (workout *with notes*), the dashboard captures the structured part and an optional notes field carries the prose into the same Dashboard mirror line.

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

### 4.7 First-principles framing — doctor / coach / assistant
**[ANSWERED — 2026-05-29]**

OptiMind is not a logger. It is a personal doctor + coach + assistant whose effectiveness scales with the **fidelity and continuity** of the data it has on you. Every surface, prompt, and routine should be designed around the question: *what does a great human coach do, and where does this surface let them do it better?*

Five operating principles fall out of that framing — they govern §4.2, §6, §7, and §8.

1. **Observation precedes advice.** A coach who can't see what's happening can't help. Capture must be cheap and frictionless. When in doubt, lower the ask, not raise it — the audit shows the user rarely volunteers numerics, so the system estimates them from qualitative input (CLAUDE.md "Structured Logging" already encodes this for caffeine; the dashboard extends the pattern to meals, sleep quality, workouts).
2. **Memory accrues; don't re-ask.** A great doctor opens your file before the visit. Every session re-orients from `journal/*.md` + `user_profile.json` + `state.json` (see §6.3); the model never assumes continuity with a previous turn. Captured data is durable; conversation context is not.
3. **Minimum-viable structure.** Force structure only where it pays off downstream — numeric trends, compliance %, time-of-day distributions. Everything else lives in prose, parsed when needed. The 7-category audit (§4.2) is the discriminator: real-time numerics → forms; language → chat.
4. **Surface gaps, not noise.** A coach notices what you *aren't* logging. Reflection and the dashboard nudges (§7.8) flag **capture gaps** (days with no sleep log), **open loops** (User questions in the last 7d with no resolution), and **adherence drops** (routine compliance trending down). These are higher signal than another aggregate chart.
5. **Beliefs evolve on evidence.** The system's model of you (rules in `user_profile.json`) updates from observed behavior under PENDING semantics (§7.5 + §8.3) — proposals surface for review, never silently override an explicit user rule. The *why* behind each rule is itself versioned: the three-tier knowledge model (§6.6) separates the protocol (the what) from the mechanism (the science), so a rule's stated reason can be re-validated and corrected on its own timescale — the surface that caught a stale four-month-old mechanism inversion.

The four cognitive lenses from `comprehensive_memory.md` — **Neuro-Sleep / Nutrition / Psychology-Coach / Strategy** — are the standing frame the system reasons in. Trend cards (§7.8), Weekly Review (§8.2), and Reflection (§8.3) organize observations under those four heads rather than ad-hoc groupings, so the user always knows which lens a finding belongs to.

The user-facing chain of value (the loop §5–§8 implements):

```
seamless capture  →  longitudinal record  →  gap + pattern detection  →  better-grounded advice  →  rule evolution
   (§4.2, §7.7)         (daily + journal)        (Reflection §8.3,            (CLAUDE.md +              (PENDING queue
                                                  Weekly §8.2,                 user_profile.json)        §7.5, §8.3)
                                                  nudges §7.8)
```

Each surface earns its place by making one of those arrows shorter or higher-fidelity. A surface that doesn't ships nothing.

### 4.8 Memory persistence model
**[ANSWERED — 2026-05-30]**

OptiMind's memory is not "in the chat" — it lives in the `optimind-journal` repo. The cloud chat session is a stateless ephemeral process: a doctor who walks into the room with no recollection of prior visits. The repo is the chart. Continuity comes from one principle: **write everything substantive to files, read those files at the start of every turn that needs them.**

#### Two layers, two timescales

| Layer | Where | Who writes | Who reads |
|---|---|---|---|
| **Durable memory** | `user_profile.json`, `state.json`, `comprehensive_memory.md`, `CLAUDE.md` | Reflection routine, explicit user edits, occasional chat agent | Every session, on demand per turn |
| **Conversation history** | `journal/YYYY-MM-DD.md` (verbatim User / Agent / Dashboard lines), `daily/YYYY-MM-DD.json` (structured), System entries from Routines | Every chat turn (via verbatim contract + dual-write), every Routine fire | The agent on substantive turns; the Reflection routine for trend detection |

#### Two distinct mechanisms must compose

For the LLM to actually reason on current state, two operations have to happen in order:

1. **Files-on-disk freshness** — `git pull --rebase --autostash origin main` updates the session's local checkout to current `origin/main`. Necessary when something has landed on main since the session's clone (a Routine fire, another chat session, a manual edit).
2. **Context-window ingest** — once files are fresh on disk, the LLM still doesn't see their content until a `Read` tool call pulls those bytes into the conversation. The model can only reason on what's in its context window, not what's on disk.

**Important distinction**: `git pull` ≠ "refresh the LLM's memory". `git pull` refreshes files on disk; `Read` refreshes the LLM's context window. Both are required. Skipping `git pull` risks reading stale data; skipping `Read` means the model answers from training/internal recall, not from the current chart — the stale-recall failure mode (when files on disk hold updated rules but the model cites a recalled prior version).

```
origin/main  --[git pull]-->  files on disk  --[Read tool call]-->  LLM context window
 (truth)                       (cache layer)                          (what the model sees)
```

#### Three failure modes the architecture must handle

1. **Stale clone** — long-lived chat session's local files frozen at session-start time while `origin/main` moves forward. Mitigation: HEAVY-read turns (Q&A / decisions / backfill) execute `git pull` first (§6.5).
2. **Stale read** — fresh files on disk but the model answered from internal recall. Mitigation: the turn-start procedure mandates `Read` calls for the file set that matches the input shape.
3. **Lost conversation history** — turns that didn't make it into `journal/<date>.md` are invisible to future sessions. Mitigation: dual-write contract + verbatim-first write order (CLAUDE.md "How to Log" + "Critical write contracts").

#### Does it work alike for fresh vs long-running sessions?

Almost — but with one load-bearing asymmetry on `CLAUDE.md` itself.

| Aspect | Fresh new session | Long-running session |
|---|---|---|
| Turn-start procedure | Runs identically | Runs identically |
| `git pull` on HEAVY turns | No-op (clone is current) — cheap | Load-bearing — catches drift since clone |
| `Read` tool calls | Load fresh state into context | Load updated state, overwriting older recall |
| Dual-write contract | Identical | Identical |
| Push enforcement (non-FF rejection) | Identical | Identical |
| **`CLAUDE.md` updates** | Picks up the latest from the clone | **Frozen at clone time** — system prompt is locked at session start; mid-session edits to CLAUDE.md don't take effect until the NEXT new session |

The last row is the only meaningful asymmetry. **The system prompt is sealed in at session start.** Every other file (`user_profile.json`, `journal/`, `daily/`, `state.json`, `comprehensive_memory.md`) can be re-`Read` mid-session to refresh the LLM's view of it. `CLAUDE.md` alone is special: it's loaded once into the system prompt and stays there.

**Consequence for shipping `CLAUDE.md` edits**: when you push a CLAUDE.md change (e.g. a new turn-start procedure), it takes effect on:
- ✅ The very next Routine fire (each fire is a fresh session).
- ✅ Every new chat session started after the push.
- ❌ Any chat session already running — they keep the old CLAUDE.md until you close the chat and open a new one.

**Mental model**: CLAUDE.md is the doctor's standing orders, baked in when the doctor signs in for the shift; the chart on the wall (every other file) can be updated and re-read mid-shift.

#### User-side workflow (chat-session continuity)

The user's working rule for chat sessions, given the asymmetry above:

1. **Continue conversation in a single open session by default.** Don't reflexively start a new chat — the running session has accumulated context, the agent has already done the heavy reads, and turn-to-turn continuity is cheap.
2. **When a major `CLAUDE.md` update lands** (a new contract, a revised playbook, a structural change to the turn-start procedure), **start a fresh session** to pick up the updated system prompt, then continue the conversation from there. The journal/daily files preserve the prior session's substance — the new session reads them on its first HEAVY turn.
3. **Minor file updates** (e.g. a `user_profile.json` rule change, a new `state.json` mode) do **not** require a new session — the next HEAVY turn re-reads those files via the turn-start procedure (§6.5). Only system-prompt-level changes (i.e. `CLAUDE.md`) need a session restart.

This is a deliberate workflow practice, not a workaround: it costs almost nothing (chat re-attach + one HEAVY turn) and guarantees the prompt-level contracts stay in sync with whatever is on disk.

#### Routines vs chat — different staleness profiles

|  | Routine fire | Chat session |
|---|---|---|
| Clone time | At fire (05:55 / 22:00 / Sun 18:00 ET) | At session boot (user-driven) |
| Session length | Minutes (single-shot) | Minutes to hours (multi-turn) |
| Drift risk during session | Negligible (one-shot) | Real (concurrent Routine / cross-tab writes) |
| Read discipline source | Routine's own prompt steps | CLAUDE.md turn-start procedure (intent-keyed, §6.5) |

The user's primary daily interface is CC mobile chat. Routines are scheduled fire-and-forget jobs that don't need the turn-start machinery — their own prompts already specify what they read. The intent-keyed turn-start procedure (§6.5) scopes to chat sessions only.

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
  - **Flexible (when structured doesn't fit):** Open CC mobile → "logged: cold shower 7:35, felt foggy after". The cloud session writes the verbatim `### HH:MM | User` line to `journal/<date>.md` (per CLAUDE.md "How to Log" — agent-followed, no hook in cloud) AND parses the structured part into `daily/<date>.json` with a matching `Dashboard` mirror line (the CLAUDE.md dual-write; mirrors the SDK `do_log_field`).
- **System reads:** existing `daily/<date>.json` for dedup; rules for validation (e.g., a user-defined cutoff rule → warn).
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

> _Once goals + flows are specified, this section converts them to concrete edits in the **active** system prompt and the agent overrides._
>
> **Which prompt to edit — read this first.** The **active runtime system prompt is `optimind-journal/CLAUDE.md`** (private repo). A push there takes effect on the very next Routine fire and every new chat session (the prompt is sealed at session start — see §4.8). This is the highest-leverage knob. `optimind-sdk/CLAUDE.md` (public, in this repo) is **not** the runtime prompt — it is a reference template with `{{USER_NAME}}` / `{{USER_CITY}}` placeholders that a developer adapting the repo would fill in; periodically sync the *generic* parts of the journal CLAUDE.md back into it, but never expect edits there to change runtime behavior. Agent personas: generic base in `optimind/.claude/agents/*.md`, personal overrides in `optimind-journal/.claude/agents/*.md`. (Matches README §"One pitfall worth naming" and governance rule 4.)

### 6.1 Existing principles (keep)
- Holistic reasoning (cross-domain trace)
- Evidence-based (Huberman/Attia/Walker consensus, no fads)
- Disciplined coach tone (not cheerleader)
- Subagent delegation only when domain depth is needed

### 6.2 Existing principles (revise)
- ~~Slack formatting rules~~ → **Mobile-app markdown formatting.** The `*bold*` / `•` Slack idioms are gone with Slack (removed in 4.0.0; `slack_format_hook` deleted). CC mobile renders standard markdown — write plain markdown, no Slack mrkdwn conversion anywhere.

### 6.3 New principles (from §4.6 ephemeral runtime)

> These are encoded **as instructions in `optimind-journal/CLAUDE.md`**, because the cloud runtime has no hooks to enforce them — they are agent-followed contracts, not runtime guarantees. (The SDK reference path enforces some of them via hooks; see the §2 capability table.)

- **Re-orient from files, not from memory.** Every session starts cold. CLAUDE.md's turn-start procedure (§6.5) mandates reading the file set that matches the input shape before reasoning. Don't assume continuity with the previous turn unless the journal proves it.
- **`state.json` is the only durable mode handle.** If the user said "I'm in EXAM_MODE" three sessions ago, that only persists because it was written to `state.json`. Never rely on session-resume — an in-memory session id is not a substitute for state on disk.
- **Log verbatim before reasoning — by contract, not by hook.** CLAUDE.md "How to Log" mandates writing the verbatim `### HH:MM | User` line first. In cloud there is **no `UserPromptSubmit` hook** to guarantee it (hooks are CLI-only) — the guarantee is the agent following the contract. If a hard runtime guarantee is ever required, it needs the CLI/hook path or a server (out of scope; §11).
- **Dashboard / structured writes are authoritative.** When a structured value is logged (e.g. `sleep.quality: 4`), the model treats it as ground truth even if the user later says something different conversationally. Conflicts surface as a question, not a silent override (CLAUDE.md "Surface conflicts, don't silently override").
- **No long-running assumptions.** Don't say "I'll check on this in an hour" — there is no "I" between sessions. Anything periodic happens via the §8 scheduled Routines/jobs.

### 6.4 To-be-derived from goals & flows
- _[e.g., "always end a reactive consult with a verification step the user can do in <10 minutes"]_
- _[e.g., "never propose more than 3 changes in a single response — chunk into follow-ups"]_
- _[e.g., "morning brief is read-only by default; never auto-write a new rule before noon"]_

### 6.5 Turn-start procedure — intent-keyed reads + conditional pull
**[ANSWERED — 2026-05-30]**

Scope: **chat sessions only.** Routines have their own per-prompt read lists; they don't need this layer. Encoded in `optimind-journal/CLAUDE.md` immediately after the input-handling playbook.

For every chat turn:

1. **Classify the shape** of the user input using the 7-shape playbook (§4.2 / CLAUDE.md "Input-handling playbook").
2. **Execute the read level** for that shape:
   - **LIGHT** → Read `daily/<today>.json` only.
   - **LIGHT+** → LIGHT + the topic-relevant rule(s) from `user_profile.json` (e.g. caffeine cutoff rule + current supplement schedule).
   - **MEDIUM** → LIGHT+ + last 1-2 days of `daily/*.json` + `state.json`.
   - **HEAVY** → Run `git pull --rebase --autostash origin main` FIRST (refreshes files on disk against any concurrent Routine fires or cross-session writes), then `Read`: `state.json`, `user_profile.json`, `comprehensive_memory.md`, last 3 days of `journal/*.md`, last 7 days of `daily/*.json`.
3. **Cross-session reference handling** — if the user says "as we discussed", "yesterday's plan", "the X we talked about", regardless of shape: grep last 7 days of `journal/*.md` for the referent BEFORE responding.
4. Write the verbatim `### HH:MM | User` line, compose the response, dual-write any structured facts, commit + push per the Critical write contracts.

**Compound inputs** — a single turn can span multiple shapes ("logged 9am coffee — also, should I take magnesium tonight?"). Decompose the **writes** (one dual-write per loggable element, as in Backfill), and set the turn's read level to the **highest** among the shapes present. Because the levels are nested supersets (LIGHT ⊂ LIGHT+ ⊂ MEDIUM ⊂ HEAVY), one read pass at the max covers every element — no per-shape read pass needed. Bias: when a turn is ambiguous between shapes, classify up; under-reading produces the stale-recall failure mode, while over-reading only costs a little context.

**Shape → read level mapping** (the load-bearing table; defaults you keep unless a turn argues for more):

| Shape | Read level |
|---|---|
| Routine completion ("cold shower done") | LIGHT |
| Structured event — caffeine or meal | LIGHT+ |
| Structured event — workout, sleep numerics | LIGHT |
| Sleep / state narrative | MEDIUM |
| Q&A / consult | HEAVY |
| Decision / override | HEAVY |
| Backfill / catch-up | HEAVY (against the TARGET date's files, not today's) |
| Reflective / open loop | LIGHT |

**Why intent-keyed, not uniform**: a mandatory 5-file Read on every turn wastes context budget and latency on trivial taps ("cold shower done" doesn't need `user_profile.json`). Conversely, light reads on HEAVY shapes produce the stale-recall failure mode. The 7-shape playbook is already the agent's first cognitive step on every turn; attaching read levels to it adds zero classification cost.

**Why `git pull` only on HEAVY**: structured-event writes are safe even on a stale clone — `git push` rejects non-fast-forward, forcing the agent to pull and retry. The remaining failure mode is *stale reads* — the agent answering Q&A or decisions from frozen files. HEAVY shapes pull first because they're answering with authority; stale data here produces wrong advice.

**Cost**: HEAVY turns add ~1s (pull) + ~5-7 `Read` calls (~1-2s combined). LIGHT/LIGHT+ turns add nothing meaningful. Median chat turn pays no cost; high-stakes turns pay for fidelity.

**Mechanism note**: `git pull` ≠ "refresh the LLM's context window". `git pull` refreshes files on disk; only `Read` ingests those bytes into the LLM's working context. Both are necessary; neither is sufficient alone. See §4.8.

### 6.6 Three-tier knowledge model — Sources → Mechanisms → Protocols
**[ANSWERED — 2026-06-07, shipped in 4.1.0]**

The §4.7 principle *"beliefs evolve on evidence"* and §4.8's *"memory accrues; don't re-ask"* needed a knowledge structure that lets the **what** and the **why** of a protocol change on their own timescales. 4.1.0 normalized the knowledge base into three connector-linked tiers. This is the durable-memory schema the system reasons over; it is a contract spanning `user_profile.json` (this repo's `user_profile.schema.json` v1.1), `comprehensive_memory.md` (`mechanism.schema.json`), and `CLAUDE.md` write contract #4. Authoritative spec: `schemas/optimind_interface.md` §"Knowledge-base architecture (v1.1+)" and `comprehensive_memory.md` §5.

| Tier | What it holds | Changes on | Home |
|---|---|---|---|
| **Protocols** (hot) | The *what + when + context* of a rule, plus a cached `why_brief` and a `mechanism_ref` connector | **user context** — moves, seasons, schedules (frequent) | `user_profile.json` rules (`PreferenceRule`) |
| **Mechanisms** (warm) | The *why* — an addressable causal claim with a stable id `mech.<domain>.<slug>`, `sources[]`, `last_reviewed`, `confidence` | **science** (rare, external) | `comprehensive_memory.md`, as HTML-anchored subsections (`<a id="mech.sleep.thermal_onset">`) |
| **Sources** (cold) | Full citations + as-derived reasoning | append-only | nested in each mechanism's `sources[]`; full derivation in `journal/*.md` |

**Why split protocol from mechanism.** Coupling them meant a context change (e.g. a schedule shift) forced touching the science, and vice versa. Separating them also gives an inline error-detection surface: a protocol whose `why_brief` contradicts the mechanism it cites is catchable on read — the surface that catches a protocol whose cached `why_brief` has gone stale against the mechanism it cites — e.g. a months-old reason later corrected by new evidence.

**Schema state.** `schema_version` is `"1.1"`; the schema enum permits `["1.0", "1.1"]` during the migration window (flip to `const: "1.1"` once no v1.0 data remains). `why_brief`, `mechanism_ref` (pattern `^mech\.[a-z_]+\.[a-z0-9_]+$`), and `last_reviewed` are optional additions to `PreferenceRule` — so v1.0 data still validates and existing readers keep parsing.

**Three load-bearing invariants** (the connector is an inert string until something walks it — these are the query engine, encoded in CLAUDE.md write contract #4 and the agent overrides):

1. **Denormalization-for-reads (compressed-why-inline).** Every protocol carries a non-empty `why_brief`. The hot path (Scheduler / Morning Brief, the LIGHT/LIGHT+/MEDIUM read levels of §6.5) reads `why_brief` directly and does **not** dereference `mechanism_ref` per-apply. Only HEAVY turns walk the connector to the mechanism record (and optionally to its `sources[]`).
2. **Coupling / sync.** On any **protocol** update → walk `mechanism_ref` and confirm rule↔mechanism↔sources consistency. On any **mechanism** update → walk back to all referencing protocols and re-validate their `why_brief`. Never update one side silently. The nightly Reflection Routine (§8.2) implements this sync-walk on every fire (analyst override Method §K).
3. **Re-validation trigger.** Items with `confidence < 0.95` or `last_reviewed > 6 months` nominate themselves for review; Reflection flags them as PENDING until the user revises-or-recommits. (Expect aggressive first-run flagging — most legacy rules sit at 0.9.)

**Runtime read pattern (ties to §6.5 read levels):**
- **Hot path** (daily protocol generation, LIGHT→MEDIUM): read the rule's `rule` + `why_brief` directly; do not walk the connector.
- **Cold path** (Q&A consult / decision / backfill, HEAVY): read the rule, walk `mechanism_ref` → read the mechanism record → optionally walk `sources[]` if the rationale is in question. This is exactly the "if a rule under consideration carries `mechanism_ref`, walk the connector" step already in §6.5's HEAVY level.

**Populate-on-create.** Creating a rule that needs a not-yet-existing mechanism is one atomic write: new rule (`user_profile.json`) + new mechanism record (anchor + `sources[]` + `last_reviewed` + `confidence` in `comprehensive_memory.md`) + the deriving journal entry. The runtime never auto-creates mechanism records on demand — this is the nutritionist override's responsibility per CLAUDE.md → Subagents.

---

## 7. Derived dashboard requirements **[INPUT NEEDED + seeded]**

> _A dashboard is a different surface than chat. Decide what it's for: at-a-glance review? Data entry? Tweaking rules? All three?_

### 7.1 Purpose
**[ANSWERED]**

Two responsibilities, equal weight:

**(a) Easy structured logging.** Tap-driven entry for the things that are tedious to type:

| Domain | Fields |
|---|---|
| Sleep | `bedtime`, `wake_time`, `sleep_quality` (1–5 or label) |
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
| Auth | **GitHub OAuth (PKCE)** scoped to optimind-journal, **from day one** (DECIDED) | No client secret in the browser; scoped + revocable. Needs a **Cloudflare Pages Function** for the code→token exchange (GitHub's token endpoint sends no CORS headers, so a pure SPA can't exchange directly). The Function is on-demand serverless — no 24/7 host. Isolate behind `auth.ts`. |
| Package manager | **npm** (DECIDED) | First-class on Cloudflare Pages + SvelteKit, zero setup. Note: commit the lockfile and add `!**/package-lock.json` to `.gitignore` (the `*.json` blanket-ignore would drop it — §10.7). |
| Hosting | **Cloudflare Pages** | Faster than GH Pages, free, easy custom domain; hosts the static app + the OAuth token-exchange Function |
| PWA | **vite-plugin-pwa** | Service worker → offline + home-screen install |
| Offline queue | **Dexie (IndexedDB)** | Queue writes when offline, flush on reconnect (deferred to iteration 2) |

Avoid in v1: Next.js App Router (overkill), Remix, any backend, ORMs, auth libraries beyond Octokit, paid component libraries.

#### Open decisions (block kickoff)

1. **Commit-log hygiene.** Accept the noisy git log (one commit per submission) or add a nightly GHA on optimind-journal that squashes the day's daily-log commits into one? *Lean: accept v1, add squash later if it bothers you.*
2. **OAuth vs PAT.** ~~Lean: PAT for v0~~ **DECIDED (2026-05-28): GitHub OAuth PKCE from day one** (no PAT spike). Rationale: the primary surface is the Claude *mobile* app, so the dashboard will be used on the phone immediately — there is no "throwaway local spike" window, and a long-lived PAT in mobile-browser localStorage is the riskier surface OAuth was meant to avoid. Cost: ~1 dev day + a Cloudflare Pages Function for the token exchange (still serverless, no 24/7 host).
3. **Domain.** Custom subdomain (`optimind.<your-domain>`) vs `.pages.dev`? Affects OAuth callback config. *Lean: `.pages.dev` for v0; custom when domain matters.*
4. **Offline policy.** Service worker + Dexie queue from day one, or require connectivity in v1? *Lean: build offline from day one — subway-logging is a core use case and bolting it on later is expensive.*

### 7.7 Seamless-capture principles
**[ANSWERED — 2026-05-29, derived from §4.2 audit]**

The dashboard's job is to make logging *cheaper than not logging*. Seven design rules, each tied to an audit observation:

1. **Preset > typed value.** Caffeine: pick drink type (latte / espresso / cold brew / drip / tea) → system maps to mg via lookup. Meal: pick slot (breakfast / lunch / dinner / snack) + single free-text "what" field — do not ask for ingredient rows or macros (the audit shows the user writes "pad see ew (tofu, broccoli, egg)" as one phrase, not as a structured list). Workout: pick type (strength / cardio / mobility) + duration. Sleep: bedtime + wake time + quality slider 1–5.
2. **Single-tap routine ticks.** Each `protocol.items[]` row tappable; no confirmation modal. Time defaults to now.
3. **Time always defaults to now.** User only adjusts when backfilling within the day.
4. **Optional everything except the field being logged.** No required-field gates beyond the one the form is named after.
5. **Dual-write is implicit and surface-agnostic.** Every tap mirrors as `### HH:MM | Dashboard\n[<field>] <value>` in `journal/<date>.md` (§7.5). User never thinks about two surfaces. The same contract applies when the cloud agent extracts structured facts from prose ("had a latte at 10:30" → `daily.log.caffeine[]` + Dashboard mirror line) — encoded in `optimind-journal/CLAUDE.md` → Structured Logging.
6. **Backfill via chat, not forms.** A "Log a past day" deep-link on Today opens CC mobile with a date-stamped template (`Backfill 2026-05-21: …`); the cloud agent parses the message into multiple dual-writes against that historic file. Forms would require 8+ separate submits and don't help.
7. **A "What's on your mind?" hybrid field** at the bottom of Today opens chat with the text pre-filled. Handles reflective notes (#7) and decision intent (#5) without forcing a surface switch when the user is already on the dashboard.

These seven rules are the acceptance contract for any new dashboard form. Any form that violates them goes back to the design step.

### 7.8 Trend lenses + friction nudges
**[ANSWERED — 2026-05-29]**

**Trends** are organized around the four cognitive lenses from `comprehensive_memory.md`. Each lens is one card on the Trends view; widgets are sourced from `daily/*.json` so they cost nothing extra to render.

| Lens | Widgets (data already captured) | Source fields |
|---|---|---|
| **Neuro-Sleep** | sleep-quality sparkline (7d/30d); median bedtime + wake; caffeine total mg/day + count after the user's caffeine-cutoff time; evening-supplement-slot compliance | `log.sleep`, `log.caffeine[]`, `log.routine.*` |
| **Nutrition** | meal presence per slot (compliance %); breakfast-composition tick row vs. the user's breakfast rule in `user_profile.json`; supplement-caffeine co-dose compliance per any pairing rule | `log.meals[]`, `log.caffeine[].source` |
| **Psychology / Coach** | routine compliance % per item (e.g. sunlight, cold_shower, meditation, deep_work, wind_down); 14d heatmap | `log.routine`, `protocol.items[]` |
| **Strategy** | workouts/week + avg duration; deep_work block adherence; open-loops carried week-over-week | `log.workouts[]`, weekly review System entries, reflection open-loops list |

Trends widgets render only when ≥7 days of data exist for the underlying field — empty sparklines discourage logging. Until that threshold, the lens card shows a "Logging X for Y more days unlocks this trend" message that *itself* doubles as a nudge.

**Friction nudges** are passive prompts on the Today header that close capture and adherence gaps. Two computation sources:

| Nudge | Computed by | Action when tapped |
|---|---|---|
| "3 days without a sleep log" | Dashboard: scan `daily/*.json` for missing `log.sleep` | Open CC chat with `Backfill <date>: bedtime ?, wake ?, quality ?` template |
| "No workouts logged this week" | Dashboard: same scan over `log.workouts[]` | Open workout form (today) OR chat backfill (past) |
| "Open loop: 'what's the ideal lunch' (2 days ago)" | Reflection (§8.3): User-line questions in last 7d with no Agent resolution | Open chat with original question + context loaded |
| "Routine compliance trending down: sunlight 2/7 this week" | Weekly Review (§8.2): per-item compliance vs. prior week | Open chat for an upstream-cause consult |
| "Protocol override from yesterday not confirmed" | Reflection: user-stated mode/override that wasn't reflected in `state.json` or `daily.protocol.source` | Open chat for confirmation |

The dashboard renders nudges as small chips above the protocol checklist, capped at 3 visible (most recent / highest urgency wins). The full list lives on a "Loops" view (tertiary, §7.2).

**Why nudges, not push notifications:** the §8.4 decision (2026-05-28) was dashboard-pull only — no push channel. Nudges work *because* the user is already on the dashboard for the morning protocol check; they catch attention without a new dependency.

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

> **Live Routine config (2026-05-29 — set up + verified).** The three Routines are **claude.ai scheduled agents connected to `optimind-journal`**: Schedule trigger (05:55 / 22:00 / Sun 18:00 ET), **no MCP connectors** (Drive/Notion unused), cloud environment **network = Trusted** (needed for `git push`), **Permissions → "unrestricted git push" ON** (required to commit to `main`), **Behavior → auto-fix-PRs OFF**. Paste-ready prompts live in `routines/*.md`, each carrying the **OUTPUT BRANCH → `main`** directive (cloud Routines otherwise default to a per-run `claude/*` branch — no UI toggle exists; see §9). Reflection runs in **DRY-RUN** until ~1 week of clean runs.

### 8.3 Memory-update pipeline (concrete)

This is the journal → memory loop, mapped to the schedule above. The data-flow diagram and dual-write contract live in §7.5; this is the temporal sequence:

1. **Capture** (interactive, all day):
   - Mobile (cloud CC) → the agent writes the verbatim `User`-role line to `journal/<d>.md` per CLAUDE.md "How to Log" (agent-followed contract; no hook in cloud). If the turn states a structured fact, it also dual-writes `daily/<d>.json` + the `Dashboard` mirror line.
   - Dashboard → GitHub-API dual-write to `daily/<d>.json` (structured) **and** `journal/<d>.md` as a `Dashboard`-role line (mirror). Both writes are atomic per submission.
2. **Reflect** (22:00 Routine) — Analyst reads **both** `journal/*.md` (last 7d) and `daily/*.json` (last 14d). Emits `MemoryAction` deltas. Auto-applies at PENDING confidence (< 0.5); queues anything ≥ 0.5 for human review. Also runs the three-tier KB sync-walk + re-validation flagging (§6.6).
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
- **2026-05-28** — §7.6 sub-decisions → **commit-log hygiene: accept noise v1; OAuth vs PAT: ~~PAT spike first~~ → OAuth from day one (revised, see entry below); domain: `.pages.dev` v0; offline: DEFERRED to iteration 2** (connectivity-required for the first validation spike; keep the write path queue-shaped so the SW+Dexie queue is a clean retrofit). Offline flipped from §7.6's "day one" lean per the user's min-build stance.
- **2026-05-28** — Dashboard auth + package manager (user). → **Auth: GitHub OAuth (PKCE) from day one — NOT the earlier PAT-spike-then-harden lean.** Rationale: the primary interface is the Claude *mobile* app, so the dashboard goes straight onto the phone — there's no throwaway-local-spike window, and a long-lived PAT in mobile-browser localStorage is exactly the standing-secret risk OAuth avoids; OAuth gives scoped, revocable, no-raw-token access from the first use. Cost accepted: ~1 extra dev day + a **Cloudflare Pages Function** for the code→token exchange (GitHub's token endpoint has no CORS, so a pure SPA can't exchange directly) — still on-demand serverless, preserving the zero-24/7-host rule. Auth isolated behind `auth.ts`. OAuth callback is pinned to the domain, so the `.pages.dev` v0 callback gets reconfigured if/when a custom domain is adopted. → **Package manager: npm** — first-class on Cloudflare Pages + SvelteKit, zero setup, single small project; commit `package-lock.json` and add `!**/package-lock.json` to `.gitignore` (the `*.json` blanket-ignore drops it otherwise — §10.7).
- **2026-05-28** — Dashboard repo placement → **`optimind/dashboard/` subdir** (user). Keeps the dashboard reading the canonical schemas directly (single source, no drift); accepts mixed Node/Python toolchain in one repo. Split into its own repo later only if deploy coupling annoys.
- **2026-05-28** — `schemas/user_profile.schema.json` was silently dropped from the initial commit by the `*.json` gitignore rule. → **Added explicit gitignore negations for schema/config JSON; force-committed the file; documented the gotcha in §10.7 and CLAUDE.md** — Prevents the same silent drop for `daily_log.schema.json`, `.mcp.json`, and the dashboard `package.json` on the build list.
- **2026-05-28** — Is the `Dashboard` journal role tied to the dashboard *surface*? → **No — `Dashboard` marks any structured `log_field` write, regardless of surface (dashboard API, chat agent calling `log_field`, or a future surface).** Redefined the role contract in `journal_entry.schema.md` and generalized §7.5(1). Rationale: `log_field` is a single surface-agnostic tool that does the dual-write; once CC mobile sessions gain the tool (Tasks 3–4) the agent should call it whenever the user states a structured fact, so chat-logged data reaches the `daily/*.json` trends layer and reflection — not only dashboard taps. Tagging the mirror by surface would fragment the contract and orphan chat-logged structured data. (At the time, the agent directive was written into the SDK reference prompt; on the cloud path it now lives as the dual-write contract in `optimind-journal/CLAUDE.md` → "Structured Logging".)
- **2026-05-28** — How is the journal bootstrapped at session start, and how do the MCP tools reach a fresh `claude` CLI session? → **Corrected the Task 3/4 approach after confirming against the Agent SDK + Claude Code docs: (i) `SessionStart` is NOT a Python Agent SDK callback hook (TypeScript-only, like `SessionEnd`); (ii) an in-process `create_sdk_mcp_server` CANNOT be exposed via `.mcp.json`.** Therefore Task 3 = a `.claude/settings.json` `SessionStart` *shell* hook (picked up via the existing `setting_sources=["project"]`) that clones/pulls the journal and writes the resolved path to `$CLAUDE_ENV_FILE`, plus a startup `ensure_journal()` for the SDK-app process (sets `os.environ` before first tool call). Task 4 = a *standalone* stdio MCP server (built on the `mcp` package, importing the existing tool logic) launched by `.mcp.json` — not the in-process SDK server. Env reaches the MCP server process via the `.mcp.json` `env` block. NOTE: `$CLAUDE_ENV_FILE` only affects Bash tool calls, not the MCP server's process env — hence the `.mcp.json` `env` block is the real path-delivery mechanism for the tools.
- **2026-05-28** — Live verification caught the chat agent logging a free-text caffeine value (no mg), producing a schema-invalid `{time, value}` entry (`amount_mg` required, extra `value` key forbidden). → **Keep `daily_log.schema.json` strict; strengthen agent guidance instead of relaxing the schema.** The `log_field` tool descriptions (`src/tools/daily.py` + `src/mcp_server.py`) and `optimind-sdk/CLAUDE.md` now instruct the agent to ALWAYS pass a structured object for event categories and to ESTIMATE the numeric field (e.g. `amount_mg`) from the source when the user doesn't state it. Rationale: preserves the dashboard's structured-data guarantee and keeps the daily file schema-valid; the chat path leans on the agent's estimates (flagged as estimates via `source`). The standalone MCP server's tool description is the channel that actually reaches a CLI session, so it must carry the same guidance as the SDK `@tool`.
- **2026-05-28 — REPLAN (cloud-native).** User's primary interface is now the **Claude mobile/web app (cloud CC) connected to `optimind-journal`**; they want zero local-machine / zero-24/7-host operation, and have stopped using Slack. Confirmed against the docs: **cloud CC cannot read `.mcp.json` stdio tools or run `.claude/settings.json` hooks** (CLI-only), and loads only the repo-root `CLAUDE.md`. → **Re-center the architecture on cloud file-I/O:** the interactive agent and scheduled Routines do the structured dual-write themselves (Read/Write/git) guided by `optimind-journal/CLAUDE.md` + the schemas. The Python tools (Tasks 2/4) and the SessionStart hook (Task 3) are **CLI/dev-only + the canonical reference**, not the production path. A **remote-HTTP MCP server is explicitly deferred** (it would reintroduce a 24/7 host). Capture = cloud CC (chat) + dashboard PWA (GitHub API); scheduled = CC Routines + GHA; data = GitHub. Consequence to track: verbatim `User`-line logging and git-sync are **no longer runtime-guaranteed** in cloud (they were hooks) — now agent-followed per `CLAUDE.md`.
- **2026-05-28** — Reminder channel (§8.4) → **dashboard-pull (active check), no notification infra.** The morning-brief Routine writes the `protocol` + a `System` brief; the dashboard surfaces it; the user checks in. No push, no Slack (removed), no new dependency. Revisit a push channel only if adherence data shows it's needed (§11).
- **2026-05-28** — Slack → **REMOVED** (user hasn't used it in a while). Delete the active surface (`optimind-sdk/src/server.py`, `hooks/slack_format_hook.py`, Slack tokens in `config.py`, `slack-bolt` dep, Slack refs in `agent.py`/`subagents`) and the legacy v1 tree (`optimind/src/`). Tracked as a build task (§10.3).
- **2026-05-27** — Slack server fate? → **~~Deprecate as primary; keep as optional notification channel~~ Superseded: removed entirely (see 2026-05-28 Slack → REMOVED).**
- **2026-05-29** — `user_profile.json` diverged from the canonical schema (no `schema_version`; topics `supplementation`/`psychology`/`system`; free-text provenance `source`s like "Supplement Protocol Review (2026-05-05)"). → **Non-lossy migration: expand the schema to reality, not the data to the enum.** Added `schema_version: "1.0"` to the data (journal `main`); in `user_profile.schema.json` (optimind#17) widened the `topic` enum (+`supplementation`/`psychology`/`system`) and changed `source` from an enum to a free string (provenance is open-ended; the decay job only fades `source=agent_learned`, so legacy curated sources stay exempt). The migrated profile validates; this unblocks Reflection's `schema_version` check in apply-mode.
- **2026-05-29** — Cloud CC Routines push to a per-session `claude/*` branch by default, and there is **no UI toggle** for it (the connector's "Default" is a cloud *environment* — name/network/env/setup-script — not a branch; Connectors are only MCP integrations like Drive/Notion). → **Make Routines commit DIRECTLY to `main`** via an explicit "OUTPUT BRANCH → `main`, no branch, no PR" directive at the top of each prompt, backed by the connector's **"unrestricted git push" permission (ON)**. Rationale: the journal is append-only / single-writer; per-run branches diverge (each run forks `main` and recreates the day's file) and never accumulate. **Verified** — the agent now switches off the feature branch and commits to `main`. Prompts updated in `routines/*.md` (optimind#18); also codified anti-duplicate (skip if today's protocol already exists unchanged).
- **2026-05-29** — When to enable Reflection **apply-mode** (autonomous `user_profile.json` writes)? → **Keep DRY-RUN for ~1 week of nightly runs first**, then delete the dry-run paragraph. Rationale: (a) the §10.5 gate; (b) one run isn't enough trust for autonomous edits to the durable rule store (the first dry-run was excellent — caught a wake-time rule/behavior conflict, respected the N-of-M threshold, refused to touch a 0.9 rule — but it's one data point); (c) there's **no rule-review UI yet** (the dashboard MVP is logging-only), so PENDING rules would accumulate reviewable only via journal `System` entries. apply-mode stays conservative regardless (new rules PENDING <0.5, N-of-M threshold, never overrides explicit/durable rules).
- **2026-05-29 — Input-shape audit (~60 journal days) → idiomatic capture model.** → Seven input categories observed (Routine completion / Structured event / Sleep-state narrative / Q&A consult / Decision-override / Backfill / Reflective). Quantitative values almost never volunteered; only friction is in catch-up logging. → Codified the **category-to-surface map (§4.2)**, the **seamless-capture principles (§7.7)**, and the **trend-lens + friction-nudges model (§7.8)**; folded category handling into `optimind-journal/CLAUDE.md` "Input-handling playbook". Drives dashboard next steps (sleep + workout forms, caffeine preset, meal single-line, backfill deep-link, system feed, nudges).
- **2026-05-29 — First-principles framing made explicit.** → Added **§4.7 doctor/coach mental model** with five operating principles (observation precedes advice; memory accrues; minimum-viable structure; surface gaps not noise; beliefs evolve on evidence) and the chain-of-value loop (capture → record → gap detection → grounded advice → rule evolution). The four cognitive lenses from `comprehensive_memory.md` (Neuro-Sleep / Nutrition / Psychology-Coach / Strategy) are now the standing organizational frame for trends, weekly review, and reflection. Used as the acceptance test for new features: each must shorten one arrow in the loop or it doesn't ship.
- **2026-05-29 — Routine prompts extended to detect gaps + open loops.** → `routines/reflection.md` now also emits (a) **capture gaps** per day, (b) **open loops** (User-line questions w/ no resolution), (c) **override confirmation** (was a stated mode/protocol change reflected in state.json or daily.protocol.source). `routines/weekly_review.md` reorganized to report **Wins/Drift per cognitive lens** + a **Capture** one-liner. `routines/morning_brief.md` System brief now includes a per-item **why** (rule topic + excerpt) and carries open loops from yesterday. These power the §7.8 nudges and the dashboard System feed.
- **2026-05-30 — Memory persistence model + turn-start procedure made explicit.** → Added **§4.8 Memory persistence model** (files = memory, sessions = stateless caches; three failure modes — stale clone / stale read / lost conversation; fresh vs long-running session symmetry except CLAUDE.md is sealed at session start) and **§6.5 Turn-start procedure** (intent-keyed read levels — LIGHT / LIGHT+ / MEDIUM / HEAVY — keyed to the 7-shape playbook; `git pull --rebase --autostash origin main` only on HEAVY turns where stale data produces wrong advice). Codified in `optimind-journal/CLAUDE.md` as a Turn-start procedure block replacing the descriptive "Context" section. **Key mechanism distinction**: `git pull` refreshes files on disk; `Read` ingests bytes into the LLM's working context — both required, neither sufficient alone. Cancels the earlier proposal for a SessionStart hook (redundant with clone-on-boot). Scope: chat sessions only; Routines have their own per-prompt read lists.
- **2026-05-30 — User-side workflow rule for CLAUDE.md updates + CLAUDE.md style cleanup.** → Added the explicit user workflow to §4.8: continue conversation in a single open chat session by default; **start a fresh session only when a major CLAUDE.md update lands** (to pick up the new system prompt). Minor file updates (`user_profile.json`, `state.json`) don't need a session restart — the turn-start procedure picks them up via `Read`. Also scrubbed date-specific incident references from `optimind-journal/CLAUDE.md` (kept example dates in literal Backfill prompts; generic-ized the "stale-apigenin failure mode" sentence to a generic example). Rationale: system prompts should encode rules and generic examples, not incident timestamps — those belong in this decision log instead.
- **2026-06-04 — Compound-input handling made explicit.** → The 7-shape playbook (§4.2) and turn-start table (§6.5) read as one-shape-per-turn, but real turns can mix shapes (a structured-event log + a Q&A consult in one message). The correct behavior was emergent (an LLM classifies softly and the read levels are nested supersets), not stated. Codified the rule in both §6.5 and `optimind-journal/CLAUDE.md` (Input-handling cross-cutting rules): **decompose the writes (one dual-write per loggable element), set the read level to the highest shape present; when ambiguous, classify up.** Closes the under-read gap where a strict agent could latch onto the logging shape and answer the consult half from stale/no reads.
- **2026-06-07 — Knowledge base normalized into three tiers (shipped 4.1.0).** → The protocol "what" and the mechanism "why" were coupled in the same store, so a context change forced touching the science (and vice versa), and there was no read-time surface to catch a rule whose stated reason had gone stale — the failure that let a months-old stale-mechanism inversion persist. → **Split into Sources → Mechanisms → Protocols (§6.6).** `user_profile.schema.json` bumped 1.0 → 1.1 (enum permits both during the migration window): `PreferenceRule` gains optional `why_brief` (denormalized hot-path cache), `mechanism_ref` (connector `^mech\.[a-z_]+\.[a-z0-9_]+$`), and `last_reviewed`. New `mechanism.schema.json` for the addressable causal claims, which live as HTML-anchored subsections in `comprehensive_memory.md` with `sources[]` / `last_reviewed` / `confidence`. Three load-bearing invariants govern the connectors: **denormalization-for-reads** (hot path reads `why_brief`, never dereferences per-apply), **coupling/sync** (any rule or mechanism update walks the connector to re-validate the other side — implemented as a sync-walk on every nightly Reflection), **re-validation trigger** (`confidence < 0.95` or `last_reviewed > 6mo` self-nominates for review). Encoded in `CLAUDE.md` write contract #4 and the analyst/scheduler/nutritionist overrides; full spec in `schemas/optimind_interface.md` + `comprehensive_memory.md` §5; rationale in `CHANGELOG.md` [4.1.0].
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
| 5 | Morning-brief Routine | ✅ **DONE / LIVE** | Reframed for cloud: `routines/morning_brief.md` writes the `protocol` block into `daily/<date>.json` via file-I/O + a `System` brief line (no `set_protocol` tool on the cloud path). Live as a claude.ai scheduled agent (05:55 ET). |
| **S** | **Remove Slack** | ✅ **DONE (4.0.0)** | Deleted the Slack server, `slack_format_hook`, Slack tokens, the `slack-bolt` dep, and the legacy `optimind/src/` v1 tree in the cloud-native pivot. |
| 6 | Dashboard MVP — `optimind/dashboard/` | ✅ **DONE / LIVE** at `optimind-dashboard.pages.dev` (2026-05-29) | Static PWA (SvelteKit + **npm** + Cloudflare Pages). **GitHub-API dual-write in `writeDaily.ts`** (mirrors `do_log_field`). **GitHub OAuth (PKCE)** via `auth.ts` + Cloudflare Pages Function for token exchange. "Today" = protocol checklist + sleep/meal/caffeine/workout forms (sleep/workout stubbed — see Task 9). |
| 7 | Scheduled jobs | ✅ **DONE / LIVE** | 3 Routine prompts (`routines/*.md`) live as claude.ai scheduled agents committing to `main` (verified); decay + schema-lint GHA in `optimind-journal` (dry-run). No push infra (reminders = dashboard-pull). |
| 8 | Reflection pipeline | ✅ **DONE** (folded into `routines/reflection.md`) | Reflection is a cloud Routine reading 7d journal + 14d daily, proposing `user_profile.json` rule deltas with PENDING/threshold semantics. **DRY-RUN** until ~1 week of clean runs, then flip (§9). 2026-05-29 extended with capture-gap + open-loop + override-confirmation detection. |
| **9** | **Sleep + Workout forms on Today** | **NEXT — highest-leverage capture gap** | Add `SleepForm.svelte` (bedtime, wake_time, quality 1–5 slider, optional notes) and `WorkoutForm.svelte` (time, duration_min, type select strength/cardio/mobility) backed by `writeDaily.ts`. Audit shows zero structured sleep + zero workouts despite both being foundational. Schema fields already exist in `daily_log.schema.json`; pure UI work. |
| **10** | **Caffeine preset → mg lookup; Meal single-line capture** | NEXT (paired with 9) | Replace caffeine `amount_mg` text input with drink-type select (latte / espresso / cold brew / drip / tea) → preset mg map (95/65/205/95/47). Meal form: slot select (breakfast/lunch/dinner/snack) + single free-text "what". Both match the §7.7 preset-over-typed rule. |
| **11** | **System feed + protocol provenance chip** | After 9-10 | Today view: collapsed cards for the latest Morning Brief / Reflection (dry-run summary) / Weekly Review System entries from `journal/<recent>.md` — provides the "what does OptiMind think" view without opening files. Add a provenance chip on the protocol header reading `default` / `rule_derived` / `mobile_override` from `protocol.source`. |
| **12** | **Friction nudges + Backfill deep-link + "What's on your mind?" hybrid field** | After 11 | Dashboard gap-scan over last 7d of `daily/*.json` → render up to 3 chips above the checklist (§7.8). Each chip taps to either the relevant form (today gaps) or `https://claude.ai/...` with a date-stamped backfill template (past gaps). Add a text field at the bottom of Today that opens chat with the prose pre-filled — handles reflective notes + decision intent without surface-switch. |
| **13** | **Trends view (4 cognitive-lens cards)** | After ~2 weeks of capture | One card per lens (Neuro-Sleep / Nutrition / Psychology-Coach / Strategy), each with 2-3 widgets per §7.8 table. Render only when ≥7d data exists per widget; otherwise show a "logging X for Y more days unlocks this" nudge. Pure read from `daily/*.json` — no new data path. |
| **14** | **Rules view + PENDING review queue** (after Reflection apply-mode flip) | Gated on Reflection DRY-RUN → apply-mode flip (~2026-06-05 if clean) | Sortable rule list (filter by topic / confidence / `updated_at`). PENDING (<0.5) queue at top with Accept / Reject / Snooze buttons that bump confidence ≥0.5 (Accept) or delete (Reject) via the same GitHub API path. Closes the §7.5 promotion loop end-to-end. |
| **15** | **Monthly Synthesis Routine** (optional, evaluate after 4 Weekly Reviews) | Deferred | New cloud Routine on the 1st of each month: reads last 4 Weekly Reviews + last 30d of daily/json, produces a per-lens trend narrative + identifies stuck open loops. Decide whether to ship based on whether weekly reviews already give enough longitudinal signal. |
| **KB** | **Three-tier knowledge model** (Sources → Mechanisms → Protocols) | ✅ **DONE (4.1.0, 2026-06-07)** | `user_profile.schema.json` v1.1 (`why_brief` / `mechanism_ref` / `last_reviewed`); new `mechanism.schema.json`; `optimind_interface.md` §"Knowledge-base architecture"; data migration in `optimind-journal` (`comprehensive_memory.md` mechanism records + §5; `user_profile.json` → v1.1; CLAUDE.md write contract #4; agent overrides). Three invariants: denormalization-for-reads, coupling-sync, re-validation. See §6.6 + `CHANGELOG.md` [4.1.0]. |

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
- **Slack** — removed entirely in 4.0.0 (the user no longer uses it). Not a surface, not a notification channel. The Slack code (server, hook, dep, tokens) and the legacy v1 tree were deleted (§10.3 Task S).
- **Remote / hosted MCP server** — would let cloud CC use the Python tools directly, but requires a 24/7 host. The cloud path uses file-I/O via `CLAUDE.md` instead. Revisit only if tool-guaranteed writes (vs. agent-followed) become necessary.
- **Push notifications** — reminders are dashboard-pull for now. Add a push channel only if adherence data shows it's needed.
- **Runtime-guaranteed verbatim logging in cloud** — was a `UserPromptSubmit` hook (CLI-only). In cloud it's agent-followed per `CLAUDE.md`; a hard guarantee would need the CLI/hook path or a server.
