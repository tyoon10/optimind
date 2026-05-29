"""
Validates routines/default_protocol.json (the morning-brief Routine's day-one
fallback, Task 5) against daily_log.schema.json — so the protocol the Routine
falls back to is guaranteed schema-valid before it ever reaches set_protocol.
"""

import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parents[2]
SCHEMA_PATH = ROOT / "schemas" / "daily_log.schema.json"
DEFAULT_PATH = ROOT / "routines" / "default_protocol.json"


@pytest.fixture(scope="module")
def validator():
    with open(SCHEMA_PATH, encoding="utf-8") as f:
        return Draft202012Validator(json.load(f))


def test_default_protocol_items_validate(validator):
    items = json.loads(DEFAULT_PATH.read_text(encoding="utf-8"))["items"]
    assert items, "default protocol must not be empty"
    # Wrap in a full daily doc so items validate through protocol -> ProtocolItem.
    doc = {
        "schema_version": "1.0",
        "date": "2026-05-28",
        "tz": "America/New_York",
        "protocol": {
            "generated_at": "2026-05-28T05:55:00-04:00",
            "source": "default",
            "items": items,
        },
    }
    errors = sorted(validator.iter_errors(doc), key=str)
    assert not errors, "\n".join(e.message for e in errors)


def test_default_protocol_ids_are_snake_case(validator):
    items = json.loads(DEFAULT_PATH.read_text(encoding="utf-8"))["items"]
    import re
    for it in items:
        assert re.fullmatch(r"[a-z][a-z0-9_]*", it["id"]), it["id"]
