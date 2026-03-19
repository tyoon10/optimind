"""
Preference tools — CRUD for user preference rules.

Storage: data/user_profile.json (Pydantic schema from v1)
Preserved from v1: JSON format, topic/rule/confidence structure, fuzzy delete.
Changed: agent can now add/delete rules mid-conversation (preference learning revived).
"""

import json
import os
from datetime import datetime
from typing import Any

from claude_agent_sdk import tool

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
PROFILE_PATH = os.path.join(BASE_DIR, "data", "user_profile.json")

DEFAULT_PROFILE = {"user_id": "1", "name": "User", "rules": []}


def _load_profile() -> dict:
    if not os.path.exists(PROFILE_PATH):
        return DEFAULT_PROFILE.copy()
    try:
        with open(PROFILE_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, FileNotFoundError):
        return DEFAULT_PROFILE.copy()


def _save_profile(profile: dict):
    os.makedirs(os.path.dirname(PROFILE_PATH), exist_ok=True)
    with open(PROFILE_PATH, "w", encoding="utf-8") as f:
        json.dump(profile, f, indent=2, default=str)


@tool(
    "get_rules",
    "Get user preference rules, optionally filtered by topic. "
    "Topics include: nutrition, scheduling, profile, environment. "
    "Use this when the user's query involves a domain with known preferences.",
    {"topic": str},
)
async def get_rules(args: dict[str, Any]) -> dict[str, Any]:
    profile = _load_profile()
    rules = profile.get("rules", [])

    topic = args.get("topic")
    if topic:
        rules = [r for r in rules if r.get("topic") == topic]

    if not rules:
        label = f" for topic '{topic}'" if topic else ""
        return {"content": [{"type": "text", "text": f"No preference rules found{label}."}]}

    lines = [f"- [{r['topic']}] {r['rule']} (confidence: {r.get('confidence', 1.0)})" for r in rules]
    return {"content": [{"type": "text", "text": "\n".join(lines)}]}


@tool(
    "add_rule",
    "Add a new preference rule learned from conversation. "
    "Use this when the user explicitly or implicitly states a preference, constraint, or habit.",
    {"topic": str, "rule": str, "confidence": float},
)
async def add_rule(args: dict[str, Any]) -> dict[str, Any]:
    profile = _load_profile()
    new_rule = {
        "topic": args["topic"],
        "rule": args["rule"],
        "source": "agent_learned",
        "created_at": datetime.now().isoformat(),
        "confidence": args.get("confidence", 0.8),
    }

    # Avoid exact duplicates
    for existing in profile.get("rules", []):
        if existing["topic"] == new_rule["topic"] and existing["rule"].lower() == new_rule["rule"].lower():
            return {"content": [{"type": "text", "text": f"Rule already exists: [{new_rule['topic']}] {new_rule['rule']}"}]}

    profile.setdefault("rules", []).append(new_rule)
    _save_profile(profile)
    return {"content": [{"type": "text", "text": f"Added rule: [{new_rule['topic']}] {new_rule['rule']}"}]}


@tool(
    "delete_rule",
    "Delete a preference rule that is outdated or explicitly revoked by the user. "
    "Matches by topic and fuzzy content match (case-insensitive substring).",
    {"topic": str, "content": str},
)
async def delete_rule(args: dict[str, Any]) -> dict[str, Any]:
    profile = _load_profile()
    topic = args["topic"]
    content = args["content"].lower()

    initial_count = len(profile.get("rules", []))
    profile["rules"] = [
        r for r in profile.get("rules", [])
        if not (r.get("topic") == topic and content in r.get("rule", "").lower())
    ]

    removed = initial_count - len(profile["rules"])
    if removed > 0:
        _save_profile(profile)
        return {"content": [{"type": "text", "text": f"Removed {removed} rule(s) matching [{topic}] '{args['content']}'"}]}

    return {"content": [{"type": "text", "text": f"No rules found matching [{topic}] '{args['content']}'"}]}


preference_tools = [get_rules, add_rule, delete_rule]
