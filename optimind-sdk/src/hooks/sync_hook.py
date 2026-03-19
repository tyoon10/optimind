"""
Sync hook — git commit and push journal changes.

Fires on: Stop (after each agent turn completes)
Replaces: asyncio.to_thread(journal_manager.sync) in slack.py (line 47)

Note: SessionEnd is not available as a Python SDK callback hook (TypeScript only).
Using Stop as the trigger instead. This fires after each turn, which means
we sync more frequently than v1 (which synced once after the Slack response).
This is acceptable — git push is idempotent, and frequent syncs reduce data loss risk.
"""

import os
import asyncio

from claude_agent_sdk import HookMatcher

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
JOURNAL_DIR = os.path.join(BASE_DIR, "data", "journal")


def _git_sync():
    """Synchronous git sync — runs in a thread to avoid blocking the event loop."""
    try:
        from git import Repo, GitCommandError

        if not os.path.exists(os.path.join(JOURNAL_DIR, ".git")):
            return  # No repo, nothing to sync

        repo = Repo(JOURNAL_DIR)

        # Pull first to avoid conflicts
        try:
            repo.git.pull("origin", "main")
        except GitCommandError as e:
            print(f"Git pull warning: {e}")

        # Commit and push if dirty
        if repo.is_dirty(path=JOURNAL_DIR) or repo.untracked_files:
            import datetime

            msg = f"Journal Sync {datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}"
            repo.git.add(JOURNAL_DIR)
            repo.index.commit(msg)
            repo.git.push()

    except ImportError:
        pass  # GitPython not installed — skip sync
    except Exception as e:
        print(f"Git sync error: {e}")


async def on_stop(input_data, tool_use_id, context):
    """Fire-and-forget git sync after each turn."""
    try:
        await asyncio.to_thread(_git_sync)
    except Exception as e:
        print(f"Sync hook error: {e}")
    return {}


sync_hook_matcher = HookMatcher(hooks=[on_stop])
