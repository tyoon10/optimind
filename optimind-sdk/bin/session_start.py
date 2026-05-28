#!/usr/bin/env python3
"""
Claude Code `SessionStart` hook entrypoint (wired in .claude/settings.json).

Runs once when a CC session opens in the optimind repo: ensures the
optimind-journal checkout exists (clone/pull) and exports the resolved
OPTIMIND_JOURNAL_PATH to $CLAUDE_ENV_FILE so later Bash tool calls see it.
(The MCP tools read the path from .mcp.json's env block — see Task 4.)

Never fails the session: any error is reported on stderr and swallowed.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.bootstrap import ensure_journal


def main() -> int:
    try:
        path = ensure_journal()
    except Exception as e:  # ensure_journal is best-effort, but never crash the session
        print(f"session_start: journal bootstrap error: {e}", file=sys.stderr)
        return 0

    env_file = os.getenv("CLAUDE_ENV_FILE")
    if path and env_file:
        try:
            with open(env_file, "a", encoding="utf-8") as f:
                f.write(f"export OPTIMIND_JOURNAL_PATH={path}\n")
        except OSError as e:
            print(f"session_start: could not write CLAUDE_ENV_FILE: {e}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
