import logging
import datetime
from fastapi import FastAPI, Request
from src.config import config
from src.services.slack import handler as slack_handler
from src.core.memory.journal import journal_manager

# Initialize Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("OptiMind.Main")

app = FastAPI(title="OptiMind 2.0 (Cognitive Agent)", version="2.0.0")

@app.on_event("startup")
async def startup_event():
    """Initialize resources on startup."""
    logger.info(f"OptiMind 2.0 Starting up in {config.ENV} mode...")
    # Initialize Repo (Git Sync)
    journal_manager.initialize_repo()

@app.get("/")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "active",
        "version": "2.0.0",
        "mode": config.ENV,
        "time": datetime.datetime.now().isoformat()
    }

@app.post("/slack/events")
async def slack_events(request: Request):
    """
    Main webhook for Slack Events API.
    Delegates fully to the Slack Service handler.
    """
    # Deduplication: Ignore Slack Retries
    if "x-slack-retry-num" in request.headers:
        retry_num = request.headers["x-slack-retry-num"]
        retry_reason = request.headers.get("x-slack-retry-reason", "unknown")
        logger.warning(f"Ignoring Slack Retry #{retry_num} (Reason: {retry_reason})")
        return {"status": "ok", "message": "Ignored retry"}

    # Simply pass the request to Bolt's AsyncHandler
    return await slack_handler.handle(request)
