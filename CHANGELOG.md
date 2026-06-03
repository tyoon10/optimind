# Changelog

All notable changes to the OptiMind project will be documented in this file.

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
