"""
Daily-log tools — the structured per-day record (`daily/YYYY-MM-DD.json`) with a
mandatory dual-write to the markdown journal.

Contract (USER_FLOW_PLAN §7.5): every `log_field` write updates BOTH
  - `daily/<date>.json`  — authoritative structured record (schemas/daily_log.schema.json)
  - `journal/<date>.md`  — a `### HH:MM | Dashboard` mirror line, `[<field>] <value>`
so dashboard inputs reach the reflection / long-term-memory pipeline, which reads
the journal. The journal alone must be sufficient to reconstruct what was logged.

Paths resolve only via `src.config.journal_root()` (§10.7), never hard-coded.
"""

import datetime
import json
import os
from typing import Any, Optional

import pytz

try:
    from claude_agent_sdk import tool
except ImportError:  # let the dual-write logic be unit-tested without the agent runtime installed
    def tool(name, description, input_schema):
        def _decorator(fn):
            fn.tool_meta = {"name": name, "description": description, "input_schema": input_schema}
            return fn
        return _decorator

from src.paths import journal_root

TZ_NAME = os.environ.get("OPTIMIND_TIMEZONE", "America/New_York")  # locale-configurable; default preserves prior behavior
TZ = pytz.timezone(TZ_NAME)
SCHEMA_VERSION = "1.0"

# Event categories stored as lists under log.* (append, not set).
LIST_KEYS = {"meals", "caffeine", "snacks", "workouts"}
# Canonical singular keywords (journal_entry.schema.md) -> the JSON array key.
LIST_ALIASES = {"meal": "meals", "snack": "snacks", "workout": "workouts"}


# --- path helpers (resolved per call so runtime env changes are picked up) ---

def _daily_dir() -> str:
    return os.path.join(journal_root(), "daily")


def _journal_dir() -> str:
    return os.path.join(journal_root(), "journal")


def _daily_path(date: str) -> str:
    return os.path.join(_daily_dir(), f"{date}.json")


def _journal_path(date: str) -> str:
    return os.path.join(_journal_dir(), f"{date}.md")


def _today_str() -> str:
    return datetime.datetime.now(TZ).date().isoformat()


def _now_hhmm() -> str:
    return datetime.datetime.now(TZ).strftime("%H:%M")


# --- daily.json read/write ---

def _new_doc(date: str) -> dict:
    return {"schema_version": SCHEMA_VERSION, "date": date, "tz": TZ_NAME}


def load_daily(date: str) -> dict:
    path = _daily_path(date)
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return _new_doc(date)


def save_daily(date: str, doc: dict) -> str:
    os.makedirs(_daily_dir(), exist_ok=True)
    path = _daily_path(date)
    tmp = f"{path}.tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(doc, f, indent=2, ensure_ascii=False)
        f.write("\n")
    os.replace(tmp, path)  # atomic on POSIX
    return path


# --- field routing + rendering ---

def _list_key(field: str) -> Optional[str]:
    """Return the JSON array key if `field` names an event category, else None."""
    head = (field[4:] if field.startswith("log.") else field).split(".")[0]
    head = LIST_ALIASES.get(head, head)
    return head if head in LIST_KEYS else None


def _set_path(obj: dict, parts: list, value: Any) -> None:
    cur = obj
    for p in parts[:-1]:
        nxt = cur.get(p)
        if not isinstance(nxt, dict):
            nxt = {}
            cur[p] = nxt
        cur = nxt
    cur[parts[-1]] = value


def render_value(value: Any) -> str:
    """Human, greppable rendering for the journal mirror line."""
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, dict):
        return " ".join(render_value(v) for v in value.values())
    if isinstance(value, list):
        return " ".join(render_value(v) for v in value)
    return str(value)


def apply_field(doc: dict, field: str, value: Any, time: str) -> Any:
    """
    Mutate doc['log'] for `field`. Event categories (meals/caffeine/snacks/workouts,
    or their singular aliases) append an entry; everything else is a dotted-path set.
    Returns the value as stored, so the mirror line reflects the JSON exactly.
    """
    f = field[4:] if field.startswith("log.") else field
    log = doc.setdefault("log", {})
    lk = _list_key(field)
    if lk:
        entry = dict(value) if isinstance(value, dict) else {"value": value}
        if time and "time" not in entry:
            entry = {"time": time, **entry}
        log.setdefault(lk, []).append(entry)
        return entry
    _set_path(log, f.split("."), value)
    return value


def append_dashboard_line(date: str, time: str, field: str, rendered: str) -> str:
    os.makedirs(_journal_dir(), exist_ok=True)
    path = _journal_path(date)
    with open(path, "a", encoding="utf-8") as f:
        f.write(f"\n### {time} | Dashboard\n[{field}] {rendered}\n")
    return path


