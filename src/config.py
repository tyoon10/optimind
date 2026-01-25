import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

class Config:
    """Centralized configuration for OptiMind."""
    
    # Environment
    ENV = os.getenv("OPTIMIND_ENV", "development")
    IsDev = ENV == "development"
    
    # Google / Vertex AI
    GOOGLE_PROJECT_ID = os.getenv("GOOGLE_PROJECT_ID")
    GOOGLE_LOCATION = os.getenv("GOOGLE_LOCATION", "us-central1")
    # Default to Gemini 2.0 Flash (Stable on Vertex) but can be overridden
    GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-3-flash-preview")
    
    # AI Studio (API Key) - Required for Gemini 3 Preview if not on allowlist
    GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")

    # Slack
    SLACK_BOT_TOKEN = os.getenv("SLACK_BOT_TOKEN")
    SLACK_APP_TOKEN = os.getenv("SLACK_APP_TOKEN")
    SLACK_SIGNING_SECRET = os.getenv("SLACK_SIGNING_SECRET")

    # Git / Journal
    GITHUB_PAT = os.getenv("GITHUB_PAT")
    # Default to the current repo if not specified, but for cloud we need a URL
    JOURNAL_REPO_URL = os.getenv("JOURNAL_REPO_URL")

    # Paths
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    DOCS_DIR = os.path.join(BASE_DIR, "docs")
    CONTEXT_FILE = os.path.join(DOCS_DIR, "OPTIMIND_CONTEXT.md")

config = Config()
