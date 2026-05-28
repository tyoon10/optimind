"""
Smoke test for schemas/daily_log.schema.json.

Validates the §7.3 illustrative example from docs/USER_FLOW_PLAN.md against the
schema, plus a few negative cases that lock in the load-bearing constraints
(bare-UTC timestamps rejected, additionalProperties:false, schema_version const).

Run: pytest optimind-sdk/tests/test_daily_log_schema.py
Only needs `jsonschema` (no claude_agent_sdk).
"""

import json
import copy
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

SCHEMA_PATH = Path(__file__).resolve().parents[2] / "schemas" / "daily_log.schema.json"

# The §7.3 illustrative shape, made schema-complete (schema_version/date/tz).
EXAMPLE = {
    "schema_version": "1.0",
    "date": "2026-05-27",
    "tz": "America/New_York",
    "protocol": {
        "generated_at": "2026-05-27T05:55:00-04:00",
        "source": "default",
        "items": [
            {"id": "sunlight", "expected_window": "06:30-07:30", "duration_min": 10},
            {"id": "cold_shower", "expected_window": "07:00-08:00"},
            {"id": "meditation", "expected_window": "07:30-08:00", "duration_min": 10},
            {"id": "workout", "expected_window": "08:00-09:30", "type": "strength"},
            {"id": "deep_work", "expected_window": "09:30-12:00", "duration_min": 150},
        ],
    },
    "log": {
        "sleep": {"bedtime": "23:14", "wake_time": "06:42", "quality": 7},
        "meals": [{"time": "08:30", "items": "eggs, oats, blueberries"}],
        "caffeine": [{"time": "08:14", "amount_mg": 95, "source": "espresso"}],
        "snacks": [],
        "routine": {
            "sunlight": {"done": True, "time": "07:10", "duration_min": 12},
            "cold_shower": {"done": True, "time": "07:35"},
            "meditation": {"done": False},
        },
        "workouts": [{"time": "08:05", "duration_min": 50, "type": "strength"}],
    },
}


@pytest.fixture(scope="module")
def validator():
    with open(SCHEMA_PATH, encoding="utf-8") as f:
        schema = json.load(f)
    Draft202012Validator.check_schema(schema)
    return Draft202012Validator(schema)


def test_schema_is_itself_valid(validator):
    assert validator.schema["$id"].endswith("daily_log.schema.json")


def test_section_7_3_example_validates(validator):
    errors = sorted(validator.iter_errors(EXAMPLE), key=str)
    assert not errors, "\n".join(e.message for e in errors)


def test_minimal_doc_validates(validator):
    # protocol and log are both optional — a freshly created file is valid.
    minimal = {"schema_version": "1.0", "date": "2026-05-27", "tz": "America/New_York"}
    assert not list(validator.iter_errors(minimal))


def test_bare_utc_timestamp_rejected(validator):
    bad = copy.deepcopy(EXAMPLE)
    bad["protocol"]["generated_at"] = "2026-05-27T05:55:00Z"
    assert list(validator.iter_errors(bad)), "bare-UTC 'Z' offset must be rejected"


def test_additional_properties_rejected(validator):
    bad = copy.deepcopy(EXAMPLE)
    bad["log"]["mood"] = "great"  # not in the §7.3 shape
    assert list(validator.iter_errors(bad)), "unknown top-level log field must be rejected"


def test_wrong_schema_version_rejected(validator):
    bad = copy.deepcopy(EXAMPLE)
    bad["schema_version"] = "2.0"
    assert list(validator.iter_errors(bad)), "schema_version is a const '1.0'"


def test_bad_local_time_rejected(validator):
    bad = copy.deepcopy(EXAMPLE)
    bad["log"]["sleep"]["wake_time"] = "6:42"  # needs zero-padded HH
    assert list(validator.iter_errors(bad)), "HH:MM must be zero-padded 24h"
