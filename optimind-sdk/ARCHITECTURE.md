# OptiMind SDK — Architecture Document

## 1. Problems with the Current System

### Problem 1: Context Dumping

Every message injects the full system state into the prompt regardless of relevance.

```
agent.py:60-96 — every turn executes all of these:
  journal_manager.sync(push=False)          # git pull
  state_manager.get_state()                 # read state.json
  journal_manager.get_recent_context(5)     # read 5 days of markdown
  memory_store.get_context_str()            # read all preference rules
```

A "Hi" message loads ~3,000 tokens of journal history, state, and rules. A "What should I eat?" loads the same 3,000 tokens — even though it only needs nutrition rules and today's meals.

**Cost**: Fixed ~3K tokens/turn regardless of query complexity.
**Failure mode**: As journal grows, context window fills faster. No way to search — only chronological dump.

### Problem 2: Read-Only Agent

The agent cannot modify its own state or learn new preferences. State and rules are injected into the prompt as static text:

```python
# agent.py:88-96 — all injected as template variables
invoke_params = {
    "system_mode": active_state.get("system_mode", "STANDARD"),
    "constraints": active_state.get("active_constraints", []),
    "focus": active_state.get("current_focus", {}),
    "journal_history": journal_history,
    "user_profile": user_profile,
    ...
}
```

If the user says "I have an exam Friday, switch to exam mode," the agent can acknowledge the request but cannot actually write to `state.json`. If the user says "I'm not doing keto anymore," the agent cannot update `user_profile.json`.

### Problem 3: Dead Preference Learning

The `ReflectorAgent` (65 lines in `legacy/agents/reflector_agent.py`) used LangChain structured output to extract implicit preferences from conversation. It was abandoned in v2.0 when the multi-agent Star Topology was collapsed into a single agent — the routing overhead wasn't worth the benefit.

Users cannot teach OptiMind through conversation. Every preference must be manually added to `user_profile.json`.

### Problem 4: No Conversation Continuity

Every Slack message is a stateless LLM call. There is no session state between messages.

```
User: "Plan my week"        → fresh LLM call with 5-day journal dump
User: "Move gym to Thursday" → fresh LLM call — has no idea what "my week" plan was
```

The only continuity mechanism is the journal (raw message logs), which is too noisy for the agent to reconstruct prior reasoning.

### Problem 5: Abandoned Multi-Agent Architecture

v1.0 used a LangGraph Star Topology: orchestrator → classifier → specialist agents (nutritionist, scheduler, medical, chit-chat). Abandoned in v2.0 because:

- Routing overhead added latency without proportional quality gain
- Each specialist duplicated most of the system prompt
- Adding a new domain required rewiring the LangGraph graph definition
- The classifier was a separate LLM call just to pick which specialist to invoke

The consolidation into a single `OptiMindAgent` was correct — but it killed the ability to have deep domain-specific reasoning without bloating the single prompt.

### Problem 6: Missing Feedback Loop

`ARCHITECTURE_COMPARISON.md` identifies a gap: no "nightly review" or trend analysis capability. The system logs interactions but never analyzes them. "How did my sleep affect productivity this week?" is unanswerable — the agent can surface raw journal entries but cannot correlate across days.

This was identified as a desired feature but never built because LangGraph made adding new agents impractical (see Problem 5).

### Problem 7: LLM Plumbing Overhead

Three categories of code exist solely to handle Gemini-specific behavior:

1. **LLM factory** (`llm.py`): Google AI Studio primary, Vertex AI fallback, model selection logic
2. **Retry logic** (`agent.py:98-133`): exponential backoff for Gemini 503 errors
3. **Response parsing** (`agent.py:106-115`): Gemini returns multimodal `list[dict]` with `{'text': ...}` parts; requires manual extraction and `**` → `*` normalization

~80 lines of code that exist only because the LLM provider doesn't handle these concerns.

### Problem 8: Tangled Side Effects

Journal logging, git sync, and response formatting are interleaved with core agent logic:

```python
# agent.py — side effects mixed into the reasoning flow
journal_manager.log_interaction("User", user_input)     # line 77
# ... LLM call happens ...
journal_manager.log_interaction("OptiMind", content)     # line 118

# slack.py — sync after response
await asyncio.to_thread(journal_manager.sync, push=True) # line 47
```

Adding any new side effect (analytics, preference extraction, formatting) means modifying the core agent code.

---

## 2. Design Choices for the Agent SDK Rebuild

### Design Choice 1: CLAUDE.md for Static Context

**Problem addressed**: #1 (Context Dumping), #7 (LLM Plumbing)

Move the persona, core directives, and permanent rules into `CLAUDE.md`. This file is:
- Loaded at session start and re-injected on every request automatically
- Prompt-cached by the SDK (pay full cost once, cached thereafter)
- Never lost to compaction (unlike conversation history)
- Plain markdown — no string template formatting

