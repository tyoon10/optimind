"""
Configuration — simplified from v1.

Removed: GOOGLE_API_KEY, GOOGLE_PROJECT_ID, GOOGLE_LOCATION, GEMINI_MODEL,
         dual-provider validation logic.
Added: ANTHROPIC_API_KEY.
Preserved: Slack tokens, GitHub PAT, journal repo URL, path resolution.
"""

import os
from dotenv import load_dotenv

load_dotenv()


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
        self.DATA_DIR = os.path.join(self.BASE_DIR, "data")

        self._validate()

    def _validate(self):
        errors = []
        if not self.ANTHROPIC_API_KEY:
            errors.append("Missing ANTHROPIC_API_KEY")
        if not self.SLACK_BOT_TOKEN:
            errors.append("Missing SLACK_BOT_TOKEN")
        if not self.SLACK_SIGNING_SECRET:
            errors.append("Missing SLACK_SIGNING_SECRET")
        if errors:
            raise EnvironmentError(f"Configuration Errors: {', '.join(errors)}")


config = Config()
