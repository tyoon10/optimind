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
    assert doc["schema_version"] == "1.1" and doc["date"] == DATE

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
    assert daily.do_get_daily(DATE) == {"schema_version": "1.1", "date": DATE, "tz": "America/New_York"}
    daily.do_log_field("sleep.quality", 4, date=DATE)
    assert daily.do_get_daily(DATE)["log"]["sleep"]["quality"] == 4


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
    daily.do_log_field("sleep.quality", 4, date=DATE)
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


# --- postcondition verification (capture-integrity build) ---------------------
#
# The defect these guard against: a write that lands on one side, returns
# success, and tells the user "logged". Four days of real health data were lost
# that way before anything noticed.


def test_journal_failure_cannot_return_success(journal, monkeypatch):
    """If the mirror can't be appended, the call must raise, not return."""
    def boom(*a, **k):
        raise IOError("disk full")
    monkeypatch.setattr(daily, "append_dashboard_line", boom)

    with pytest.raises(daily.DualWriteError) as exc:
        daily.do_log_field("sleep.quality", 3, time="07:00", date=DATE)
    assert exc.value.completed == "structured"
    assert "reconcile" in exc.value.repair or "audit" in exc.value.repair


def test_journal_failure_rolls_back_the_structured_write(journal, monkeypatch):
    """
    A structured-only record is the worse half-write: nothing in the audit log
    says it exists, so no reconciliation can ever find it.
    """
    daily.do_log_field("sleep.wake_time", "06:42", time="06:42", date=DATE)
    before = (journal / "daily" / f"{DATE}.json").read_text(encoding="utf-8")

    monkeypatch.setattr(daily, "append_dashboard_line",
                        lambda *a, **k: (_ for _ in ()).throw(IOError("nope")))
    with pytest.raises(daily.DualWriteError):
        daily.do_log_field("sleep.quality", 3, time="07:00", date=DATE)

    assert (journal / "daily" / f"{DATE}.json").read_text(encoding="utf-8") == before


def test_rollback_removes_a_file_it_created(journal, monkeypatch):
    monkeypatch.setattr(daily, "append_dashboard_line",
                        lambda *a, **k: (_ for _ in ()).throw(IOError("nope")))
    with pytest.raises(daily.DualWriteError):
        daily.do_log_field("sleep.quality", 3, time="07:00", date=DATE)
    assert not (journal / "daily" / f"{DATE}.json").exists()


def test_rollback_never_clobbers_a_concurrent_writer(journal, monkeypatch, tmp_path):
    """Rollback proceeds only when the file still holds exactly what we wrote."""
    daily.do_log_field("sleep.wake_time", "06:42", time="06:42", date=DATE)
    path = journal / "daily" / f"{DATE}.json"

    def append_then_someone_else_writes(*a, **k):
        doc = json.loads(path.read_text(encoding="utf-8"))
        doc["log"]["meals"] = [{"time": "12:30", "items": "from another session"}]
        path.write_text(json.dumps(doc, indent=2), encoding="utf-8")
        raise IOError("mirror failed after a concurrent write")

    monkeypatch.setattr(daily, "append_dashboard_line", append_then_someone_else_writes)
    with pytest.raises(daily.DualWriteError):
        daily.do_log_field("sleep.quality", 3, time="07:00", date=DATE)

    assert _read_json(path)["log"]["meals"][0]["items"] == "from another session"


def test_structured_failure_leaves_no_dashboard_line(journal, monkeypatch):
    """The JSON side fails first, so no mirror line is ever written."""
    monkeypatch.setattr(daily, "save_daily",
                        lambda *a, **k: (_ for _ in ()).throw(IOError("read-only fs")))
    with pytest.raises(daily.DualWriteError) as exc:
        daily.do_log_field("sleep.quality", 3, time="07:00", date=DATE)
    assert exc.value.completed == ""
    assert not (journal / "journal" / f"{DATE}.md").exists()


def test_silent_no_op_write_is_caught(journal, monkeypatch):
    """
    The exact production failure: save_daily 'succeeds' but the field never
    persists. Re-reading and checking the field is what catches it.
    """
    monkeypatch.setattr(daily, "save_daily", lambda date, doc: daily._daily_path(date))
    with pytest.raises(daily.DualWriteError) as exc:
        daily.do_log_field("sleep.quality", 3, time="07:00", date=DATE)
    assert "did not persist" in exc.value.detail or "structured write failed" in exc.value.detail


def test_repeated_events_stay_append_only(journal):
    for t, mg in (("08:00", 65), ("11:20", 95), ("14:00", 95)):
        daily.do_log_field("caffeine", {"amount_mg": mg, "source": "coffee"}, time=t, date=DATE)
    entries = _read_json(journal / "daily" / f"{DATE}.json")["log"]["caffeine"]
    assert [e["time"] for e in entries] == ["08:00", "11:20", "14:00"]
    assert (journal / "journal" / f"{DATE}.md").read_text(encoding="utf-8").count("| Dashboard") == 3


def test_build_write_derives_both_sides_from_one_operation(journal):
    """The mirror line must describe exactly what went into the JSON."""
    doc, written, mirror = daily.build_write(
        {"schema_version": "1.1", "date": DATE, "tz": "America/New_York"},
        "caffeine", {"amount_mg": 65, "source": "espresso"}, "08:14",
    )
    assert doc["log"]["caffeine"] == [written]
    assert mirror == "\n### 08:14 | Dashboard\n[caffeine] 08:14 65 espresso\n"


def test_verified_write_result_reports_both_paths(journal):
    res = daily.do_log_field("routine.cold_shower", {"status": "done", "time": "07:35"},
                             time="07:35", date=DATE)
    assert res["ok"] is True
    assert res["daily_path"] and res["journal_path"]


def test_tool_text_never_says_logged_on_failure(journal, monkeypatch):
    monkeypatch.setattr(daily, "append_dashboard_line",
                        lambda *a, **k: (_ for _ in ()).throw(IOError("nope")))
    text = daily.log_field_text({"field": "sleep.quality", "value": 3, "time": "07:00"})
    assert text.startswith("NOT LOGGED")
    assert "Repair:" in text


def test_hardened_writes_remain_schema_valid(journal, validator):
    daily.do_log_field("sleep.quality", 3, time="07:00", date=DATE)
    daily.do_log_field("routine.zinc", {"status": "done", "time": "19:30"}, time="19:30", date=DATE)
    daily.do_log_field("caffeine", {"amount_mg": 65, "source": "espresso", "note": "estimated"},
                       time="08:14", date=DATE)
    doc = _read_json(journal / "daily" / f"{DATE}.json")
    assert list(validator.iter_errors(doc)) == []