**What goes in CLAUDE.md** (static, rarely changes):
- "Performance Architect" persona and tone directives
- Core reasoning principles (holistic, chain-of-thought, safety)
- Output/formatting conventions (the 3.0 design listed Slack mrkdwn here; removed with Slack in 4.0.0)
- Timezone and locale
- Compaction preservation instructions

**What does NOT go in CLAUDE.md** (dynamic, fetched via tools):
- Current state/mode/constraints
- Journal history
- Mutable preference rules

**Best practice alignment**: The Agent SDK docs explicitly state: *"Persistent rules belong in CLAUDE.md rather than in the initial prompt, because CLAUDE.md content is re-injected on every request."*

### Design Choice 2: Custom Tools for Dynamic Data

**Problem addressed**: #1 (Context Dumping), #2 (Read-Only Agent)

Expose state, journal, and preferences as callable tools instead of prompt-injected blobs:

| Tool | Reads | Writes | Why |
|---|---|---|---|
| `get_state()` | state.json | — | Agent checks mode/constraints only when relevant |
| `set_state(mode, constraints, focus)` | — | state.json | Agent can switch modes autonomously |
| `get_recent_journal(days)` | journal/*.md | — | Agent pulls only the days it needs |
| `search_journal(query, days)` | journal/*.md | — | Agent can search for patterns, not just dump chronologically |
| `log_entry(role, content)` | — | journal/today.md | Agent logs interactions |
| `get_rules(topic)` | user_profile.json | — | Agent fetches rules filtered by domain |
| `add_rule(topic, rule, confidence)` | — | user_profile.json | Agent can learn new preferences |
| `delete_rule(topic, content)` | — | user_profile.json | Agent can remove outdated rules |

**Key shift**: The agent decides what context it needs based on the query, rather than receiving everything on every turn.

**Best practice alignment**: The SDK docs on context efficiency: *"Use subagents for subtasks... Be selective with tools."* Tools make context consumption proportional to query complexity.

### Design Choice 3: Hooks for Side Effects

**Problem addressed**: #3 (Dead Preference Learning), #8 (Tangled Side Effects)

Decouple side effects from core agent logic using SDK hooks:

| Hook | Event | Replaces |
|---|---|---|
| `user_prompt_hook` | UserPromptSubmit | Verbatim user-message logging (runtime guarantee) |
| `journal_hook` | Stop | Manual `log_interaction()` calls in agent.py (lines 77, 118) |
| `reflector_hook` | Stop | Entire `ReflectorAgent` class (65 lines, abandoned in v2.0) |
| `sync_hook` | Stop | `asyncio.to_thread(journal_manager.sync)` (the v1 Slack handler) |

**`sync_hook` fires on `Stop`, not `SessionEnd`:** `SessionEnd` is not available as a Python SDK
callback hook (TypeScript only), so the git sync runs on `Stop` after each turn instead. This is
what `src/hooks/sync_hook.py` registers (`on_stop` → `HookMatcher`) and what `src/agent.py` wires
under the `"Stop"` event. Frequent syncs are acceptable: `git push` is idempotent and more frequent
syncs reduce data-loss risk.

**Reflector revival**: The Stop hook analyzes the conversation for implicit preference statements after each turn. If detected, it calls `add_rule()` or `delete_rule()`. Same behavior as the abandoned `ReflectorAgent`, ~20 lines instead of 65, no routing overhead.

**Best practice alignment**: SDK docs: *"Hooks run in your application process, not inside the agent's context window, so they don't consume context."*

### Design Choice 4: Subagents for Domain Expertise

**Problem addressed**: #5 (Abandoned Multi-Agent), #6 (Missing Feedback Loop)

Three subagents, each with a focused system prompt and restricted tool access:

| Subagent | Domain | Tools | New? |
|---|---|---|---|
| `nutritionist` | Nutrition, health, meals | `get_rules(nutrition)`, `search_journal`, Read | Revived from v1.0 |
| `scheduler` | Scheduling, deep work, circadian | `get_state`, `set_state`, `get_rules(scheduling)`, `search_journal` | Revived from v1.0 |
| `analyst` | Journal trend analysis, pattern correlation | `get_recent_journal`, `search_journal`, Read, Glob | NEW |

**Why this works when LangGraph didn't**:
- No routing graph — Claude decides which subagent to invoke based on natural language understanding
- No classifier LLM call — delegation is a tool call, not a separate inference
- Context isolation is free — each subagent gets its own context window
- Adding a new domain = adding one file, not rewiring a graph

**The Analyst fills Problem 6**: "Analyze my sleep patterns this week" triggers the analyst subagent, which reads 7-30 days of journal and identifies cross-day correlations. This was architecturally impossible in the old system.

### Design Choice 5: Session Persistence

**Problem addressed**: #4 (No Conversation Continuity)

Each conversation gets a persistent Agent SDK session, resumed by `session_id` (`src/agent.py`
threads it through `run_agent`). The session maintains full conversation state across turns:

```
User: "Plan my week"           → session created, plan generated
User: "Move gym to Thursday"   → session resumed, agent has full plan context
User: "Optimize meals around that" → session resumed, agent knows the schedule
```

Session IDs stored in a simple dict (MVP) or Redis (production). The SDK handles context management, compaction, and resumption.

**Best practice alignment**: SDK docs on sessions: *"When you resume, the full context from previous turns is restored: files that were read, analysis that was performed, and actions that were taken."*

### Design Choice 6: Eliminate the LLM Abstraction Layer

**Problem addressed**: #7 (LLM Plumbing Overhead)

Delete entirely:
- `llm.py` — LLM factory with Google AI Studio / Vertex AI fallback
- Retry logic in `agent.py:98-133` — SDK handles retries internally
- Response parsing in `agent.py:106-115` — Claude returns clean text, no multimodal part extraction

**Dependencies removed**: `langchain`, `langgraph`, `langchain-core`, `langchain-google-genai`, `langchain-google-vertexai`, `aiohttp`

**Dependencies added**: `claude-agent-sdk`

Net reduction: 14 packages → ~4 packages.

### Design Choice 7: Preserve What Works

Not everything changes. These components are architecturally sound and carry over:

| Component | Status | Rationale |
|---|---|---|
| Flat-file markdown journal | Preserved | Simple, git-syncable, human-readable |
| Git sync strategy | Preserved | Pull before read, push after write, PAT auth |
| `state.json` format | Preserved | Clean schema, works as tool backing store |
| `user_profile.json` format | Preserved (schema 1.1) | JSON-Schema validated; bumped 1.0 → 1.1 in 4.1.0 |
| Slack-Bolt integration | ~~Preserved~~ Removed in 4.0.0 | Cloud-native pivot dropped Slack entirely |
| FastAPI server | ~~Preserved~~ Removed in 4.0.0 | No long-running host; entrypoint is now the stdio MCP server |
| EST timezone handling | Preserved | User is in NYC, journal dates must match local time |
| Deduplication logic | ~~Preserved~~ N/A post-4.0.0 | Was Slack-event dedup; no webhook surface remains |

---

## 3. Architecture Diagram

> **Note (post-4.0.0):** the 3.0 migration originally fronted the Agent SDK runtime with the v2
> Slack + FastAPI server. The 4.0.0 cloud-native pivot **removed that server entirely** (`server.py`,
> the Slack hook, the `slack-bolt` dependency). The diagram below reflects the current local SDK: the
> entrypoint is a stdio MCP server (`bin/optimind_mcp_server.py`, registered in the repo-root
> `../.mcp.json`) driven by the `claude` CLI; the in-process `src/agent.py` runtime is retained for the
> `test_agent.py` smoke path. See [README.md](README.md#architecture) for the full two-transport
> picture and the cloud-native vs. local relationship.

```
claude CLI ── stdio ──▶ bin/optimind_mcp_server.py ──▶ src/mcp_server.py:run()
                                                            │
                          (in-process alt: src/agent.py via create_sdk_mcp_server)
                                                            │
                                          shared pure handlers (src/tools/*.py)
                                                            │
    ┌───────────────────────────────────────────────────────────────────────┐
    │  Agent SDK Runtime                                                      │
    │  ┌───────────────────────┐                                             │
    │  │ CLAUDE.md (static)    │  ← Persona, directives                      │
    │  │ Tools (dynamic)       │  ← Journal, State, Preferences, Daily       │
    │  │ Subagents (optional)  │  ← Nutritionist, Scheduler, Analyst         │
    │  │ Hooks (side effects)  │  ← UserPrompt log, Journal, Reflector, Sync │
    │  └───────────────────────┘                                             │
    └───────────────────────────────┬───────────────────────────────────────┘
                                     ▼
┌─────────────────────────────────────────────────────────┐
│  Data Layer — private optimind-journal checkout          │
│  resolved from $OPTIMIND_JOURNAL_PATH                    │
│  ├── journal/*.md         ← Flat-file markdown, git-synced│
│  ├── state.json           ← Mode, constraints, focus      │
│  ├── daily/*.json         ← Structured daily logs         │
│  └── user_profile.json    ← Preference rules (schema 1.1) │
└─────────────────────────────────────────────────────────┘
```

## 4. Risk Register

| Risk | Impact | Mitigation |
|---|---|---|
| Agent SDK Python is early (v0.1.48) — API may change | Medium | Pin version, isolate SDK calls behind thin adapter |
| Multi-tool-call latency exceeds single prompt-injected call | Medium | Read-only tools run in parallel; simple queries skip most tools |
| Claude is more expensive per token than Gemini 3 Flash | Medium | Fewer tokens per turn on average; prompt caching on CLAUDE.md |
| Vendor lock-in (Anthropic-only, no fallback) | Low | Acceptable for interview demo; production could add Bedrock/Vertex provider |
| Hook execution order not guaranteed across hook types | Low | Keep hooks independent; no hook depends on another hook's output |
