"""
Smoke test — verify the Agent SDK can run with our custom tools.
Run from the optimind-sdk/ directory:
    python test_agent.py
"""

import asyncio
import os
import sys

# Ensure imports resolve from project root
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from claude_agent_sdk import query, ClaudeAgentOptions, ResultMessage, create_sdk_mcp_server
from src.tools.journal import journal_tools
from src.tools.state import state_tools
from src.tools.preferences import preference_tools


async def main():
    # Minimal test: just tools, no hooks/subagents/CLAUDE.md
    server = create_sdk_mcp_server(
        name="optimind",
        version="2.0.0",
        tools=journal_tools + state_tools + preference_tools,
    )

    tool_names = [
        "mcp__optimind__get_recent_journal",
        "mcp__optimind__search_journal",
        "mcp__optimind__log_entry",
        "mcp__optimind__get_state",
        "mcp__optimind__set_state",
        "mcp__optimind__get_rules",
        "mcp__optimind__add_rule",
        "mcp__optimind__delete_rule",
    ]

    options = ClaudeAgentOptions(
        mcp_servers={"optimind": server},
        allowed_tools=tool_names,
        max_turns=5,
        effort="low",
    )

    print("Running OptiMind Agent SDK smoke test...")
    print("Prompt: 'What is my current state and what nutrition rules do I have?'\n")

    async for message in query(
        prompt="What is my current state and what nutrition rules do I have?",
        options=options,
    ):
        if isinstance(message, ResultMessage):
            print(f"\n--- Result (subtype: {message.subtype}) ---")
            if message.subtype == "success":
                print(message.result)
            else:
                print(f"Stopped: {message.subtype}")
            if message.total_cost_usd is not None:
                print(f"\nCost: ${message.total_cost_usd:.4f}")
            print(f"Turns: {message.num_turns}")
            print(f"Session ID: {message.session_id}")


if __name__ == "__main__":
    asyncio.run(main())
