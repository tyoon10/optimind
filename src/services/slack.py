import logging
import datetime
import asyncio
from slack_bolt.async_app import AsyncApp
from slack_bolt.adapter.fastapi.async_handler import AsyncSlackRequestHandler
from src.config import config
from src.core.agent import optimind
from src.core.memory.journal import journal_manager

# Initialize Logging
logger = logging.getLogger("OptiMind.Slack")

# Initialize Bolt App
slack_app = AsyncApp(
    token=config.SLACK_BOT_TOKEN,
    signing_secret=config.SLACK_SIGNING_SECRET
)
handler = AsyncSlackRequestHandler(slack_app)

# Global Event Cache for Deduplication
processed_events = {}

async def process_and_reply(user_id: str, channel_id: str, user_text: str):
    """
    Background task:
    1. Calls OptiMind Agent (Core Brain).
    2. Sends response to Slack.
    """
    try:
        # Run the Single Agent Core
        # Note: journal logging for User/Agent happens inside optimind.run()
        response_text = await optimind.run(user_text, user_id=user_id)
        
        # Send result back (instant to user)
        if response_text:
            await slack_app.client.chat_postMessage(
                channel=channel_id,
                text=response_text
            )
        else:
            logger.error("Empty response from OptiMind Agent.")

        # Sync journal AFTER Slack response is sent (no user-facing latency).
        # Awaited here so it completes before this task ends — prevents
        # orphaned background tasks that get killed on Cloud Run.
        try:
            await asyncio.to_thread(journal_manager.sync, push=True)
        except Exception as sync_err:
            logger.error(f"Journal sync failed: {sync_err}", exc_info=True)

    except Exception as e:
        logger.error(f"Error processing message: {e}", exc_info=True)
        await slack_app.client.chat_postMessage(
            channel=channel_id,
            text=f":warning: OptiMind Cogntive Error: {str(e)}"
        )

@slack_app.event("message")
async def handle_message_events(body, logger):
    """
    Main Event Listener.
    Filters bots, handles deduplication, and spawns background processing.
    """
    event = body.get("event", {})
    user_id = event.get("user")
    text = event.get("text")
    channel_id = event.get("channel")
    
    # Ignore bot messages
    if event.get("bot_id"):
        return

    # Deduplication Logic
    unique_id = body.get("event_id")
    if unique_id in processed_events:
        logger.info(f"Duplicate event {unique_id} ignored.")
        return
        
    processed_events[unique_id] = datetime.datetime.now()
    
    # Simple Cleanup (Prevent memory leak)
    if len(processed_events) > 1000:
        cutoff = datetime.datetime.now() - datetime.timedelta(minutes=15)
        # Iterate copy to modify dict safely
        for k in list(processed_events.keys()):
            if processed_events[k] < cutoff:
                del processed_events[k]

    # Fire-and-forget background task
    # In FastAPI integration, this task runs on the event loop
    asyncio.create_task(process_and_reply(user_id, channel_id, text))
