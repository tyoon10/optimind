# OptiMind SDK

A personal AI performance coach built on the [Claude Agent SDK](https://platform.claude.com/docs/en/agent-sdk/overview). OptiMind optimizes biological and professional output through nutrition, scheduling, and health.

## Where this fits

OptiMind ships in two current forms (see the [repo-root README](../README.md) and [CHANGELOG `[4.0.0]`](../CHANGELOG.md)):

- **Cloud-native (hosted model).** Ephemeral Claude Code mobile/desktop sessions plus three scheduled cloud Routines, doing file I/O directly against the private `optimind-journal` repo. No local machine, no 24/7 host. This is the production path.
- **SDK (local / self-hosted model) — this directory.** The maintained local-deployment path: a stdio MCP server (`bin/optimind_mcp_server.py`) plus `Stop`/`UserPromptSubmit`/`SessionStart` hooks that you run yourself against your own journal checkout. It's also the canonical reference implementation of the tool surface and the dual-write contract.

Both are current and neither contradicts the other: cloud-native is the hosted runtime; the SDK is the local runtime you operate. There is **no Slack bot and no FastAPI server** — that scaffolding was removed in the 4.0.0 cloud-native pivot.

The code here began as a migration from a Gemini 3 Flash + LangChain stack to the Claude Agent SDK (v3.0, [CHANGELOG `[3.0.0]`](../CHANGELOG.md)); the narrative below documents that move and is still useful as a reference for teams evaluating the same one.

## Why This Migration Exists

OptiMind v1-v2 worked. It ran on Google Gemini 3 Flash with LangChain, FastAPI, and Slack-Bolt. But it had architectural problems that couldn't be solved within the existing stack:

**1. Every message loaded everything.** The system dumped 5 days of journal history, all preference rules, and the full state object into the prompt on every turn — regardless of query relevance. A "Hi" cost the same tokens as "What should I eat after my workout?"

**2. The agent was read-only.** State and preferences were injected as static text. The agent couldn't switch modes ("I have an exam Friday") or learn preferences ("I'm not doing keto anymore") without manual JSON edits.

**3. Preference learning was dead.** A `ReflectorAgent` using LangChain structured output was built in v1, then abandoned in v2 when the multi-agent Star Topology was collapsed. Users couldn't teach the system through conversation.

**4. No conversation continuity.** Every Slack message was a stateless LLM call. "Plan my week" followed by "Move gym to Thursday" had no shared context.

**5. Multi-agent routing was impractical.** LangGraph required a classifier LLM call to route to specialist agents, each duplicating the system prompt. The overhead wasn't worth it, so domain expertise was flattened into a single prompt.

**6. ~80 lines of LLM plumbing.** A factory pattern for Gemini/Vertex AI fallback, retry logic with exponential backoff for 503 errors, and response parsing for Gemini's multimodal list-of-parts format.

The full problem analysis and design rationale are in [ARCHITECTURE.md](ARCHITECTURE.md).

## What the Agent SDK Changed

| Before (v2) | After (SDK) |
|---|---|
| 136-line system prompt template with string formatting | `CLAUDE.md` — plain markdown, loaded and cached automatically |
| All context injected every turn (~3K tokens fixed) | Tools fetch on demand — agent decides what's relevant |
| Agent can only read state and rules | Agent reads AND writes via tools |
| Preference learning abandoned (ReflectorAgent, 65 lines) | Stop hook (~20 lines), revived |
| Stateless — each message is independent | Session persistence across turns |
| Multi-agent abandoned (LangGraph overhead) | Subagents with zero routing overhead |
| LLM factory + retry + response parsing (~80 lines) | Eliminated — SDK handles it |
| 14 Python dependencies | 7 dependencies |

### New Capabilities

- **Analyst subagent**: Multi-day journal trend analysis ("How did my sleep affect productivity this week?"). Identified as a gap in v2 but never built because LangGraph made it impractical.
- **Session continuity**: "Plan my week" → "Move gym to Thursday" → "Optimize meals around that" in a single conversation thread (the SDK resumes by `session_id`).
- **Live preference learning**: "I'm switching to Mediterranean" triggers the reflector hook, which calls `delete_rule` (keto) and `add_rule` (Mediterranean) automatically.

## Architecture

The local entrypoint is a stdio MCP server registered in the repo-root `../.mcp.json`. The
`claude` CLI launches `bin/optimind_mcp_server.py`, which exposes the tools over the MCP stdio
transport; a `SessionStart` hook (`bin/session_start.py`, wired in `../.claude/settings.json`)
bootstraps the journal checkout. The same pure tool handlers are also wired into an in-process
Agent SDK runtime in `src/agent.py` for the standalone `test_agent.py` smoke path — one shared
core, two transports.

```
claude CLI  (stdio)                    test_agent.py  (in-process)
    │                                       │
    ▼                                       ▼
┌──────────────────────────────┐   ┌──────────────────────────────┐
│  bin/optimind_mcp_server.py  │   │  src/agent.py                │
│  → src/mcp_server.py:run()   │   │  create_sdk_mcp_server(...)  │
│  MCP stdio transport         │   │  + query() loop              │
└──────────────┬───────────────┘   └──────────────┬───────────────┘
               │   shared pure handlers (src/tools/*.py)
               └───────────────┬───────────────────┘
                               ▼
┌─────────────────────────────────────────────────┐
│  CLAUDE.md (static) — persona, directives        │
│  11 Custom Tools — Journal, State, Prefs, Daily  │
│  3 Subagents — Nutritionist, Scheduler, Analyst  │
│  Hooks — UserPrompt log, Journal, Reflector, Sync│  (in-process runtime only)
└─────────────────────────┬───────────────────────┘
                          ▼
┌─────────────────────────────────────────────────┐
│  Data Layer (private optimind-journal checkout)  │
│  resolved from $OPTIMIND_JOURNAL_PATH            │
│  ├── journal/*.md         Flat-file md, git-synced│
│  ├── state.json           Mode, constraints, focus│
│  ├── daily/*.json         Structured daily logs   │
│  └── user_profile.json    Preference rules        │
└─────────────────────────────────────────────────┘
```

## Custom Tools

All tools are registered under a single MCP server (`optimind`) — see `src/mcp_server.py` for the
canonical registry:

| Tool | Type | Purpose |
|---|---|---|
| `get_recent_journal` | Read | Last N days of journal entries |
| `search_journal` | Read | Keyword search across journal files |
| `log_entry` | Write | Append to today's journal |
| `get_state` | Read | Current mode, constraints, focus |
| `set_state` | Write | Switch modes, update constraints |
| `get_rules` | Read | Preference rules filtered by topic |
| `add_rule` | Write | Learn a new preference |
| `delete_rule` | Write | Remove an outdated rule |
| `get_daily` | Read | Structured daily log (protocol + log) for a date |
| `log_field` | Write | Log one structured field, dual-written to `daily/<date>.json` and the journal |
| `set_protocol` | Write | Write today's protocol (plan) into the daily log |

## Subagents

| Agent | Domain | Can Write State? |
|---|---|---|
| `nutritionist` | Meals, supplements, caffeine, diet transitions | No |
| `scheduler` | Deep work, circadian alignment, mode switching | Yes |
| `analyst` | Multi-day trend analysis and pattern correlation | No |

Claude decides when to delegate based on the subagent descriptions. No routing graph, no classifier LLM call.

## Hooks

The in-process runtime (`src/agent.py`) registers these SDK callback hooks:

| Hook | Event | Replaces |
|---|---|---|
| `user_prompt_hook` | UserPromptSubmit | Verbatim user-message logging (runtime guarantee) |
| `journal_hook` | Stop | Manual `log_interaction()` calls |
| `reflector_hook` | Stop | `ReflectorAgent` class (abandoned in v2) |
| `sync_hook` | Stop | `asyncio.to_thread(journal_manager.sync)` |

Note: `SessionEnd` is not available as a Python SDK callback hook (TypeScript only), so git sync
uses the `Stop` hook instead — see `src/hooks/sync_hook.py`.

Separately, the stdio-MCP path wires one `SessionStart` command hook in `../.claude/settings.json`
(`bin/session_start.py`) that clones/pulls the journal checkout and exports the resolved
`OPTIMIND_JOURNAL_PATH` before the first turn.

## Setup

```bash
# Clone
git clone https://github.com/tyoon10/optimind.git
cd optimind/optimind-sdk

# Install
pip install -r requirements.txt

# Configure: point at your private journal checkout
cp .env.example .env
# Edit .env — set OPTIMIND_JOURNAL_PATH (and ANTHROPIC_API_KEY for the in-process path)
```

The local entrypoint is the stdio MCP server, registered in the repo-root `../.mcp.json` (one
directory up from here). Launch it the way the `claude` CLI does — from the repo root, with
`OPTIMIND_JOURNAL_PATH` exported so the tools can find your journal:

```bash
cd ..                                    # repo root, where .mcp.json lives
export OPTIMIND_JOURNAL_PATH=/abs/path/to/optimind-journal
python3 optimind-sdk/bin/optimind_mcp_server.py
```

Run the `claude` CLI from the repo root and it picks up `.mcp.json` automatically; the
`SessionStart` hook in `../.claude/settings.json` clones/pulls the journal checkout on the first
turn. The MCP server itself needs no API key — it only wraps the tool handlers.

### Environment Variables

| Variable | Required | Purpose |
|---|---|---|
| `OPTIMIND_JOURNAL_PATH` | Yes (prod) | Absolute path to your `optimind-journal` checkout; tools resolve all data I/O from it. Falls back to `<optimind-sdk>/data/` in dev with a warning. |
| `ANTHROPIC_API_KEY` | For the agent | Claude API access — needed by the in-process `src/agent.py` path; the stdio MCP server alone does not require it |
| `GITHUB_PAT` | No | Git sync for the journal (omit for local-only) |
| `JOURNAL_REPO_URL` | No | Journal git repo URL |

### Smoke Test

```bash
# Outside of Claude Code (nested sessions are blocked)
export ANTHROPIC_API_KEY=sk-ant-...
python test_agent.py
```

## Project History

| Version | Date | Stack | What Changed |
|---|---|---|---|
| 1.0 | Jan 2026 | Gemini + LangGraph | Multi-agent Star Topology (orchestrator → specialists) |
| 2.0 | Jan 2026 | Gemini + LangChain | Collapsed to single agent — routing overhead not worth it |
| 2.1 | Feb 2026 | Gemini + LangChain | Reliability fixes (Slack retry storm, git race condition) |
| 2.2 | Feb 2026 | Gemini + LangChain | Gemini 3 Competition submission |
| 3.0 | Mar 2026 | Claude Agent SDK | Full migration — Slack + FastAPI server on the Agent SDK |
| 4.0 | May 2026 | Cloud-native | Slack + server removed; cloud Routines + this SDK as the local/reference path |
| 4.1 | Jun 2026 | Cloud-native | `user_profile` schema 1.0 → 1.1 (three-tier knowledge model) |

See [CHANGELOG.md](../CHANGELOG.md) for detailed release notes.

## What Stayed the Same

The data layer is identical across the migrations. Same flat-file markdown journal, same
`state.json` schema, same `user_profile.json` format (now at `schema_version` 1.1), same git sync
strategy.

The 3.0 migration replaced the orchestration and LLM layers only. The 4.0.0 cloud-native pivot then
removed the Slack + FastAPI server entirely (see the [`[4.0.0]`](../CHANGELOG.md) changelog entry):
the hosted runtime is now ephemeral Claude Code sessions, and this SDK is the maintained
local/self-hosted path described above.

## Lessons Learned

1. **CLAUDE.md is genuinely better than prompt templates.** No string formatting, no injection bugs, automatic prompt caching, survives compaction. The 136-line template became 60 lines of plain markdown.

2. **Tools > prompt injection for dynamic data.** Letting the agent decide what context to fetch (vs. dumping everything) reduced average token usage and made the agent smarter about what it reads.

3. **Hooks revive abandoned features for free.** The ReflectorAgent was 65 lines of LangChain structured output code with a dedicated routing path. The equivalent hook is 20 lines with no routing overhead.

4. **Subagents solve the problem that killed multi-agent.** LangGraph's routing overhead made specialists impractical. Agent SDK subagents have zero routing cost — Claude decides when to delegate as part of its normal reasoning.

5. **`SessionEnd` is TypeScript-only in the Python SDK.** Plan for this if you need session lifecycle hooks in Python.

## License

MIT — see [LICENSE](../LICENSE).
