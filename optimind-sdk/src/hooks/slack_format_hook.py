"""
Slack format hook — convert markdown to Slack mrkdwn in tool outputs.

Fires on: PostToolUse (after any tool returns a result)
Purpose: ensure any text the agent will relay to Slack is properly formatted.

Note: The primary formatting rules are in CLAUDE.md (the agent generates Slack-native
formatting from the start). This hook is a safety net for edge cases where markdown
leaks through, especially from subagent responses.
"""

import re

from claude_agent_sdk import HookMatcher


async def on_post_tool_use(input_data, tool_use_id, context):
    """
    Post-process tool outputs to convert any remaining markdown to Slack mrkdwn.
    """
    tool_output = input_data.get("tool_output", "")
    if not isinstance(tool_output, str):
        return {}

    # Only process if markdown artifacts are present
    if "**" not in tool_output and "###" not in tool_output:
        return {}

    cleaned = tool_output
    # **bold** → *bold*
    cleaned = re.sub(r"\*\*(.+?)\*\*", r"*\1*", cleaned)
    # ### Header → *Header*
    cleaned = re.sub(r"^#{1,3}\s+(.+)$", r"*\1*", cleaned, flags=re.MULTILINE)

    if cleaned != tool_output:
        return {
            "hookSpecificOutput": {
                "hookEventName": input_data["hook_event_name"],
                "additionalContext": f"[Formatted for Slack]\n{cleaned}",
            }
        }

    return {}


slack_format_hook_matcher = HookMatcher(hooks=[on_post_tool_use])
