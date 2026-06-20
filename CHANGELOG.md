# Changelog

All notable changes to the OptiMind project will be documented in this file.

## [4.1.1] - 2026-06-19
### Documentation & knowledge-base consistency pass

A full audit of both repos (`optimind` + `optimind-journal`) for doc cleanliness, cross-file consistency, and schema↔data alignment. Corrections and de-staling only — no architecture change.

**Public repo (`optimind/`):**
- **`routines/reflection.md` — load-bearing fix.** Step 9's apply-mode `schema_version` check accepted only `"1.0"` and would `STOP` on the live `"1.1"` profile, silently blocking every nightly rule-write once apply-mode is on; it now accepts the migration-window enum `["1.0","1.1"]`. Added the explicit KB sync-walk steps (analyst Method §K: re-validation scan + rule↔mechanism connector-walk + coverage line) that write-contract #4 and `comprehensive_memory.md` §5 say the nightly Reflection performs — the prompt previously described it nowhere.
- **`routines/morning_brief.md`** — each item's "why" now reads the rule's cached `why_brief` (the v1.1 hot-path read) rather than re-deriving from topic+excerpt.
- **`optimind-sdk/`** — de-staled to the actual stdio-MCP local SDK: removed deleted-`src/server.py` / Slack / FastAPI references (pre-4.0.0); documented the real entrypoint; reconciled the `sync_hook` event (`Stop`) between README and ARCHITECTURE; bumped the SDK's expected `schema_version` to `1.1`; dropped Slack env vars from `.env.example`.
- **`docs/`** — rewrote `USER_FLOW_PLAN.md` to the cloud-native + three-tier architecture (added the missing §6.6 three-tier model; fixed the §6 system-prompt pointer that aimed edits at the wrong `CLAUDE.md`); deleted the obsolete `SUBAGENT_TRAINING.md`; added "Superseded (pre-4.0.0)" banners to the three remaining v1/v2 design docs.
- **`schemas/`** — `daily_log.schema.json` gained an optional `metrics` map (graded daily readings — e.g. a 0–5 soreness / energy / mood score — distinct from binary `routine` completions; additive, `const "1.0"` unchanged). Corrected cardinality wording (`1:m`, not `m:n`) in `mechanism.schema.json` + `user_profile.schema.json` + `optimind_interface.md`; the `const`→accepted-set migration wording (the profile schema uses an `enum` during the window); the migration-script story (1.0→1.1 was additive/no-script; `user_profile_1to2.py` is the next-breaking-bump template); and the re-validation trigger (`OR`, not `and`).
- Misc: README "four canonical contracts" → **five** (added `mechanism.schema.json`); the three generic agents' "Respond in Slack format" → markdown; deleted the dead-stack root `.env.example` (Gemini Vertex + Slack + Cloud Run); fixed a dead `CLAUDE.md → Subagents` pointer.

**Private layer (`optimind-journal/`):** the owner's personal records (rules, mechanism records, journal hygiene) were updated in the same cross-repo consistency pass. Those are personal protocol + data changes — they live in that private repo's own history, not here. Personal protocol values and identity stay out of the public framework per the two-repo governance contract.

## [4.1.0] - 2026-06-07
### Knowledge-base normalization — three-tier model with mechanism connector

User-profile schema bumped 1.0 → 1.1 to support a three-tier knowledge model: **sources** (cold; citations + derivation logs in the private journal repo) → **mechanisms** (warm; addressable causal claims with stable IDs in `comprehensive_memory.md`) → **protocols** (hot; `user_profile.json` rules, each carrying a cached `why_brief` plus a `mechanism_ref` connector to its mechanism record).

**Why the split.** Protocols and mechanisms change on different timescales: mechanisms with science (rare, external), protocols with user context (frequent — moves, seasons, schedules). Coupling them meant a context change forced touching the science, and vice versa. Separating them also gives the system an inline error-detection surface: a protocol whose claimed `why_brief` contradicts the mechanism it cites is catchable on read — the surface that caught a four-month-old "cold shower pre-sleep to lower core temp" inversion that motivated this change.

