"""
Reflector hook — extract implicit preferences from conversation.

Fires on: Stop (after each agent turn completes)
Replaces: ReflectorAgent class (65 lines, abandoned in v2.0)
Revives preference learning without multi-agent routing overhead.

How it works:
- Injects a system message asking the agent to reflect on whether
  the user expressed any new preferences or revoked existing ones.
- The agent can then call add_rule/delete_rule tools on its next turn.
- This is a lightweight nudge, not a separate LLM call.
"""

from claude_agent_sdk import HookMatcher


async def on_stop(input_data, tool_use_id, context):
    """
    After each turn, inject a system message prompting the agent to
    check whether implicit preferences were expressed.
    """
    return {
        "systemMessage": (
            "Reflect: did the user just express a new preference, constraint, or revoke "
            "an existing one? If so, use add_rule or delete_rule to update their profile. "
            "If not, ignore this message."
        ),
    }


reflector_hook_matcher = HookMatcher(hooks=[on_stop])
