"""
Server — FastAPI + Slack-Bolt integration.

Preserved from v1: webhook endpoint, dedup logic, retry-ignore headers, health check.
Changed: calls Agent SDK instead of LangChain. Session management per Slack user.
"""

import logging
import datetime
import asyncio

from fastapi import FastAPI, Request
from slack_bolt.async_app import AsyncApp
from slack_bolt.adapter.fastapi.async_handler import AsyncSlackRequestHandler

# Bootstrap the journal checkout before config validation: in production Config()
# requires OPTIMIND_JOURNAL_PATH, which ensure_journal() resolves (cloning the
# journal repo if needed) and sets in os.environ. See src/bootstrap.py.
from src.bootstrap import ensure_journal

ensure_journal()

from src.config import config
from src.agent import run_agent

# Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("OptiMind.Server")

# FastAPI
app = FastAPI(title="OptiMind SDK", version="3.0.0")

# Slack-Bolt
slack_app = AsyncApp(
    token=config.SLACK_BOT_TOKEN,
    signing_secret=config.SLACK_SIGNING_SECRET,
)
slack_handler = AsyncSlackRequestHandler(slack_app)

# Session store: user_id -> session_id (MVP: in-memory dict)
user_sessions: dict[str, str] = {}

# Deduplication cache: event_id -> timestamp
processed_events: dict[str, datetime.datetime] = {}


async def process_and_reply(user_id: str, channel_id: str, user_text: str):
    """Background task: run agent, reply via Slack."""
    try:
        session_id = user_sessions.get(user_id)
        response_text, new_session_id = await run_agent(user_text, session_id)

        # Persist session for continuity
        user_sessions[user_id] = new_session_id

        if response_text:
            await slack_app.client.chat_postMessage(
                channel=channel_id,
                text=response_text,
            )
        else:
            logger.error("Empty response from agent.")

    except Exception as e:
        logger.error(f"Error processing message: {e}", exc_info=True)
        await slack_app.client.chat_postMessage(
            channel=channel_id,
            text=f":warning: OptiMind Error: {str(e)}",
        )


@slack_app.event("message")
async def handle_message_events(body, logger):
    """Preserved from v1: filter bots, dedup, spawn background task."""
    event = body.get("event", {})
    user_id = event.get("user")
    text = event.get("text")
    channel_id = event.get("channel")

    # Ignore bot messages
    if event.get("bot_id"):
        return

    # Deduplication
    unique_id = body.get("event_id")
    if unique_id in processed_events:
        return
    processed_events[unique_id] = datetime.datetime.now()

    # Cleanup (prevent memory leak)
    if len(processed_events) > 1000:
        cutoff = datetime.datetime.now() - datetime.timedelta(minutes=15)
        for k in list(processed_events.keys()):
            if processed_events[k] < cutoff:
                del processed_events[k]

    asyncio.create_task(process_and_reply(user_id, channel_id, text))


@app.get("/")
async def health_check():
    return {
        "status": "active",
        "version": "3.0.0",
        "mode": config.ENV,
        "active_sessions": len(user_sessions),
        "time": datetime.datetime.now().isoformat(),
    }


@app.post("/slack/events")
async def slack_events(request: Request):
    """Preserved: ignore Slack retries, delegate to Bolt handler."""
    if "x-slack-retry-num" in request.headers:
        retry_num = request.headers["x-slack-retry-num"]
        logger.warning(f"Ignoring Slack Retry #{retry_num}")
        return {"status": "ok", "message": "Ignored retry"}
    return await slack_handler.handle(request)