**Three load-bearing invariants** govern the connectors (without them, mechanism_ref is an inert string):
1. **Compressed-why-inline (denormalization-for-reads).** Every protocol carries a non-empty `why_brief`. The hot path reads `why_brief` directly and never dereferences `mechanism_ref` on each apply.
2. **Coupling / sync.** On any protocol update → walk `mechanism_ref` and confirm consistency. On any mechanism update → walk back to all referencing protocols and re-validate `why_brief`. Implemented as a sync-walk on every nightly Reflection.
3. **Re-validation trigger.** Items older than 6 months or below confidence 0.95 nominate themselves for review.

- **`schemas/user_profile.schema.json` v1.1** (this repo):
  - `schema_version` widened from `const: "1.0"` to `enum: ["1.0", "1.1"]` to support the migration window. Flip to `const: "1.1"` in a future release once no v1.0 data remains anywhere.
  - `PreferenceRule` gains three optional fields: `why_brief` (one-line cached mechanism, hot-path read), `mechanism_ref` (connector pattern `^mech\.[a-z_]+\.[a-z0-9_]+$`), `last_reviewed` (bare YYYY-MM-DD).
  - `additionalProperties: false` posture confirmed at the rule-item level via the `$ref` → `PreferenceRule` indirection (the earlier audit's claim that it was unset was a Python-check artifact that missed the indirection).
- **`schemas/mechanism.schema.json`** (NEW): formal shape for mechanism records — id, domain (`sleep | nutrition | psychology | strategy`), claim prose, `sources[]` (minItems: 1), `last_reviewed`, `confidence`. Records live as anchor-ID'd subsections in the journal repo's `comprehensive_memory.md`; the schema documents the shape but doesn't constrain location (memory or future `evidence/` are both valid renderers).
- **`schemas/optimind_interface.md`**: new §"Knowledge-base architecture (v1.1+)" documenting the three tiers, the connector resolution mechanics (HTML-anchor convention to preserve dotted IDs), the three load-bearing invariants (denormalization-for-reads / coupling-sync / re-validation trigger), and the hot-path vs cold-path read patterns.
- **`schemas/journal_entry.schema.md`**: grep-signal keyword table extended with `mech.<domain>.<slug>` and `mechanism:` so the analyst's multi-day pattern grep finds derivation entries that link back to mechanism IDs.

**Data migration in `optimind-journal/` (private repo, separate commit history):**
- `comprehensive_memory.md`: 21 mechanism records carved out across §§1–4 with anchors, sources, last_reviewed, confidence; new §5 Knowledge Architecture (~6 lines) stating the three invariants.
- `user_profile.json`: bumped to `schema_version: "1.1"`. 19/23 rules now carry `why_brief`; 17/23 carry `mechanism_ref`; 23/23 carry `last_reviewed`. The stale `topic:system` pointer rule (`Reference data/journal/comprehensive_memory.md`, v1-era path) was superseded with the new self-referential pointer. Migration was JSON-Schema-validated against v1.1.
- `CLAUDE.md`: Critical write contracts expanded 3 → 4 (added KB-sync contract); turn-start procedure HEAVY-read step added connector-walk; populate-on-create rule for new mechanisms.
- `optimind-journal/.claude/agents/` (the personal overrides only — the generic `optimind/.claude/agents/` base prompts were not touched; a fork supplies the KB wiring in its own override layer): analyst override gained Method §K (re-validation + sync-walk + coverage report on every Nightly Reflection); scheduler gained hot-path read pattern (use `why_brief`, don't dereference per-apply); nutritionist gained populate-on-create rule (new rule + new mechanism + new journal entry are one atomic write).

**Decided thresholds** (stricter than originally proposed): `confidence < 0.95` OR `last_reviewed > 6 months` triggers the re-validation flag (either threshold is sufficient), per user choice at Phase 0c of the proposal. Expect aggressive flagging on the first Reflection — most existing rules at 0.9 confidence will auto-flag.

**Breaking changes from 4.0.0:**
- None at the contract level: v1.1 schema permits v1.0 data via the enum form. Existing tooling that reads `user_profile.json` continues to parse it correctly.
- Behavior change: agents in `optimind-journal/.claude/agents/` now follow the v1.1 read patterns (hot-path via `why_brief`, cold-path via connector walk). Any fork of `optimind-journal` should review their overrides.

## [4.0.0] - 2026-05-31
### Cloud-native pivot + public design archive

This release moves OptiMind off Slack and off any long-running server. The runtime is now the Claude Code mobile/desktop app talking to a private companion repo (`optimind-journal`), plus three scheduled cloud Routines on claude.ai. This repo is retitled as the **public design archive** — canonical schemas, paste-ready routine prompts, dashboard PWA, the v3 SDK as a reference implementation, and the design doc with the engineering decision log.

- **Architecture: cloud-native.** Removed all Slack and server scaffolding (`optimind-sdk/src/server.py`, `hooks/slack_format_hook.py`, Slack tokens, `slack-bolt` dependency) and the legacy `optimind/src/` v1 tree. The chat surface is now the Claude Code mobile app connected to a private `optimind-journal` repo via file I/O. No local machine, no 24/7 host. The §9 decision log in `docs/USER_FLOW_PLAN.md` traces every choice.
- **Three scheduled cloud Routines** (`routines/`): Morning Brief (daily 05:55 ET), Nightly Reflection (daily 22:00 ET), Weekly Review (Sundays 18:00 ET). Each `.md` file's fenced `text` block is the paste-ready source-of-truth for what gets pasted into the claude.ai Routines configuration UI. All three carry an explicit `OUTPUT BRANCH → main` directive (cloud Routines default to a per-session `claude/*` branch otherwise). Reflection starts in DRY-RUN until ~1 week of clean runs.
- **Dashboard MVP** (`dashboard/`): SvelteKit static PWA deployed to Cloudflare Pages. GitHub OAuth (PKCE) via a Cloudflare Pages Function for the code→token exchange (GitHub's token endpoint sends no CORS headers, so a pure SPA can't exchange directly). Writes to the journal repo via the GitHub REST API following a dual-write contract: every structured field write goes to both `daily/<date>.json` (numeric) and `journal/<date>.md` as a Dashboard-role mirror line.
- **Canonical schemas** (`schemas/`): `daily_log.schema.json`, `user_profile.schema.json`, `journal_entry.schema.md`, `optimind_interface.md`. The four contracts that bind this repo to `optimind-journal` at runtime. `schema_version: "1.0"` enforced; migrations live in `migrations/`.
- **`optimind-sdk/` reframed:** the Python implementation (tools, hooks, MCP server) becomes the **canonical reference algorithm + local-CLI tooling**, not the production path. Cloud sessions do file I/O directly guided by `CLAUDE.md` instead of calling these tools. The dual-write algorithm in `optimind-sdk/src/tools/daily.py` remains the public reference for anyone implementing the contract in another language.
- **Design doc with engineering decision log** (`docs/USER_FLOW_PLAN.md`): first-principles framing for the doctor/coach mental model (§4.7), the memory persistence model with files = memory and sessions = stateless caches (§4.8), the 7-shape input playbook (§4.2), the intent-keyed turn-start procedure (§6.5), and the cumulative decision log (§9).
- **Public design archive framing:** README rewritten to describe the two-repo system (public `optimind` / private `optimind-journal`), six governance rules for ongoing updates, MIT-licensed for forks. Legacy v1/v2 documentation and Windows PowerShell scripts archived off-repo (preserved for personal reference outside the public tree). Routine prompts and design doc lightly scrubbed of specific personal-protocol references (the user's data lives in the private companion repo; the public side is the system architecture).

**Breaking changes from 3.0.0:**
- Slack integration is gone (server, hooks, dependency, tokens).
- The `optimind/src/` v1 tree (FastAPI + LangChain + Slack-Bolt) is removed; the legacy `bin/` PowerShell startup scripts are gone.
- The production runtime no longer invokes `optimind-sdk/` tools or hooks; that code is now reference + CLI-dev tooling, not a server.

## [3.0.0] - 2026-03-19
### Claude Agent SDK Migration
- **Migration:** Rebuilt from Gemini 3 Flash + LangChain to Claude Agent SDK (`optimind-sdk/`).
- **CLAUDE.md:** Replaced 136-line system prompt template with plain markdown persona file.
  Loaded automatically, prompt-cached, survives context compaction.
- **Custom Tools (8):** Journal (read/search/log), State (get/set), Preferences (get/add/delete).
  Agent fetches context on demand instead of injecting everything on every turn.
- **Subagents (3):** Nutritionist, Scheduler, Analyst. Claude decides when to delegate.
  No routing graph, no classifier LLM call. Replaces abandoned LangGraph Star Topology.
- **Hooks (4):**
  - `journal_hook` (Stop): Auto-logs interactions. Replaces manual `log_interaction()` calls.
  - `reflector_hook` (Stop): Preference extraction revived. Replaces abandoned `ReflectorAgent` (65 lines to 20).
  - `sync_hook` (Stop): Git commit and push. Note: `SessionEnd` is TypeScript-only in Python SDK.
  - `slack_format_hook` (PostToolUse): Markdown to Slack mrkdwn conversion.
- **Session Persistence:** Multi-turn Slack conversations via Agent SDK sessions (keyed by user_id).
- **New Capability:** Analyst subagent for multi-day journal trend analysis.
  Fills the "missing feedback loop" gap identified in v2 architecture review.
- **Dependencies:** 14 packages reduced to 7.
- **Eliminated:** LLM factory, retry logic, Gemini response parsing, prompt template string formatting.
- **Preserved:** Flat-file journal, state.json, user_profile.json, Slack-Bolt integration, git sync.
- See `optimind-sdk/ARCHITECTURE.md` for full problem analysis and design rationale.

## [2.1.0] - 2026-02-06
### Reliability & Latency Patch
- **Fixed: Double Response Bug (Slack Retry Storm)**
    - **Issue:** Cold starts caused request latency >3s, triggering Slack retries and duplicate agent execution.
    - **Fix:** Implemented `X-Slack-Retry-Num` guard in `src/main.py` to ignore retries.
- **Fixed: Git Sync Race Condition**
    - **Issue:** Parallel execution caused concurrent `git push` attempts, leading to missing logs.
    - **Fix:** Solved by the Retry Guard (above), ensuring strictly serial execution.
- **Improved: Latency (Reply-First Architecture)**
    - **Change:** Updated `OptiMindAgent` to send the HTTP response to Slack *before* expecting the Git Push.
    - **Method:** The final `journal_manager.sync(push=True)` is now offloaded to a background thread using `asyncio.to_thread`.
    - **Benefit:** User receives near-instant response regardless of GitHub latency.
- **Improved: Observability & Safety**
    - Added `ENV PYTHONUNBUFFERED=1` to Dockerfile for real-time Cloud Run logs.
    - Added `GIT_TERMINAL_PROMPT=0` to `JournalManager` to prevent infinite hangs on auth failure.

## [2.0.1] - 2026-01-28
### Sync Performance Optimization
- **Git Workflow Redesign:**
    - **Removed:** Implicit `_sync_git()` calls (5+ per turn) from `JournalManager`.
    - **Added:** Session-based Sync in `OptiMindAgent`.
        1. **Start:** Pull Only (Syncs laptop changes).
        2. **End:** Commit & Push (Saves interaction).
    - **Result:** Drastically reduced latency by batching Git operations.
- **Tools:**
    - Upgraded `bin/pull_journal.ps1` to "Smart Sync" (Auto-Commit local changes before Pulling) to prevent "Dirty Working Directory" conflicts.

## [2.0.0] - 2026-01-26
### Architecture Migration (The "Single Brain" Refactor)
- **Refactor:**
    - Replaced multi-agent Star Topology (LangGraph) with a simplified `OptiMindAgent` class (`src/core/agent.py`).
    - **Benefit:** Reduced cognitive overhead and file complexity.
- **Directory Structure:**
    - `src/core/`: State, Memory, LLM Client.
    - `src/services/`: Slack, API handlers.
    - `src/legacy/`: Archived old graph code.
- **Infrastructure:**
    - Added `bin/` for management scripts.
    - Added `logs/` for local output.
    - Strict Config: Type-safe environment loading in `src/config.py`.
