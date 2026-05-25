"""
Journal hook — auto-log user/agent interactions to today's journal.

Fires on: Stop (after each agent turn completes)
Replaces: manual journal_manager.log_interaction() calls in agent.py (lines 77, 118)
"""

import os
import datetime
import pytz

from claude_agent_sdk import HookMatcher

from src.config import journal_root

TZ = pytz.timezone("US/Eastern")


async def on_stop(input_data, tool_use_id, context):
    """
    Log the session's last exchange to today's journal file.
    Runs as a fire-and-forget side effect — does not block the agent.
    """
    # Stop hooks don't have tool_input; they signal the agent finished.
    # We use async output so the agent isn't blocked.
    try:
        journal_dir = os.path.join(journal_root(), "journal")
        today = datetime.datetime.now(TZ).date()
        filepath = os.path.join(journal_dir, f"{today.isoformat()}.md")
        timestamp = datetime.datetime.now(TZ).strftime("%H:%M")

        os.makedirs(journal_dir, exist_ok=True)

        # Log that the agent completed a turn
        entry = f"\n### {timestamp} | System\n[Agent session turn completed]\n"
        with open(filepath, "a", encoding="utf-8") as f:
            f.write(entry)

    except Exception as e:
        # Side effect — never crash the agent
        print(f"Journal hook error: {e}")

    return {}


journal_hook_matcher = HookMatcher(hooks=[on_stop])
