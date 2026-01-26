from fastapi import FastAPI, Request, BackgroundTasks
from slack_bolt.async_app import AsyncApp
from slack_bolt.adapter.fastapi.async_handler import AsyncSlackRequestHandler
from src.config import config
from src.graph.builder import graph
from src.config import config
from langchain_core.messages import HumanMessage
import logging
import json
import asyncio
import datetime
# from langchain_core.prompts import ChatPromptTemplate
# from langchain_core.messages import SystemMessage
# from src.memory.store import memory_store
# from src.memory.schemas import PreferenceRule
# from src.agents.base import BaseAgent
# from pydantic import BaseModel
# from typing import List
import logging
import json

# Initialize Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("OptiMind")

# Global Event Cache for Deduplication
processed_events = {}

# Initialize FastAPI
app = FastAPI(title="OptiMind Assistant", version="0.1.0")

# Initialize Slack Bolt App
slack_app = AsyncApp(
    token=config.SLACK_BOT_TOKEN,
    signing_secret=config.SLACK_SIGNING_SECRET
)
handler = AsyncSlackRequestHandler(slack_app)

@app.get("/")
async def health_check():
    """Health check endpoint."""
    return {"status": "ok", "bot_running": True}

@app.post("/slack/events")
async def slack_events(request: Request):
    """
    Main webhook for Slack Events API.
    Bolt handler manages url_verification and event dispatch.
    """
    body = await request.body()
    logger.info(f"DEBUG: Webhook Received at {datetime.datetime.now()}: {body[:200]}")
    return await handler.handle(request)

async def process_agent_response(user_id: str, channel_id: str, user_text: str):
    """
    Runs the LangGraph agent in the background and sends the response back to Slack.
    """
    logger.info(f"Processing message from {user_id}: {user_text}")
    
    # input state
    initial_state = {
        "messages": [HumanMessage(content=user_text)],
        "user_id": user_id,
        "user_profile": {} # In future, load full profile here if needed before graph
    }
    
    # 1. Log the User's Input IMMEDIATELY to prevent data loss on crash
    from src.memory.journal import journal_manager
    # We log it as "User" even before we know if the bot will reply successfully.
    # This also helps debug if the bot crashes.
    try:
        journal_manager.log_interaction("User", user_text)
    except Exception as log_err:
        logger.error(f"Failed to log interaction: {log_err}")

    # Run the graph with Manual Retry for 503s
    max_retries = 3
    retry_count = 0
    backoff = 2
    
    while retry_count < max_retries:
        try:
            final_response = ""
            async for output in graph.astream(initial_state):
                 for key, value in output.items():
                    if "messages" in value:
                        # Capture the latest AI message
                        final_response = value["messages"][-1].content
            
            # If we get here, success!
            # Send result back to Slack
            if final_response:
                logger.info(f"DEBUG: Final Response to Slack: {final_response[:100]}...") # Log 1st 100 chars
                await slack_app.client.chat_postMessage(
                    channel=channel_id,
                    text=final_response
                )
            else:
                logger.error("ERROR: Final Response is EMPTY.")
                await slack_app.client.chat_postMessage(
                    channel=channel_id,
                    text=":warning: OptiMind thought about it, but couldn't speak. (Empty Response)"
                )
            return # Exit function on success
            
        except Exception as e:
            error_msg = str(e)
            if "503" in error_msg or "429" in error_msg or "Overloaded" in error_msg:
                retry_count += 1
                if retry_count < max_retries:
                    logger.warning(f"Got 503/429. Retrying {retry_count}/{max_retries} in {backoff}s...")
                    await asyncio.sleep(backoff)
                    backoff *= 2 # Exponential backoff
                    continue # Retry loop
            
            # If not retriable or retries exhausted:
            logger.error(f"CRITICAL ERROR executing graph: {e}", exc_info=True)
            await slack_app.client.chat_postMessage(
                channel=channel_id,
                text=f":warning: OptiMind Brain Error: {str(e)}"
            )
            return # Exit function on failure

# Slack Event Listener
@slack_app.event("message")
async def handle_message_events(body, logger):
    event = body.get("event", {})
    user_id = event.get("user")
    text = event.get("text")
    channel_id = event.get("channel")
    
    # Ignore bot messages
    if event.get("bot_id"):
        return

    # Trigger background processing (we don't want to block the Slack acknowledgement 3s timeout)
    # Note: Bolt's async handler usually handles this, but since we are inside FastAPI, 
    # we call the async function directly. 
    # Ideally, we should use FastAPI's BackgroundTasks, but Bolt's listener signature makes it tricky.
    # For MVP simplicity, we just await it here (LangGraph is fast enough for <3s usually, or we fix architecture later).
    # IMPROVEMENT: Use FastAPI background tasks properly by extracting logic.
    
    # Deduplication Logic
    # Slack sends the same event_id on retry. We must ignore duplicates.
    event_id = event.get("event_ts") # technically event_ts is unique enough per channel, but event_id is better if available at body level.
    # Actually, body['event_id'] is the unique one.
    unique_id = body.get("event_id")
    
    if unique_id in processed_events:
        logger.info(f"DEBUG: duplicate event {unique_id} ignored.")
        return
        
    # Cache event to prevent replays (TTL logic needed in prod, but simple dict for now)
    processed_events[unique_id] = datetime.datetime.now()
    
    # Simple cleanup (keep last 1000 or clean older than 10 mins)
    if len(processed_events) > 1000:
        # Clear out old events > 15 mins
        cutoff = datetime.datetime.now() - datetime.timedelta(minutes=15)
        keys_to_remove = [k for k, v in processed_events.items() if v < cutoff]
        for k in keys_to_remove:
            del processed_events[k]

    # Fire-and-forget background task so we return 200 OK to Slack immediately
    asyncio.create_task(process_agent_response(user_id, channel_id, text))

# Log startup
@app.on_event("startup")
async def startup_event():
    logger.info("OptiMind Assistant Started. Slack Bolt App initialized.")
    from src.memory.journal import journal_manager
    journal_manager.initialize_repo()
