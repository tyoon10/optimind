"""
Journal tools — read, search, and log entries in the flat-file markdown journal.

Storage: data/journal/YYYY-MM-DD.md (one file per day, EST timezone)
Preserved from v1: file format, deduplication, EST date handling.
Changed: exposed as Agent SDK custom tools instead of prompt-injected context.
"""

import os
import datetime
import re
from typing import Any

import pytz

try:
    from claude_agent_sdk import tool
except ImportError:  # let the pure handlers be imported/tested without the agent runtime
    def tool(name, description, input_schema):
        def _decorator(fn):
            fn.tool_meta = {"name": name, "description": description, "input_schema": input_schema}
            return fn
        return _decorator

from src.paths import journal_root

TZ = pytz.timezone("America/New_York")  # canonical id; "US/Eastern" is a deprecated alias absent from minimal pytz builds


def _journal_dir() -> str:
    """Resolved per-call so tests / runtime env changes are picked up."""
    return os.path.join(journal_root(), "journal")


def _today() -> datetime.date:
    return datetime.datetime.now(TZ).date()


def _daily_path(date: datetime.date) -> str:
    return os.path.join(_journal_dir(), f"{date.isoformat()}.md")


# --- pure handlers (shared by the @tool wrappers and the standalone MCP server) ---

def get_recent_journal_text(args: dict[str, Any]) -> str:
    days = min(args.get("days", 7), 30)  # cap at 30
    today = _today()
    parts = []

    for i in range(days):
        date = today - datetime.timedelta(days=i)
        path = _daily_path(date)
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                content = f.read()
            parts.append(f"\n=== JOURNAL: {date.isoformat()} ===\n{content}")

    parts.reverse()  # oldest first
    return "".join(parts) if parts else "No journal entries found for the requested period."


def search_journal_text(args: dict[str, Any]) -> str:
    query = args["query"]
    days = min(args.get("days", 14), 30)
    today = _today()
    matches = []

    pattern = re.compile(re.escape(query), re.IGNORECASE)

    for i in range(days):
        date = today - datetime.timedelta(days=i)
        path = _daily_path(date)
        if not os.path.exists(path):
            continue

        with open(path, "r", encoding="utf-8") as f:
            lines = f.readlines()

        for line_num, line in enumerate(lines, 1):
            if pattern.search(line):
                matches.append(f"[{date.isoformat()} L{line_num}] {line.rstrip()}")

    if not matches:
        return f"No matches for '{query}' in the last {days} days."
    return f"Found {len(matches)} match(es) for '{query}':\n" + "\n".join(matches)


def log_entry_text(args: dict[str, Any]) -> str:
    role = args["role"]
    content = args["content"]
    filepath = _daily_path(_today())
    timestamp = datetime.datetime.now(TZ).strftime("%H:%M")
    entry = f"\n### {timestamp} | {role}\n{content}\n"

    os.makedirs(_journal_dir(), exist_ok=True)

    # Deduplication: skip if content already appears near end of file
    if os.path.exists(filepath):
        with open(filepath, "r", encoding="utf-8") as f:
            existing = f.read()
        if content.strip() in existing[-len(content) * 2 :]:
            return "Entry already logged (duplicate skipped)."

    with open(filepath, "a", encoding="utf-8") as f:
        f.write(entry)

    return f"Logged to {filepath}"


# --- MCP tool wrappers ---

@tool(
    "get_recent_journal",
    "Read the last N days of journal entries. Returns chronological log text. "
    "Use this when the user's query requires recent context (meals, workouts, sleep, mood).",
    {"days": int},
)
async def get_recent_journal(args: dict[str, Any]) -> dict[str, Any]:
    return {"content": [{"type": "text", "text": get_recent_journal_text(args)}]}


@tool(
    "search_journal",
    "Search journal entries for a keyword or pattern within the last N days. "
    "Use this for targeted lookups (e.g., 'caffeine', 'workout', 'sleep score').",
    {"query": str, "days": int},
)
async def search_journal(args: dict[str, Any]) -> dict[str, Any]:
    return {"content": [{"type": "text", "text": search_journal_text(args)}]}


@tool(
    "log_entry",
    "Append an entry to today's journal. Use this to log interactions, observations, or notes.",
    {"role": str, "content": str},
)
async def log_entry(args: dict[str, Any]) -> dict[str, Any]:
    return {"content": [{"type": "text", "text": log_entry_text(args)}]}


# All journal tools for registration
journal_tools = [get_recent_journal, search_journal, log_entry]
