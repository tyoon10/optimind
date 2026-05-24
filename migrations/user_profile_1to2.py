"""
Placeholder migration: user_profile.json schema 1.0 → 2.0.

Schema 2.0 does not exist yet — this file is a stub so the migration protocol
in schemas/optimind_interface.md has a concrete template to point at. When the
profile schema changes:

1. Bump the `const` in schemas/user_profile.schema.json.
2. Bump SCHEMA_VERSION in optimind-sdk/src/tools/preferences.py.
3. Fill in transform() below.
4. Run: python -m migrations.user_profile_1to2 <OPTIMIND_JOURNAL_PATH>

The migration MUST be idempotent (running it twice on already-migrated data
is a no-op, not a corruption).
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
from datetime import datetime, timezone

FROM_VERSION = "1.0"
TO_VERSION = "2.0"


def transform(profile: dict) -> dict:
    """Transform a v1.0 profile dict into a v2.0 profile dict."""
    raise NotImplementedError(
        f"Schema {TO_VERSION} is not defined yet. "
        f"Define it in schemas/user_profile.schema.json before running this migration."
    )


def migrate(journal_path: str, *, dry_run: bool = False) -> None:
    profile_path = os.path.join(journal_path, "user_profile.json")
    if not os.path.exists(profile_path):
        print(f"No user_profile.json at {profile_path}; nothing to migrate.")
        return

    with open(profile_path, "r", encoding="utf-8") as f:
        profile = json.load(f)

    current = profile.get("schema_version")
    if current == TO_VERSION:
        print(f"user_profile.json is already at schema_version {TO_VERSION}; no-op.")
        return
    if current != FROM_VERSION:
        print(
            f"Refusing to migrate: user_profile.json schema_version is {current!r}, "
            f"expected {FROM_VERSION!r}.",
            file=sys.stderr,
        )
        sys.exit(1)

    new_profile = transform(profile)
    new_profile["schema_version"] = TO_VERSION

    if dry_run:
        print(json.dumps(new_profile, indent=2))
        return

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    backup_path = f"{profile_path}.bak-{FROM_VERSION}-{timestamp}"
    shutil.copy2(profile_path, backup_path)
    with open(profile_path, "w", encoding="utf-8") as f:
        json.dump(new_profile, f, indent=2)
    print(f"Migrated. Backup written to {backup_path}.")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "journal_path",
        nargs="?",
        default=os.environ.get("OPTIMIND_JOURNAL_PATH"),
        help="Path to the optimind-journal checkout. Defaults to $OPTIMIND_JOURNAL_PATH.",
    )
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    if not args.journal_path:
        parser.error("journal_path is required (or set OPTIMIND_JOURNAL_PATH).")

    migrate(args.journal_path, dry_run=args.dry_run)


if __name__ == "__main__":
    main()