# --- operations (shared by the MCP tools and the unit tests) ---

def do_log_field(field: str, value: Any, time: Optional[str] = None,
                 date: Optional[str] = None) -> dict:
    """The dual-write. Updates daily/<date>.json AND appends a Dashboard mirror line."""
    date = date or _today_str()
    time = time or _now_hhmm()
    doc = load_daily(date)
    written = apply_field(doc, field, value, time)
    daily_p = save_daily(date, doc)
    journal_p = append_dashboard_line(date, time, field, render_value(written))
    return {"date": date, "time": time, "field": field,
            "daily_path": daily_p, "journal_path": journal_p}


def do_get_daily(date: Optional[str] = None) -> dict:
    return load_daily(date or _today_str())


def do_set_protocol(items: list, source: str = "default",
                    date: Optional[str] = None, generated_at: Optional[str] = None) -> dict:
    date = date or _today_str()
    doc = load_daily(date)
    doc["protocol"] = {
        "generated_at": generated_at or datetime.datetime.now(TZ).isoformat(timespec="seconds"),
        "source": source,
        "items": items,
    }
    save_daily(date, doc)
    return doc


# --- pure text handlers (shared by the @tool wrappers and the standalone MCP server) ---

def get_daily_text(args: dict[str, Any]) -> str:
    doc = do_get_daily(args.get("date") or None)
    return json.dumps(doc, indent=2, ensure_ascii=False)


def log_field_text(args: dict[str, Any]) -> str:
    res = do_log_field(args["field"], args["value"], args.get("time") or None)
    return f"Logged [{res['field']}] at {res['time']} → {res['daily_path']} + journal mirror."


def set_protocol_text(args: dict[str, Any]) -> str:
    doc = do_set_protocol(args["items"], args.get("source") or "default")
    p = doc["protocol"]
    return f"Protocol set for {doc['date']}: {len(p['items'])} item(s), source={p['source']}."


# --- MCP tool wrappers ---

@tool(
    "get_daily",
    "Read the structured daily log (protocol + sleep/meals/caffeine/snacks/routine/workouts) "
    "for today, or a given YYYY-MM-DD date. Use when the user asks what they've logged today, "
    "or you need exact numeric values rather than the prose journal.",
    {"date": str},
)
async def get_daily(args: dict[str, Any]) -> dict[str, Any]:
    return {"content": [{"type": "text", "text": get_daily_text(args)}]}


@tool(
    "log_field",
    "Log ONE structured field to today's daily log AND mirror it to the journal (dual-write). "
    "`field` is a dotted path under the daily 'log' object: scalars like 'sleep.wake_time', "
    "'sleep.bedtime', 'sleep.quality'; routine items like 'routine.cold_shower'; or event "
    "categories 'caffeine', 'meal', 'snack', 'workout'. "
    "For event categories ALWAYS pass `value` as a structured object matching daily_log.schema.json "
    "— never a bare string: caffeine -> {\"amount_mg\": <int>, \"source\": <str>}; "
    "meal/snack -> {\"items\": <str>}; workout -> {\"duration_min\": <int>, \"type\": <str>}. "
    "If the user doesn't give the number, ESTIMATE it from the source (brewed coffee ~95mg/cup, "
    "espresso ~65mg/shot, cold brew ~205mg/16oz, black tea ~47mg, energy drink ~80mg) and keep the "
    "drink/food description in `source`. For scalar fields pass the value directly. `time` is "
    "optional HH:MM (defaults to now, NYC). Use canonical keywords from journal_entry.schema.md.",
    {
        "type": "object",
        "properties": {
            "field": {"type": "string"},
            "value": {},
            "time": {"type": "string"},
        },
        "required": ["field", "value"],
    },
)
async def log_field(args: dict[str, Any]) -> dict[str, Any]:
    return {"content": [{"type": "text", "text": log_field_text(args)}]}


@tool(
    "set_protocol",
    "Write today's protocol (the plan for the day) into the daily log. `items` is a list of "
    "{id, expected_window?, duration_min?, type?}. Used mainly by the morning-brief routine. "
    "`source` is one of default | mobile_override | rule_derived.",
    {
        "type": "object",
        "properties": {
            "items": {"type": "array", "items": {"type": "object"}},
            "source": {"type": "string", "enum": ["default", "mobile_override", "rule_derived"]},
        },
        "required": ["items"],
    },
)
async def set_protocol(args: dict[str, Any]) -> dict[str, Any]:
    return {"content": [{"type": "text", "text": set_protocol_text(args)}]}


daily_tools = [get_daily, log_field, set_protocol]
