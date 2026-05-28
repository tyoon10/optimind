"""
Journal bootstrap — ensure the optimind-journal checkout exists and that
OPTIMIND_JOURNAL_PATH points at it, before the first tool call.

Two runtimes need this (USER_FLOW_PLAN §10.3 Task 3, decisions log 2026-05-28):

- **SDK app** (`server.py`): call `ensure_journal()` at startup. It sets
  `os.environ["OPTIMIND_JOURNAL_PATH"]` for the in-process tools.
- **CC mobile session**: a `.claude/settings.json` `SessionStart` shell hook runs
  `bin/session_start.py`, which calls `ensure_journal()` (clone/pull) and exports
  the resolved path to `$CLAUDE_ENV_FILE`. NOTE: the MCP tools get the path from
  `.mcp.json`'s `env` block (Task 4), because `$CLAUDE_ENV_FILE` only affects Bash
  tool calls — the hook's real job there is to make the repo exist on disk.

This module is deliberately self-contained: it reads env vars directly and does
NOT import `src.config`, so it stays usable in a fresh clone where Config() would
refuse to load (no API keys yet). `SessionStart` is intentionally NOT an SDK
callback hook — that event is unavailable in the Python Agent SDK.
"""

import logging
import os

logger = logging.getLogger(__name__)

DEFAULT_JOURNAL_HOME = "~/.optimind/optimind-journal"


def default_journal_path() -> str:
    """Where to clone the journal when OPTIMIND_JOURNAL_PATH is unset."""
    return os.path.abspath(os.path.expanduser(
        os.getenv("OPTIMIND_JOURNAL_HOME", DEFAULT_JOURNAL_HOME)))


def _is_git_checkout(path: str) -> bool:
    return os.path.isdir(os.path.join(path, ".git"))


def plan_bootstrap(journal_path, repo_url, *, path_exists, is_git):
    """
    Pure decision (unit-tested). Given the env + filesystem facts, return the action:
      "ready"   — path is an existing non-git dir (e.g. a bind-mounted checkout); use as-is.
      "pull"    — path exists and is a git checkout; refresh it.
      "clone"   — path missing but a repo_url is configured; clone it.
      "missing" — OPTIMIND_JOURNAL_PATH set to a non-existent path, no url to recover.
      "noop"    — nothing set and no url; caller falls back to the in-repo data/ dir (dev).
    """
    if journal_path:
        if not path_exists:
            return "clone" if repo_url else "missing"
        return "pull" if is_git else "ready"
    # unset → consider the default clone location
    if path_exists:
        return "pull" if is_git else "ready"
    return "clone" if repo_url else "noop"


def _authed_url(repo_url: str, pat: str) -> str:
    """Inject a PAT into an https GitHub URL so a private journal can be cloned."""
    if pat and repo_url.startswith("https://") and "@" not in repo_url:
        return repo_url.replace("https://", f"https://{pat}@", 1)
    return repo_url


def ensure_journal():
    """
    Resolve / clone / pull the journal and ensure OPTIMIND_JOURNAL_PATH is set.
    Idempotent and best-effort: never raises — a bootstrap failure must not block
    the session. Returns the resolved path, or None when there's nothing to bind.
    """
    journal_path = os.getenv("OPTIMIND_JOURNAL_PATH")
    repo_url = os.getenv("JOURNAL_REPO_URL")
    pat = os.getenv("GITHUB_PAT")

    target = journal_path or default_journal_path()
    action = plan_bootstrap(
        journal_path, repo_url,
        path_exists=os.path.isdir(target),
        is_git=_is_git_checkout(target),
    )

    if action == "missing":
        logger.warning("OPTIMIND_JOURNAL_PATH=%s does not exist and no JOURNAL_REPO_URL "
                       "is set to recover it.", target)
        return journal_path
    if action == "noop":
        logger.warning("No OPTIMIND_JOURNAL_PATH and no JOURNAL_REPO_URL; the runtime will "
                       "fall back to the in-repo data/ dir. Set one for production.")
        return None

    try:
        if action == "clone":
            logger.info("Cloning journal into %s", target)
            _git_clone(_authed_url(repo_url, pat), target)
        elif action == "pull":
            _git_pull(target)
    except Exception as e:  # GitPython missing, network/auth error, etc.
        logger.warning("Journal bootstrap (%s) failed: %s", action, e)

    if os.path.isdir(target):
        os.environ["OPTIMIND_JOURNAL_PATH"] = target
        return target
    return journal_path or None


def _git_clone(url: str, target: str) -> None:
    from git import Repo
    os.makedirs(os.path.dirname(target) or ".", exist_ok=True)
    Repo.clone_from(url, target)


def _git_pull(target: str) -> None:
    try:
        from git import Repo, GitCommandError
    except ImportError:
        return  # GitPython not installed — skip refresh, the checkout still works
    try:
        Repo(target).git.pull("origin", "main")
    except GitCommandError as e:
        logger.warning("Journal pull warning: %s", e)
