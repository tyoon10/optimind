# OptiMind ↔ optimind-journal Interface Contract

This document is the **coupling contract** between the `tyoon10/optimind` application (this repo) and the `optimind-journal` data repo. It exists so that **neither repo needs to know the other's location at build time** — they bind at runtime via an environment variable, and they agree on data shape via the schemas in [`./`](./).

## Repo split

| Repo               | Owns                                                                 |
|--------------------|----------------------------------------------------------------------|
| `tyoon10/optimind` | Agent runtime, tool definitions, generic agent prompts, this schema |
| `optimind-journal` | Personal data (`user_profile.json`, daily journal files), personal agent overrides |

Both repos reference the schemas in this directory as the single source of truth. The schemas are checked into `tyoon10/optimind` (canonical); `optimind-journal` MAY vendor a copy but MUST NOT diverge.

## Runtime binding: `OPTIMIND_JOURNAL_PATH`

The app discovers the journal repo at startup via the `OPTIMIND_JOURNAL_PATH` environment variable.

- **Value:** absolute filesystem path to the root of the `optimind-journal` checkout (the directory that contains `user_profile.json` and the daily `*.md` files).
- **Default:** if unset, falls back to `<optimind-sdk>/data/` (the legacy in-repo location). A warning is logged.
- **Required for production.** The Python runtime SHOULD refuse to start in production if the path is unset and the fallback directory doesn't exist.

Resolution code lives in `optimind-sdk/src/config.py` and is consumed by:
- `optimind-sdk/src/tools/journal.py` (read/search/log)
- `optimind-sdk/src/tools/preferences.py` (user_profile.json)
- `optimind-sdk/src/tools/state.py` (state.json)
- `optimind-sdk/src/hooks/journal_hook.py` (auto-log)

## What the app reads

| Path (relative to `OPTIMIND_JOURNAL_PATH`) | Schema                                                | Read by                          |
|--------------------------------------------|-------------------------------------------------------|----------------------------------|
| `user_profile.json`                        | [`user_profile.schema.json`](./user_profile.schema.json) | preference tools                 |
| `state.json`                               | (informal; see `optimind-sdk/src/tools/state.py`)     | state tools                      |
| `journal/YYYY-MM-DD.md`                    | [`journal_entry.schema.md`](./journal_entry.schema.md)   | journal tools, Analyst subagent  |

On load of `user_profile.json`, the app MUST validate against the JSON Schema. If `schema_version` is missing or mismatched, the app refuses to proceed (see Migration protocol below).

## What the app writes

| Path                                | Writer                                    |
|-------------------------------------|-------------------------------------------|
| `user_profile.json` (rules array)   | preference tools (`add_rule`, `delete_rule`) |
| `state.json`                        | state tools (`set_state`)                 |
| `journal/YYYY-MM-DD.md`             | journal tools (`log_entry`), journal hook |

All writes preserve `additionalProperties: false` — the app will not silently introduce fields not declared in the schema.

## LSP-style agent override resolution

Agent prompts are resolved with a layered lookup that mirrors how an LSP client resolves capabilities:

1. **Base layer:** `tyoon10/optimind/.claude/agents/<name>.md` — generic agent definitions, no personal references.
2. **Override layer:** `<OPTIMIND_JOURNAL_PATH>/.claude/agents/<name>.md` — personal "Before You Answer" blocks that reference `user_profile.json`, named contacts, etc.

The runtime concatenates **base + override** (override appended). If the override file is absent, the base prompt is used as-is. The override layer SHOULD NOT re-declare the base — it only adds personal context. This keeps the open-source repo free of personal data while letting each user maintain their own override layer in their own journal repo.

## Schema migration protocol

When a schema's shape changes (a field is added, renamed, or removed):

1. Bump `schema_version` in the schema file (e.g. `"1.0"` → `"2.0"`).
2. Add a migration script: `migrations/user_profile_<from>to<to>.py` (e.g. `user_profile_1to2.py`).
   - The script reads the old file, transforms it, writes the new file, and SHOULD back up the old version next to it.
3. The runtime, on load, compares the file's `schema_version` to the schema's `const`. If they differ:
   - If a forward migration script exists, the runtime suggests the exact command to run.
   - The runtime does NOT auto-migrate (data changes should be explicit and reviewable).
4. Once migrated, commit the new file in `optimind-journal` and the new schema + script in `tyoon10/optimind`.

This way the two repos can be upgraded independently as long as the schema versions agree at the moment the app boots.
