"""
FastAPI routes for the OptiMind record-integrity tab.

Read-only, like every other plugin here: it observes the journal checkout and
never writes to it. Capture and repair belong in the SvelteKit app, which is
reachable from a phone; this tab is the desk-side monitor.

The classification is NOT reimplemented here. It imports optimind_core from the
journal repo's scripts/, which is the same engine that gates the nightly
Reflection, so this tab and the CLI can never disagree about what a day is.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Any, Optional

from fastapi import APIRouter, HTTPException, Query

router = APIRouter()

def _journal_root() -> Path:
    """
    The optimind-journal checkout.

    Set OPTIMIND_JOURNAL_PATH -- the same variable the SDK runtime uses. No
    location is hard-coded here: this file lives in the public framework repo,
    and the journal is private.
    """
    env = os.environ.get("OPTIMIND_JOURNAL_PATH")
    if env:
        return Path(env)

    # No env var: search upward for a checkout that actually holds the engine.
    # A fixed parents[N] hop is brittle -- it silently depends on where this
    # plugin sits inside the framework repo, and got it wrong once already.
    # Probing for the file we need works from any depth or symlink.
    here = Path(__file__).resolve()
    for ancestor in here.parents:
        if (ancestor / "scripts" / "optimind_core.py").exists():
            return ancestor
        for sibling in ("journal", "optimind-journal"):
            candidate = ancestor / sibling
            if (candidate / "scripts" / "optimind_core.py").exists():
                return candidate
    return here.parents[3] / "journal"  # nothing found; report this path in the error


def _engine():
    """Import the shared engine from the journal checkout, or explain why not."""
    scripts = _journal_root() / "scripts"
    if not (scripts / "optimind_core.py").exists():
        raise FileNotFoundError(
            f"optimind_core.py not found under {scripts}. "
            "Set OPTIMIND_JOURNAL_PATH to the optimind-journal checkout."
        )
    if str(scripts) not in sys.path:
        sys.path.insert(0, str(scripts))
    import optimind_core  # noqa: PLC0415
    try:
        from reconcile_daily_logs import convert_fact  # noqa: PLC0415

        def resolver(fact):
            return convert_fact(fact).ok
    except Exception:
        resolver = None  # audit still works, just without the needs_input split
    return optimind_core, resolver


def _fail(exc: Exception) -> None:
    status = 404 if isinstance(exc, FileNotFoundError) else 400 if isinstance(exc, ValueError) else 500
    raise HTTPException(status_code=status, detail={"error": str(exc), "type": type(exc).__name__}) from exc


@router.get("/health")
async def health() -> dict:
    """Whether the journal checkout is reachable — shown before any data loads."""
    root = _journal_root()
    try:
        core, _ = _engine()
        return {
            "ok": True,
            "journal_root": str(root),
            "today": core.today_nyc(),
            "daily_files": len(list((root / "daily").glob("*.json"))),
            "journal_files": len(list((root / "journal").glob("*.md"))),
        }
    except Exception as exc:
        return {"ok": False, "journal_root": str(root), "error": str(exc)}


@router.get("/integrity")
async def integrity(days: int = Query(14, ge=1, le=180)) -> dict:
    """
    Dual-write status for the last N days.

    `closed_mismatches` is the number that matters: repairable divergence on
    days that have ended. The current day is reported but never counted, and
    `needs_input` days are excluded because no rerun can fix them.
    """
    try:
        core, resolver = _engine()
        today = core.today_nyc()
        start = core.daterange(today, today)[0]
        import datetime  # noqa: PLC0415

        start = (datetime.date.fromisoformat(today) - datetime.timedelta(days=days - 1)).isoformat()
        reports = core.audit_range(str(_journal_root()), start, today, today=today, resolver=resolver)
        broken = core.closed_mismatches(reports)
        closed = [r for r in reports if not r.in_progress]
        return {
            "window": {"start": start, "end": today},
            "today": today,
            "closed_days": len(closed),
            "matched": sum(1 for r in closed if r.status == core.MATCHED),
            "closed_mismatches": len(broken),
            "needs_input_days": sum(1 for r in closed if r.needs_input),
            "ok": not broken,
            "days": [r.to_dict() for r in reports],
        }
    except Exception as exc:
        _fail(exc)


@router.get("/day/{date}")
async def day(date: str) -> dict:
    """One day's structured record plus the Dashboard mirror lines behind it."""
    try:
        core, resolver = _engine()
        d = core.load_day(str(_journal_root()), date)
        report = core.classify_day(d, core.today_nyc(), resolver=resolver)
        return {
            "date": date,
            "status": report.to_dict(),
            "log": (d.daily or {}).get("log") or {},
            "protocol_items": d.protocol_items,
            "user_turns": d.user_turns,
            "facts": [
                {"time": f.time, "field": f.field, "value": f.raw}
                for f in d.facts if f.is_log_field
            ],
        }
    except Exception as exc:
        _fail(exc)


@router.get("/coverage")
async def coverage(days: int = Query(14, ge=1, le=180)) -> dict:
    """
    Per-field capture counts over closed days.

    `journal_only` is reported beside `captured` on purpose: a field can look
    uncaptured purely because its write was lost, and ranking it as a habit
    failure on that basis is the miscount this whole system exists to prevent.
    """
    try:
        core, resolver = _engine()
        import datetime  # noqa: PLC0415

        today = core.today_nyc()
        start = (datetime.date.fromisoformat(today) - datetime.timedelta(days=days - 1)).isoformat()
        rows: dict[str, dict[str, Any]] = {}
        closed = 0
        for date in core.daterange(start, today):
            if date >= today:
                continue
            closed += 1
            d = core.load_day(str(_journal_root()), date)
            skeys = core.structured_keys(d.daily or {})
            jkeys, _ = core.journal_keys(d.facts, resolver)
            for key in set(skeys) | set(jkeys):
                row = rows.setdefault(key, {"field": key, "captured": 0, "journal_only": 0, "dates": []})
                if skeys.get(key):
                    row["captured"] += 1
                    row["dates"].append(date)
                elif jkeys.get(key):
                    row["journal_only"] += 1
        return {
            "window": {"start": start, "end": today},
            "closed_days": closed,
            "fields": sorted(rows.values(), key=lambda r: (-r["captured"], r["field"])),
        }
    except Exception as exc:
        _fail(exc)
