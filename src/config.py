import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

class Config:
    """Centralized configuration for OptiMind."""
    
    def __init__(self):
        # Environment
        self.ENV = os.getenv("OPTIMIND_ENV", "development")
        self.IS_DEV = self.ENV == "development"
        
        # Google / Vertex AI
        self.GOOGLE_PROJECT_ID = os.getenv("GOOGLE_PROJECT_ID")
        self.GOOGLE_LOCATION = os.getenv("GOOGLE_LOCATION", "us-central1")
        # Default to Gemini 3.0 Flash (Stable on Vertex) but can be overridden
        self.GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-3-flash-preview")
        self.GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")

        # Slack
        self.SLACK_BOT_TOKEN = os.getenv("SLACK_BOT_TOKEN")
        self.SLACK_APP_TOKEN = os.getenv("SLACK_APP_TOKEN")
        self.SLACK_SIGNING_SECRET = os.getenv("SLACK_SIGNING_SECRET")

        # Git / Journal
        self.GITHUB_PAT = os.getenv("GITHUB_PAT")
        self.JOURNAL_REPO_URL = os.getenv("JOURNAL_REPO_URL")

        # Paths
        self.BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.DOCS_DIR = os.path.join(self.BASE_DIR, "docs")
        self.DATA_DIR = os.path.join(self.BASE_DIR, "data")
        
        # Validation
        self._validate()

    def _validate(self):
        """Ensure critical environment variables are present."""
        errors = []
        if not self.SLACK_BOT_TOKEN:
            errors.append("Missing SLACK_BOT_TOKEN")
        if not self.SLACK_SIGNING_SECRET:
            errors.append("Missing SLACK_SIGNING_SECRET")
            
        # We need EITHER Vertex Project OR Google API Key
        if not self.GOOGLE_PROJECT_ID and not self.GOOGLE_API_KEY:
            errors.append("Missing both GOOGLE_PROJECT_ID and GOOGLE_API_KEY. Need at least one.")

        if errors:
            raise EnvironmentError(f"Configuration Errors: {', '.join(errors)}")

config = Config()
