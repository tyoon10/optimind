"""
Path resolution for the journal root — deliberately decoupled from Config().

Tools, hooks, AND the standalone MCP server (bin/optimind_mcp_server.py) import
`journal_root` from here so they can resolve data paths WITHOUT triggering
`Config()` validation, which refuses to load when API/Slack keys are absent (as
in a fresh `claude`-CLI clone). `src.config` re-exports this name for
backward-compatibility, so existing `from src.config import journal_root` keeps
working.
"""

import os


def journal_root() -> str:
    """Resolve the journal/profile/state root from OPTIMIND_JOURNAL_PATH.

    Falls back to the in-repo ``data/`` dir when unset (development only).
    """
    env_path = os.getenv("OPTIMIND_JOURNAL_PATH")
    if env_path:
        return os.path.abspath(os.path.expanduser(env_path))
    return os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data"
    )
