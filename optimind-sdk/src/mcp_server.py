"""
Standalone stdio MCP server — exposes the optimind tools to the `claude` CLI via
the project-root `.mcp.json`.

The in-process `create_sdk_mcp_server` in `agent.py` CANNOT be reused here: SDK
in-process servers aren't exposable to the CLI (confirmed against the docs —
decisions log 2026-05-28). So this server reuses the *pure handler functions*
from the tool modules and wraps them in the `mcp` (modelcontextprotocol) stdio
transport — one shared core, two transports.

Importing this module requires neither the `mcp` package nor API keys: the `mcp`
import is deferred into `run()`, and the tool modules resolve paths via
`src.paths` (not `Config()`), so a fresh `claude` clone can launch the server
without Slack/Anthropic credentials. The journal path arrives via `.mcp.json`'s
`env` block.
"""

from typing import Any, Callable

from src.tools import journal as _journal
from src.tools import state as _state
from src.tools import preferences as _prefs
from src.tools import daily as _daily

# name -> (description, json-schema, handler(args) -> str)
TOOLS: dict[str, tuple[str, dict, Callable[[dict[str, Any]], str]]] = {
    "get_recent_journal": (
        "Read the last N days of journal entries (chronological log text).",
        {"type": "object", "properties": {"days": {"type": "integer"}}},
        _journal.get_recent_journal_text,
    ),
    "search_journal": (
        "Search journal entries for a keyword within the last N days.",
        {"type": "object",
         "properties": {"query": {"type": "string"}, "days": {"type": "integer"}},
         "required": ["query"]},
        _journal.search_journal_text,
    ),
    "log_entry": (
        "Append an entry to today's journal.",
        {"type": "object",
         "properties": {"role": {"type": "string"}, "content": {"type": "string"}},
         "required": ["role", "content"]},
        _journal.log_entry_text,
    ),
    "get_state": (
        "Get the current active state: system mode, constraints, and focus.",
        {"type": "object", "properties": {}},
        _state.get_state_text,
    ),
    "set_state": (
        "Update the active state (mode/constraints/focus). Only include fields to change.",
        {"type": "object",
         "properties": {"mode": {"type": "string"},
                        "constraints": {"type": "array", "items": {"type": "string"}},
                        "focus_title": {"type": "string"},
                        "focus_deadline": {"type": "string"}}},
        _state.set_state_text,
    ),
    "get_rules": (
        "Get user preference rules, optionally filtered by topic.",
        {"type": "object", "properties": {"topic": {"type": "string"}}},
        _prefs.get_rules_text,
    ),
    "add_rule": (
        "Add a preference rule learned from conversation.",
        {"type": "object",
         "properties": {"topic": {"type": "string"}, "rule": {"type": "string"},
                        "confidence": {"type": "number"}},
         "required": ["topic", "rule"]},
        _prefs.add_rule_text,
    ),
    "delete_rule": (
        "Delete a preference rule by topic + fuzzy (case-insensitive substring) content match.",
        {"type": "object",
         "properties": {"topic": {"type": "string"}, "content": {"type": "string"}},
         "required": ["topic", "content"]},
        _prefs.delete_rule_text,
    ),
    "get_daily": (
        "Read the structured daily log (protocol + log) for today or a given YYYY-MM-DD date.",
        {"type": "object", "properties": {"date": {"type": "string"}}},
        _daily.get_daily_text,
    ),
    "log_field": (
        "Log one structured field to the daily log AND mirror it to the journal (dual-write). "
        "field is a dotted path (e.g. 'sleep.wake_time', 'caffeine', 'routine.cold_shower').",
        {"type": "object",
         "properties": {"field": {"type": "string"}, "value": {}, "time": {"type": "string"}},
         "required": ["field", "value"]},
        _daily.log_field_text,
    ),
    "set_protocol": (
        "Write today's protocol (the plan for the day) into the daily log.",
        {"type": "object",
         "properties": {"items": {"type": "array", "items": {"type": "object"}},
                        "source": {"type": "string"}},
         "required": ["items"]},
        _daily.set_protocol_text,
    ),
}


def dispatch(name: str, args: dict[str, Any]) -> str:
    """Pure dispatch to a tool's handler. Raises ValueError on an unknown tool."""
    if name not in TOOLS:
        raise ValueError(f"Unknown tool: {name}")
    return TOOLS[name][2](args or {})


def run() -> None:
    """Start the stdio MCP server. Defers the `mcp` import so module import stays light."""
    import asyncio

    from mcp.server import Server
    from mcp.server.stdio import stdio_server
    from mcp.types import TextContent, Tool

    app = Server("optimind")

    @app.list_tools()
    async def _list_tools():
        return [Tool(name=n, description=desc, inputSchema=schema)
                for n, (desc, schema, _handler) in TOOLS.items()]

    @app.call_tool()
    async def _call_tool(name: str, arguments: dict):
        return [TextContent(type="text", text=dispatch(name, arguments))]

    async def _main():
        async with stdio_server() as (read_stream, write_stream):
            await app.run(read_stream, write_stream, app.create_initialization_options())

    asyncio.run(_main())
