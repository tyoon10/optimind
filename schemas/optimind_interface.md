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
| `daily/YYYY-MM-DD.json`                    | [`daily_log.schema.json`](./daily_log.schema.json)       | daily tools, structured-log dual-write |
| `comprehensive_memory.md`                  | mechanism records (anchor-ID'd subsections per [`mechanism.schema.json`](./mechanism.schema.json), v1.1+) | Analyst, Nutritionist, Scheduler |

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

1. Bump `schema_version` in the schema file. Two cases:
   - **Additive / non-breaking** (new *optional* fields only — e.g. the `"1.0"` → `"1.1"` KB-normalization bump that added optional `why_brief` / `mechanism_ref` / `last_reviewed`): widen the version constraint to an `enum` covering both values (the migration window) so existing v1.0 data still validates. **No transform script is required** — old data is forward-compatible as-is. Flip the `enum` back to a single `const` once no older data remains anywhere.
   - **Breaking** (a field is renamed, removed, or made required — e.g. a future `"1.x"` → `"2.0"`): proceed to step 2.
2. For a breaking change, add a migration script: `migrations/user_profile_<from>to<to>.py` (`user_profile_1to2.py` is the stub template kept ready for the next breaking bump).
   - The script reads the old file, transforms it, writes the new file, and SHOULD back up the old version next to it.
3. The runtime, on load, compares the file's `schema_version` to the schema's accepted set (a `const`, or the `enum` during a migration window). If the file's version is outside that set:
   - If a forward migration script exists, the runtime suggests the exact command to run.
   - The runtime does NOT auto-migrate (data changes should be explicit and reviewable).
4. Once migrated, commit the new file in `optimind-journal` and the new schema + script in `tyoon10/optimind`.

This way the two repos can be upgraded independently as long as the schema versions agree at the moment the app boots.

## Knowledge-base architecture (v1.1+)

As of `user_profile.schema.json` v1.1, the knowledge base is normalized into three connector-linked tiers. The schemas above implement the data shape; this section documents the coupling contract.

### Three tiers

| Tier | Role | Lifecycle / owner | Home |
|---|---|---|---|
| **Operational** (hot) | Protocol = what + when + context params, plus a cached `why_brief` + `mechanism_ref` connector | changes on **user context** (frequent) | `user_profile.json` rules (PreferenceRule schema) |
| **Reference / Mechanism** (warm) | Causal claim (the "why"), addressable by stable ID, with nested `sources[]` | changes on **science** (rare, external) | `comprehensive_memory.md` (anchor-ID'd subsections per `mechanism.schema.json`) |
| **Evidential / Derivation** (cold) | Full study detail + as-derived reasoning | append-only | `journal/*.md` consults, referenced from a mechanism's `sources[]` |

Cardinality is conceptually m:n at each seam, but the v1.1 implementation collapses it to 1:m — each protocol pins exactly one `mechanism_ref`, and sources nest INSIDE each mechanism's `sources[]` field rather than being addressable on their own. Promote sources to a dedicated tier (and protocols to multi-mechanism) when the collapsed form proves too thin.

### Connector resolution

A protocol rule's `mechanism_ref` (e.g. `"mech.sleep.thermal_onset"`) resolves to an anchor-ID'd subsection in `comprehensive_memory.md`. The rendering convention preserves dotted IDs (which GH-flavored markdown anchors otherwise mangle):

```markdown
<a id="mech.sleep.thermal_onset"></a>
### Evening Thermal Dump
... claim prose ...
```

Resolution is a literal anchor lookup against the memory file. The runtime SHOULD NOT auto-create mechanism records on demand — populate-on-create is the Nutritionist subagent's responsibility (see [`.claude/agents/nutritionist.md`](../.claude/agents/nutritionist.md) → Populate-on-create).

### Three load-bearing invariants

The connector is an inert string until something walks it. These three invariants are the query engine:

1. **Compressed-why-inline (denormalization-for-reads).** Every protocol rule MUST carry a non-empty `why_brief`. The hot path (Scheduler / Morning Brief generation) reads `why_brief` directly and SHOULD NOT dereference `mechanism_ref` per-apply. The second-order benefit is error detection: a rule whose `rule` text contradicts its `why_brief` is catchable on read.
2. **Coupling / sync.** On any **protocol** update → walk `mechanism_ref`, confirm consistency. On any **mechanism** update → walk back to all referencing protocols + re-validate/sync `why_brief`. The Reflection routine extension (analyst override) implements this sync-walk on every nightly fire.
3. **Re-validation trigger.** Items older than **6 months** OR below **confidence 0.95** nominate themselves for review (either threshold is sufficient). Items past either threshold are flagged on every Reflection until reviewed.

### Runtime read pattern

The hot path (daily protocol generation):
- Read `user_profile.json` rules filtered by `topic` → use `rule` + `why_brief` directly. Do NOT walk `mechanism_ref` per-apply.

The cold path (Q&A consult / decision / backfill — HEAVY-read turns):
- Read rule + walk `mechanism_ref` → read the mechanism record → optionally walk `sources[]` if the rationale is under question.
