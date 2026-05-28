"""
Unit tests for the daily-log tools (Task 2).

Core guarantee under test (§7.5): every `log_field` call writes BOTH
daily/<date>.json and a `### HH:MM | Dashboard` mirror line in journal/<date>.md.
Also checks get_daily/set_protocol round-trips and that the JSON the tools
produce validates against schemas/daily_log.schema.json (Task 1).
"""

import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

from src.tools import daily

SCHEMA_PATH = Path(__file__).resolve().parents[2] / "schemas" / "daily_log.schema.json"
DATE = "2026-05-27"


@pytest.fixture()
def journal(tmp_path, monkeypatch):
    """Point OPTIMIND_JOURNAL_PATH at an empty temp checkout."""
    monkeypatch.setenv("OPTIMIND_JOURNAL_PATH", str(tmp_path))
    return tmp_path


@pytest.fixture(scope="module")
def validator():
    with open(SCHEMA_PATH, encoding="utf-8") as f:
        return Draft202012Validator(json.load(f))


def _read_json(p):
    with open(p, encoding="utf-8") as f:
        return json.load(f)


def test_log_field_dual_write_scalar(journal):
    res = daily.do_log_field("sleep.wake_time", "06:42", time="06:42", date=DATE)

    daily_file = journal / "daily" / f"{DATE}.json"
    journal_file = journal / "journal" / f"{DATE}.md"
    assert daily_file.exists(), "daily/<date>.json must be written"
    assert journal_file.exists(), "journal/<date>.md mirror must be written"

    doc = _read_json(daily_file)
    assert doc["log"]["sleep"]["wake_time"] == "06:42"
    assert doc["schema_version"] == "1.0" and doc["date"] == DATE

    mirror = journal_file.read_text(encoding="utf-8")
    assert "### 06:42 | Dashboard" in mirror
    assert "[sleep.wake_time] 06:42" in mirror
    assert res["daily_path"] == str(daily_file)
    assert res["journal_path"] == str(journal_file)


def test_log_field_event_appends_with_time(journal):
    daily.do_log_field("caffeine", {"amount_mg": 95, "source": "espresso"},
                        time="08:14", date=DATE)
    daily.do_log_field("caffeine", {"amount_mg": 60, "source": "tea"},
                        time="13:30", date=DATE)

    doc = _read_json(journal / "daily" / f"{DATE}.json")
    caf = doc["log"]["caffeine"]
    assert len(caf) == 2, "events append, never overwrite"
    assert caf[0] == {"time": "08:14", "amount_mg": 95, "source": "espresso"}

    mirror = (journal / "journal" / f"{DATE}.md").read_text(encoding="utf-8")
    assert "[caffeine] 08:14 95 espresso" in mirror
    assert mirror.count("| Dashboard") == 2


def test_singular_alias_routes_to_plural_array(journal):
    daily.do_log_field("meal", {"items": "eggs, oats, blueberries"}, time="08:30", date=DATE)
    doc = _read_json(journal / "daily" / f"{DATE}.json")
    assert doc["log"]["meals"][0] == {"time": "08:30", "items": "eggs, oats, blueberries"}
    # mirror tag preserves the caller's canonical keyword
    mirror = (journal / "journal" / f"{DATE}.md").read_text(encoding="utf-8")
    assert "[meal] 08:30 eggs, oats, blueberries" in mirror


def test_routine_item_set_and_bool_render(journal):
    daily.do_log_field("routine.cold_shower", {"done": True, "time": "07:35"}, date=DATE)
    doc = _read_json(journal / "daily" / f"{DATE}.json")
    assert doc["log"]["routine"]["cold_shower"] == {"done": True, "time": "07:35"}
    mirror = (journal / "journal" / f"{DATE}.md").read_text(encoding="utf-8")
    assert "[routine.cold_shower] true 07:35" in mirror


def test_get_daily_roundtrip_and_default(journal):
    assert daily.do_get_daily(DATE) == {"schema_version": "1.0", "date": DATE, "tz": "America/New_York"}
    daily.do_log_field("sleep.quality", 7, date=DATE)
    assert daily.do_get_daily(DATE)["log"]["sleep"]["quality"] == 7


def test_set_protocol_roundtrip(journal):
    items = [
        {"id": "sunlight", "expected_window": "06:30-07:30", "duration_min": 10},
        {"id": "deep_work", "expected_window": "09:30-12:00", "duration_min": 150},
    ]
    doc = daily.do_set_protocol(items, source="rule_derived", date=DATE)
    assert doc["protocol"]["source"] == "rule_derived"
    assert doc["protocol"]["items"] == items
    # generated_at must carry a numeric offset, never bare 'Z'
    assert not doc["protocol"]["generated_at"].endswith("Z")
    assert doc["protocol"]["generated_at"][-6] in "+-"


def test_built_document_validates_against_schema(journal, validator):
    """A realistic sequence of writes must produce a schema-valid daily file."""
    daily.do_log_field("sleep.bedtime", "23:14", date=DATE)
    daily.do_log_field("sleep.wake_time", "06:42", date=DATE)
    daily.do_log_field("sleep.quality", 7, date=DATE)
    daily.do_log_field("caffeine", {"amount_mg": 95, "source": "espresso"}, time="08:14", date=DATE)
    daily.do_log_field("meal", {"items": "eggs, oats"}, time="08:30", date=DATE)
    daily.do_log_field("workout", {"duration_min": 50, "type": "strength"}, time="08:05", date=DATE)
    daily.do_log_field("routine.cold_shower", {"done": True, "time": "07:35"}, date=DATE)
    daily.do_set_protocol(
        [{"id": "sunlight", "expected_window": "06:30-07:30", "duration_min": 10}],
        source="default", date=DATE,
    )

    doc = daily.do_get_daily(DATE)
    errors = sorted(validator.iter_errors(doc), key=str)
    assert not errors, "\n".join(e.message for e in errors)
