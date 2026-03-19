# Changelog

All notable changes to the OptiMind project will be documented in this file.

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

## [2.2.0] - 2026-02-09
### Gemini 3 Competition Submission
- **Documentation:**
    - added `LICENSE` (MIT).
    - updated `README.md` with submission-specific instructions.
- **Privacy:**
    - Verified strict separation of user data (`data/journal`) from codebase.
    - Confirmed `Memory-Only Mode` for judges (no `GITHUB_PAT` required).

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
