"""
OptiMind Agent — main agent configuration using Claude Agent SDK.

Replaces: src/core/agent.py (135 lines of prompt template + retry + response parsing)
This file: agent config + MCP server registration + query interface.
"""

import asyncio
from typing import AsyncIterator, Optional

from claude_agent_sdk import (
    query,
    ClaudeAgentOptions,
    AgentDefinition,
    ResultMessage,
    HookMatcher,
    create_sdk_mcp_server,
)

from src.tools.journal import journal_tools
from src.tools.state import state_tools
from src.tools.preferences import preference_tools
from src.subagents.definitions import SUBAGENTS
from src.hooks.journal_hook import journal_hook_matcher
from src.hooks.reflector_hook import reflector_hook_matcher
from src.hooks.sync_hook import sync_hook_matcher
from src.hooks.slack_format_hook import slack_format_hook_matcher
from src.hooks.user_prompt_hook import user_prompt_hook_matcher


# Register all custom tools under a single MCP server
optimind_tools = create_sdk_mcp_server(
    name="optimind",
    version="2.0.0",
    tools=journal_tools + state_tools + preference_tools,
)

# Tool names follow the MCP convention: mcp__{server}__{tool}
TOOL_NAMES = [
    # Journal
    "mcp__optimind__get_recent_journal",
    "mcp__optimind__search_journal",
    "mcp__optimind__log_entry",
    # State
    "mcp__optimind__get_state",
    "mcp__optimind__set_state",
    # Preferences
    "mcp__optimind__get_rules",
    "mcp__optimind__add_rule",
    "mcp__optimind__delete_rule",
]


def get_agent_options(session_id: Optional[str] = None) -> ClaudeAgentOptions:
    """
    Build agent options. If session_id is provided, resumes that session.
    """
    opts = ClaudeAgentOptions(
        mcp_servers={"optimind": optimind_tools},
        allowed_tools=TOOL_NAMES + ["Agent", "web_search"],
        agents=SUBAGENTS,
        setting_sources=["project"],  # loads CLAUDE.md from working directory
        max_turns=20,
        effort="medium",
        hooks={
            "UserPromptSubmit": [user_prompt_hook_matcher],
            "Stop": [journal_hook_matcher, reflector_hook_matcher, sync_hook_matcher],
            "PostToolUse": [slack_format_hook_matcher],
        },
    )

    if session_id:
        opts.resume = session_id

    return opts


async def run_agent(user_input: str, session_id: Optional[str] = None) -> tuple[str, str]:
    """
    Run OptiMind agent on a user message.

    Returns: (response_text, session_id)
    """
    options = get_agent_options(session_id)

    result_text = ""
    new_session_id = session_id or ""

    async for message in query(prompt=user_input, options=options):
        if isinstance(message, ResultMessage):
            new_session_id = message.session_id or new_session_id
            if message.subtype == "success":
                result_text = message.result or ""
            else:
                result_text = f"Agent stopped: {message.subtype}"

    return result_text, new_session_id
