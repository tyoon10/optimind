"""
State tools — read and write the active state (mode, constraints, focus).

Storage: data/state.json
Preserved from v1: JSON schema, mode enum, constraint list.
Changed: agent can now WRITE state (switch modes, add constraints), not just read.
"""

import json
import os
from datetime import datetime
from typing import Any

from claude_agent_sdk import tool

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
STATE_PATH = os.path.join(BASE_DIR, "data", "state.json")

DEFAULT_STATE = {
    "system_mode": "STANDARD",
    "active_constraints": [],
    "current_focus": {"title": "None", "deadline": None},
    "last_updated": None,
}

VALID_MODES = {"STANDARD", "EXAM_MODE", "DEEP_WORK", "RECOVERY"}


def _read_state() -> dict:
    if not os.path.exists(STATE_PATH):
        return DEFAULT_STATE.copy()
    try:
        with open(STATE_PATH, "r") as f:
            return json.load(f)
    except (json.JSONDecodeError, FileNotFoundError):
        return DEFAULT_STATE.copy()


def _write_state(state: dict):
    state["last_updated"] = datetime.now().isoformat()
    os.makedirs(os.path.dirname(STATE_PATH), exist_ok=True)
    with open(STATE_PATH, "w") as f:
        json.dump(state, f, indent=2)


@tool(
    "get_state",
    "Get the current active state: system mode, constraints, and focus. "
    "Use this when the user's query depends on their current mode or active constraints.",
    {},
)
async def get_state(args: dict[str, Any]) -> dict[str, Any]:
    state = _read_state()
    text = (
        f"System Mode: {state['system_mode']}\n"
        f"Active Constraints: {', '.join(state['active_constraints']) or 'None'}\n"
        f"Current Focus: {state['current_focus'].get('title', 'None')}\n"
        f"Focus Deadline: {state['current_focus'].get('deadline', 'None')}\n"
        f"Last Updated: {state.get('last_updated', 'Never')}"
    )
    return {"content": [{"type": "text", "text": text}]}


@tool(
    "set_state",
    "Update the active state. Can change mode (STANDARD, EXAM_MODE, DEEP_WORK, RECOVERY), "
    "set constraints, and set the current focus. Only include fields you want to change.",
    {
        "type": "object",
        "properties": {
            "mode": {"type": "string", "enum": list(VALID_MODES)},
            "constraints": {
                "type": "array",
                "items": {"type": "string"},
            },
            "focus_title": {"type": "string"},
            "focus_deadline": {"type": "string"},
        },
    },
)
async def set_state(args: dict[str, Any]) -> dict[str, Any]:
    state = _read_state()
    changes = []

    if "mode" in args:
        mode = args["mode"]
        if mode not in VALID_MODES:
            return {"content": [{"type": "text", "text": f"Invalid mode: {mode}. Valid: {VALID_MODES}"}]}
        state["system_mode"] = mode
        changes.append(f"Mode → {mode}")

    if "constraints" in args:
        state["active_constraints"] = args["constraints"]
        changes.append(f"Constraints → {args['constraints']}")

    if "focus_title" in args:
        state["current_focus"]["title"] = args["focus_title"]
        changes.append(f"Focus → {args['focus_title']}")

    if "focus_deadline" in args:
        state["current_focus"]["deadline"] = args["focus_deadline"]
        changes.append(f"Deadline → {args['focus_deadline']}")

    _write_state(state)
    text = "State updated: " + "; ".join(changes)
    return {"content": [{"type": "text", "text": text}]}


state_tools = [get_state, set_state]
