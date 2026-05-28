"""
User prompt hook — append the raw user message to today's journal verbatim.

Fires on: UserPromptSubmit (before the model sees the turn).
This is the ONLY hook point where the user's input is guaranteed unmodified,
so this is where the "every user message is logged verbatim" contract is
enforced. See schemas/journal_entry.schema.md (User role) and the Architecture
section of CLAUDE.md.

Contract:
- The full prompt string is written. No truncation, no summarization, no
  redaction. (Redaction, if ever needed, belongs in a separate downstream
  filter — not here.)
- No dedup. Identical messages on different turns are still recorded; the
  duplication is itself signal.
- Failure to write is logged but never raised — logging must not break the
  user's turn.
"""

import datetime
import os

import pytz
from claude_agent_sdk import HookMatcher

from src.config import journal_root

TZ = pytz.timezone("US/Eastern")


async def on_user_prompt(input_data, tool_use_id, context):
    try:
        prompt = input_data.get("prompt", "") if isinstance(input_data, dict) else getattr(input_data, "prompt", "")
        if not prompt:
            return {}

        journal_dir = os.path.join(journal_root(), "journal")
        os.makedirs(journal_dir, exist_ok=True)

        now = datetime.datetime.now(TZ)
        filepath = os.path.join(journal_dir, f"{now.date().isoformat()}.md")
        timestamp = now.strftime("%H:%M")

        # Verbatim — see module docstring.
        entry = f"\n### {timestamp} | User\n{prompt}\n"
        with open(filepath, "a", encoding="utf-8") as f:
            f.write(entry)

    except Exception as e:
        # Never break the user's turn over a logging failure.
        print(f"User prompt hook error: {e}")

    return {}


user_prompt_hook_matcher = HookMatcher(hooks=[on_user_prompt])
