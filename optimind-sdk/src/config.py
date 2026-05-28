"""
Configuration — simplified from v1.

Removed: GOOGLE_API_KEY, GOOGLE_PROJECT_ID, GOOGLE_LOCATION, GEMINI_MODEL,
         dual-provider validation logic.
Added: ANTHROPIC_API_KEY, OPTIMIND_JOURNAL_PATH.
Preserved: Slack tokens, GitHub PAT, journal repo URL, path resolution.

OPTIMIND_JOURNAL_PATH is the runtime coupling to the optimind-journal repo
(see schemas/optimind_interface.md). When set, all journal/profile/state I/O
resolves under that path. When unset, the legacy in-repo data/ directory is
used and a warning is logged.
"""

import logging
import os
from dotenv import load_dotenv

from src.paths import journal_root  # re-exported for backward-compat; see src/paths.py

load_dotenv()

logger = logging.getLogger(__name__)


class Config:
    def __init__(self):
        self.ENV = os.getenv("OPTIMIND_ENV", "development")

        # Anthropic (replaces Google AI Studio / Vertex AI)
        self.ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")

        # Slack
        self.SLACK_BOT_TOKEN = os.getenv("SLACK_BOT_TOKEN")
        self.SLACK_SIGNING_SECRET = os.getenv("SLACK_SIGNING_SECRET")

        # Git / Journal
        self.GITHUB_PAT = os.getenv("GITHUB_PAT")
        self.JOURNAL_REPO_URL = os.getenv("JOURNAL_REPO_URL")

        # Paths
        self.BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.JOURNAL_PATH = self._resolve_journal_path()
        self.DATA_DIR = self.JOURNAL_PATH  # back-compat alias

        self._validate()

    def _resolve_journal_path(self) -> str:
        """
        Resolve the journal/profile/state root.

        Precedence:
        1. OPTIMIND_JOURNAL_PATH env var (the canonical binding).
        2. Legacy in-repo <optimind-sdk>/data/ (warns).
        """
        env_path = os.getenv("OPTIMIND_JOURNAL_PATH")
        if env_path:
            return os.path.abspath(os.path.expanduser(env_path))

        fallback = os.path.join(self.BASE_DIR, "data")
        logger.warning(
            "OPTIMIND_JOURNAL_PATH not set; falling back to %s. "
            "Set OPTIMIND_JOURNAL_PATH to point at your optimind-journal checkout for production.",
            fallback,
        )
        return fallback

    def _validate(self):
        errors = []
        if not self.ANTHROPIC_API_KEY:
            errors.append("Missing ANTHROPIC_API_KEY")
        if not self.SLACK_BOT_TOKEN:
            errors.append("Missing SLACK_BOT_TOKEN")
        if not self.SLACK_SIGNING_SECRET:
            errors.append("Missing SLACK_SIGNING_SECRET")
        if self.ENV == "production" and not os.getenv("OPTIMIND_JOURNAL_PATH"):
            errors.append("OPTIMIND_JOURNAL_PATH must be set in production")
        if errors:
            raise EnvironmentError(f"Configuration Errors: {', '.join(errors)}")


config = Config()
