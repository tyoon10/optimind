"""
Tests for the standalone MCP server registry/dispatch (Task 4) and the pure
handlers the refactor extracted. The `mcp` package is only needed by run() (the
stdio transport), which is deferred — so importing src.mcp_server and exercising
dispatch() works without it. This verifies the refactor didn't break tool logic
and that the standalone server reaches the same handlers as the SDK wrappers.
"""

import json

import pytest

from src import mcp_server

EXPECTED_TOOLS = {
    "get_recent_journal", "search_journal", "log_entry",
    "get_state", "set_state",
    "get_rules", "add_rule", "delete_rule",
    "get_daily", "log_field", "set_protocol",
}


@pytest.fixture()
def journal(tmp_path, monkeypatch):
    monkeypatch.setenv("OPTIMIND_JOURNAL_PATH", str(tmp_path))
    return tmp_path


def test_registry_covers_all_11_tools():
    assert set(mcp_server.TOOLS) == EXPECTED_TOOLS
    for name, (desc, schema, handler) in mcp_server.TOOLS.items():
        assert desc and isinstance(schema, dict) and callable(handler)


def test_dispatch_unknown_tool_raises():
    with pytest.raises(ValueError):
        mcp_server.dispatch("nope", {})


def test_dispatch_log_field_dual_write(journal):
    out = mcp_server.dispatch("log_field",
                              {"field": "caffeine",
                               "value": {"amount_mg": 95, "source": "espresso"},
                               "time": "08:14"})
    assert "caffeine" in out
    daily_dir = journal / "daily"
    journal_dir = journal / "journal"
    assert daily_dir.exists() and journal_dir.exists()
    doc = json.loads(next(daily_dir.glob("*.json")).read_text())
    assert doc["log"]["caffeine"][0]["amount_mg"] == 95
    mirror = next(journal_dir.glob("*.md")).read_text()
    assert "| Dashboard" in mirror and "[caffeine] 08:14 95 espresso" in mirror


def test_dispatch_get_state_default(journal):
    out = mcp_server.dispatch("get_state", {})
    assert "System Mode: STANDARD" in out


def test_dispatch_get_daily_roundtrip(journal):
    mcp_server.dispatch("log_field", {"field": "sleep.quality", "value": 7})
    doc = json.loads(mcp_server.dispatch("get_daily", {}))
    assert doc["log"]["sleep"]["quality"] == 7


def test_dispatch_add_and_get_rule(journal):
    msg = mcp_server.dispatch("add_rule",
                              {"topic": "nutrition", "rule": "no caffeine after 2pm",
                               "confidence": 0.9})
    assert "Added rule" in msg
    rules = mcp_server.dispatch("get_rules", {"topic": "nutrition"})
    assert "no caffeine after 2pm" in rules
