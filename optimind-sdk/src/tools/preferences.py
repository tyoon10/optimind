"""
Preference tools — CRUD for user preference rules.

Storage: data/user_profile.json (Pydantic schema from v1)
Preserved from v1: JSON format, topic/rule/confidence structure, fuzzy delete.
Changed: agent can now add/delete rules mid-conversation (preference learning revived).
"""

import json
import logging
import os
from datetime import datetime
from typing import Any

try:
    from claude_agent_sdk import tool
except ImportError:  # let the pure handlers be imported/tested without the agent runtime
    def tool(name, description, input_schema):
        def _decorator(fn):
            fn.tool_meta = {"name": name, "description": description, "input_schema": input_schema}
            return fn
        return _decorator

from src.paths import journal_root

logger = logging.getLogger(__name__)

SCHEMA_VERSION = "1.0"
DEFAULT_PROFILE = {
    "schema_version": SCHEMA_VERSION,
    "user_id": "1",
    "name": "User",
    "rules": [],
}


def _profile_path() -> str:
    return os.path.join(journal_root(), "user_profile.json")


def _validate_schema_version(profile: dict) -> None:
    """
    Refuse to proceed on schema mismatch (per schemas/optimind_interface.md).
    Migration is explicit — see migrations/user_profile_<from>to<to>.py.
    """
    version = profile.get("schema_version")
    if version is None:
        raise ValueError(
            f"user_profile.json is missing 'schema_version'. Expected '{SCHEMA_VERSION}'. "
            f"This file pre-dates the schema; add schema_version manually or run the migration."
        )
    if version != SCHEMA_VERSION:
        raise ValueError(
            f"user_profile.json schema_version is '{version}', runtime expects '{SCHEMA_VERSION}'. "
            f"Run migrations/user_profile_{version.replace('.', '')}to{SCHEMA_VERSION.replace('.', '')}.py "
            f"to upgrade."
        )


def _load_profile() -> dict:
    path = _profile_path()
    if not os.path.exists(path):
        return DEFAULT_PROFILE.copy()
    try:
        with open(path, "r", encoding="utf-8") as f:
            profile = json.load(f)
    except json.JSONDecodeError as e:
        raise ValueError(f"user_profile.json is corrupted: {e}") from e
    _validate_schema_version(profile)
    return profile


def _save_profile(profile: dict):
    profile.setdefault("schema_version", SCHEMA_VERSION)
    path = _profile_path()
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(profile, f, indent=2, default=str)


# --- pure handlers (shared by the @tool wrappers and the standalone MCP server) ---

def get_rules_text(args: dict[str, Any]) -> str:
    profile = _load_profile()
    rules = profile.get("rules", [])

    topic = args.get("topic")
    if topic:
        rules = [r for r in rules if r.get("topic") == topic]

    if not rules:
        label = f" for topic '{topic}'" if topic else ""
        return f"No preference rules found{label}."

    lines = [f"- [{r['topic']}] {r['rule']} (confidence: {r.get('confidence', 1.0)})" for r in rules]
    return "\n".join(lines)


def add_rule_text(args: dict[str, Any]) -> str:
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
            return f"Rule already exists: [{new_rule['topic']}] {new_rule['rule']}"

    profile.setdefault("rules", []).append(new_rule)
    _save_profile(profile)
    return f"Added rule: [{new_rule['topic']}] {new_rule['rule']}"


def delete_rule_text(args: dict[str, Any]) -> str:
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
        return f"Removed {removed} rule(s) matching [{topic}] '{args['content']}'"

    return f"No rules found matching [{topic}] '{args['content']}'"


# --- MCP tool wrappers ---

@tool(
    "get_rules",
    "Get user preference rules, optionally filtered by topic. "
    "Topics include: nutrition, scheduling, profile, environment. "
    "Use this when the user's query involves a domain with known preferences.",
    {"topic": str},
)
async def get_rules(args: dict[str, Any]) -> dict[str, Any]:
    return {"content": [{"type": "text", "text": get_rules_text(args)}]}


@tool(
    "add_rule",
    "Add a new preference rule learned from conversation. "
    "Use this when the user explicitly or implicitly states a preference, constraint, or habit.",
    {"topic": str, "rule": str, "confidence": float},
)
async def add_rule(args: dict[str, Any]) -> dict[str, Any]:
    return {"content": [{"type": "text", "text": add_rule_text(args)}]}


@tool(
    "delete_rule",
    "Delete a preference rule that is outdated or explicitly revoked by the user. "
    "Matches by topic and fuzzy content match (case-insensitive substring).",
    {"topic": str, "content": str},
)
async def delete_rule(args: dict[str, Any]) -> dict[str, Any]:
    return {"content": [{"type": "text", "text": delete_rule_text(args)}]}


preference_tools = [get_rules, add_rule, delete_rule]
