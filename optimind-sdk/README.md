# OptiMind SDK

A personal AI performance coach rebuilt on the [Claude Agent SDK](https://platform.claude.com/docs/en/agent-sdk/overview). OptiMind optimizes biological and professional output through nutrition, scheduling, and health — delivered via Slack.

This is a migration from a Gemini 3 Flash + LangChain stack to Claude Agent SDK, documented as a reference implementation for teams evaluating the same move.

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
| Stateless — each message is independent | Session persistence across Slack messages |
| Multi-agent abandoned (LangGraph overhead) | Subagents with zero routing overhead |
| LLM factory + retry + response parsing (~80 lines) | Eliminated — SDK handles it |
| 14 Python dependencies | 7 dependencies |

### New Capabilities

- **Analyst subagent**: Multi-day journal trend analysis ("How did my sleep affect productivity this week?"). Identified as a gap in v2 but never built because LangGraph made it impractical.
- **Session continuity**: "Plan my week" → "Move gym to Thursday" → "Optimize meals around that" in a single conversation thread.
- **Live preference learning**: "I'm switching to Mediterranean" triggers the reflector hook, which calls `delete_rule` (keto) and `add_rule` (Mediterranean) automatically.

## Architecture

```
Slack Message
    │
    ▼
┌─────────────────────────────┐
│  FastAPI + Slack-Bolt        │  Preserved: webhook, dedup, retry-ignore
│  (server.py)                 │
└─────────┬───────────────────┘
          │
          ▼
┌─────────────────────────────┐
│  Claude Agent SDK Runtime    │
│  ┌───────────────────────┐  │
│  │ CLAUDE.md (static)    │  │  Persona, directives, Slack formatting
│  │ 8 Custom Tools        │  │  Journal, State, Preferences (read/write)
│  │ 3 Subagents           │  │  Nutritionist, Scheduler, Analyst
│  │ 4 Hooks               │  │  Journal log, Reflector, Sync, Format
│  └───────────────────────┘  │
└─────────┬───────────────────┘
          │
          ▼
┌─────────────────────────────┐
│  Data Layer (preserved)      │
│  ├── data/journal/*.md       │  Flat-file markdown, git-synced
│  ├── data/state.json         │  Mode, constraints, focus
│  └── data/user_profile.json  │  Preference rules
└─────────────────────────────┘
```

## Custom Tools

All tools are registered under a single MCP server (`optimind`):

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

## Subagents

| Agent | Domain | Can Write State? |
|---|---|---|
| `nutritionist` | Meals, supplements, caffeine, diet transitions | No |
| `scheduler` | Deep work, circadian alignment, mode switching | Yes |
| `analyst` | Multi-day trend analysis and pattern correlation | No |

Claude decides when to delegate based on the subagent descriptions. No routing graph, no classifier LLM call.

## Hooks

| Hook | Event | Replaces |
|---|---|---|
| `journal_hook` | Stop | Manual `log_interaction()` calls |
| `reflector_hook` | Stop | `ReflectorAgent` class (abandoned in v2) |
| `sync_hook` | Stop | `asyncio.to_thread(journal_manager.sync)` |
| `slack_format_hook` | PostToolUse | Markdown normalization |

Note: `SessionEnd` is not available as a Python SDK callback hook (TypeScript only). Git sync uses the `Stop` hook instead.

## Setup

```bash
# Clone
git clone https://github.com/tyoon10/optimind.git
cd optimind/optimind-sdk

# Install
pip install -r requirements.txt

# Configure
cp .env.example .env
# Edit .env with your keys

# Run
python -m uvicorn src.server:app --host 0.0.0.0 --port 8000
```

### Environment Variables

| Variable | Required | Purpose |
|---|---|---|
| `ANTHROPIC_API_KEY` | Yes | Claude API access |
| `SLACK_BOT_TOKEN` | Yes | Slack bot token |
| `SLACK_SIGNING_SECRET` | Yes | Slack webhook verification |
| `GITHUB_PAT` | No | Git sync for journal (omit for local-only) |
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
| 3.0 | Mar 2026 | Claude Agent SDK | Full migration — this version |

See [CHANGELOG.md](../CHANGELOG.md) for detailed release notes.

## What Stayed the Same

The data layer is identical. Same flat-file markdown journal, same `state.json` schema, same `user_profile.json` format, same git sync strategy. The Slack integration layer (FastAPI + Slack-Bolt, deduplication, retry-ignore) is preserved with minimal changes.

The migration replaced the orchestration and LLM layers only.

## Lessons Learned

1. **CLAUDE.md is genuinely better than prompt templates.** No string formatting, no injection bugs, automatic prompt caching, survives compaction. The 136-line template became 60 lines of plain markdown.

2. **Tools > prompt injection for dynamic data.** Letting the agent decide what context to fetch (vs. dumping everything) reduced average token usage and made the agent smarter about what it reads.

3. **Hooks revive abandoned features for free.** The ReflectorAgent was 65 lines of LangChain structured output code with a dedicated routing path. The equivalent hook is 20 lines with no routing overhead.

4. **Subagents solve the problem that killed multi-agent.** LangGraph's routing overhead made specialists impractical. Agent SDK subagents have zero routing cost — Claude decides when to delegate as part of its normal reasoning.

5. **`SessionEnd` is TypeScript-only in the Python SDK.** Plan for this if you need session lifecycle hooks in Python.

## License

MIT — see [LICENSE](../LICENSE).
