# ADR-0001: Knowledge-base normalization — three-tier model with mechanism connector

| Field | Value |
|---|---|
| Status | accepted |
| Date | 2026-06-07 |
| Authors | OptiMind (System) + Taewan |
| Promoted from | `optimind-journal/proposals/2026-06-07-knowledge-base-normalization.md` (private; status `IMPLEMENTED` after this commit) |
| Implementing commits | optimind: `fcea47f` (Phase 1 schemas), `<this commit>` (Phase 4 ADR + CHANGELOG); optimind-journal: `81bc3e8` (Phase 0.5 memory catch-up), `f62398d` (Phase 2 memory + profile migration), `f5acf9e` (Phase 3 agents + CLAUDE.md) |
| Resolves | open loop #4 from the 2026-06-06 Nightly Reflection (knowledge architecture pick) |
| Supersedes | the implicit "evidence lives only in the journal" pattern that preceded v1.0 of `user_profile.schema.json` |

---

## Context

On 2026-06-06 a protocol correction (evening shower: cold → warm, Haghayegh 2019) exposed that the error was only catchable because the rule carried its claimed mechanism ("to lower core body temp") inline — a bare "what" with no "why" would have propagated the inverted protocol silently. That surfaced a deeper architecture question, deliberated across the 2026-06-06 → 06-07 thread (journal entries 11:18 / 11:46 / 12:05 / 12:19 / 16:11):

The knowledge base was fuzzily layered:

- `user_profile.json` rules carried protocol + a compressed mechanism + a `source` string (mechanism duplicated inline).
- `comprehensive_memory.md` carried a fuller mechanism prose for *some* of the same protocols (selective, not 1:1).
- Full research detail (study n, effect sizes, URLs) lived only in journal consults — permanent on disk, but ephemeral in-context (ages out of the ~3-day HEAVY-read window).

**Four problems with that status quo:**

1. Mechanism was duplicated across profile + memory at two resolutions, with no sync link → drift risk.
2. Mechanism and protocol had different lifecycles but were coupled. A mechanism is universal truth that changes only when science changes (rare, external). A protocol is the personal projection of a mechanism through user context (frequent: graduated, moved, summer, new constraint). Coupling them meant context changes forced touching the science, and vice versa.
3. No connector between protocol (what) and mechanism (why) → the agent couldn't trace, update, or sync one when the other changed.
4. The evidential tier's home was unstable — "the journal entry from June 6" isn't an addressable target.

## Decision

Adopt a **three-tier, connector-linked** knowledge model. True cardinality is m:n at each seam (Sources ⇄(m:n)⇄ Mechanisms ⇄(m:n)⇄ Protocols — three tables). For the current scale (~22 rules at proposal time, 23 at acceptance), collapse pragmatically: **Sources nest INSIDE each mechanism record's `sources[]` field** — not spun up as their own addressable layer. Mechanism remains independently addressable; sources are nested. Promote sources to a dedicated tier only when nested pointers prove too thin.

| Tier | Role | Lifecycle / owner | Home |
|---|---|---|---|
| **Operational** (hot) | Protocol = what + when + context params, **plus a cached `why_brief`** + **`mechanism_ref` connector** | changes on user context (frequent) | `user_profile.json` rules |
| **Reference / Mechanism** (warm) | Causal claim (the "why"), addressable by stable ID, with its `sources[]` | changes on science (rare, external) | `comprehensive_memory.md` (anchor-ID'd; no new file at current scale) |
| **Evidential / Derivation** (cold) | Full study detail + as-derived reasoning | append-only | `journal/*.md` consults, referenced from the mechanism's `sources[]` |

### Three load-bearing invariants (the governance rule — the "query engine")

A connector in markdown/JSON is an inert string until something walks it. These three must hold or the model rots:

1. **Compressed-why-inline (denormalization-for-reads).** Every protocol carries a non-empty `why_brief` (a one-line cached mechanism). The load-bearing rationale is avoiding a dereference on every daily protocol build — a bare `mechanism_ref` would force the agent to resolve the connector on every apply, or operate blind. The second benefit is the error-detection surface: an inline mechanism that contradicts the protocol's "what" is catchable. A protocol with no `why_brief` is itself a flag.
2. **Coupling / sync.** On any **protocol** update → walk `mechanism_ref`, confirm consistency. On any **mechanism** update → walk back to all referencing protocols + re-validate/sync `why_brief`. Never update one side silently. Implemented as Method §K in the analyst override (rule→mechanism + mechanism→rules sync-walk on every Nightly Reflection).
3. **Re-validation trigger.** Protocols and mechanisms carry `last_reviewed` + `confidence`. Items older than **6 months** or below **confidence 0.95** nominate themselves for review. (Stricter than the originally-proposed 12mo / 0.85; the user explicitly overruled at Phase 0c. Trade-off accepted: more flagged items / more review cadence; the wake-time rule at 0.9 confidence will auto-flag immediately, which is the intended forcing function for long-running open loops.)

### Data-model spec

**Mechanism record** (schema: `optimind/schemas/mechanism.schema.json`, new in this ADR):

```
id:            mech.<domain>.<slug>        # stable, snake_case, e.g. mech.sleep.thermal_onset
domain:        sleep | nutrition | psychology | strategy
claim:         <one-paragraph causal mechanism prose>
sources:       [ "Haghayegh 2019 (Sleep Med Rev)", "JCSM 2021 DPG", "journal:2026-06-06#11:18" ]
last_reviewed: 2026-06-07                   # bare YYYY-MM-DD (JSON Schema format: date)
confidence:    0.0–1.0                      # numeric only
```

**Protocol rule** (`user_profile.json` — three new optional fields added to `PreferenceRule` in `user_profile.schema.json`):

```jsonc
{
  "topic": "supplementation",
  "rule": "Evening: warm shower 40–42.5°C, ~90 min pre-sleep …",  // WHAT + when + context
  "why_brief": "core-temp drop via distal-skin vasodilation",      // NEW: cached compressed why
  "mechanism_ref": "mech.sleep.thermal_onset",                     // NEW: connector → mechanism id
  "source": "…",                                                   // RETAINED during migration; long-run migrates onto the mechanism record
  "last_reviewed": "2026-06-06",                                   // NEW: re-validation hook
  "created_at": "2026-04-05T23:42:00-04:00",
  "confidence": 1.0
}
```

**Anchor mechanics:** GH-flavored markdown mangles periods in auto-anchors. Each mechanism subsection in `comprehensive_memory.md` is rendered with an explicit inline HTML anchor:

```markdown
<a id="mech.sleep.thermal_onset"></a>
### Evening Thermal Dump
```

This preserves the dotted ID format the schema's `mechanism_ref` pattern enforces (`^mech\.[a-z_]+\.[a-z0-9_]+$`).

## Rationale

The deliberation considered three alternatives:

- **(a) Hybrid implementation now** — this option. The three-tier model implemented immediately with the mechanism-connector layer.
- **(b) Hybrid + future `evidence/` stub** — same as (a) plus a placeholder dedicated evidence store. Rejected as premature scaffolding at 22-rule scale (YAGNI).
- **(c) Leave as-is** — keep the implicit two-layer structure. Rejected as inert: the connector would still be missing, drift would continue.

Cardinality collapse from m:n×3 to "sources nested in mechanism" was chosen because at 22 rules the m:n×3 normalization is over-engineered. The collapse is reversible: the `sources[]` array on a mechanism is the exact same data shape that would become a row in a separate Sources table later — promotion is a future migration, not a rewrite.

User-side scope override at Phase 0a: pilot recommendation was overruled in favor of FULL migration in a single window. Per §3C atomicity, Phase 1 (schema) + Phase 2 (data) completed in the same off-hours window on 2026-06-07 (between the 22:00 Reflection and the next 05:55 Morning Brief).

## Consequences

**Positive:**
- Mechanism + protocol now have separate lifecycles. Context changes (user moves, season change, new constraint) touch only protocols; science changes touch only mechanisms.
- The 21 mechanism records in `comprehensive_memory.md` are now addressable and citable from rules — no more "the principle is somewhere in §2."
- Reflection's K-pass surfaces drift automatically. Stale mechanisms (>6mo) and low-confidence rules (<0.95) get flagged on every fire until reviewed.
- Future evidence-tier promotion (when nested `sources[]` prove too thin) is a clean migration: extract sources into a new repo or directory; rules' `mechanism_ref` is unaffected.

**Negative / accepted trade-offs:**
- Hot path now requires the cached `why_brief` to stay in sync with the mechanism's `claim`. The sync invariant (#2) makes this an explicit Reflection responsibility, but it adds operational discipline.
- Aggressive flagging from the stricter 0.95 / 6mo thresholds means the first Reflection after rollout will surface ~5–8 rules at confidence 0.9 or 0.95 (the wake-time rule, the Caffeine-Mg Antagonism rule, several supplements). User accepted this as the intended forcing function.
- 6/23 rules don't yet have `mechanism_ref` (the meta-rules + 2 supplement rules where memory doesn't yet have a clean mechanism — B-Complex's MTHFR mechanism, Alpha-GPC exclusion's TMAO mechanism). These are tracked for a future memory addition.

**Rollback:** v1.1 fields are additive/optional; reverting = drop the new fields + restore `schema_version: 1.0` (the schema's `enum: ["1.0", "1.1"]` form supports this without rewriting). Mechanism anchor IDs in memory are inert HTML if unused. Low blast radius.

## Implementation

Five phases, all completed 2026-06-07:

1. **Phase 0.5** — memory-synthesis catch-up: synced 3 unsynced items (5/29 brand update, 6/02 gut-brain relocation, 6/03 light variant) into `comprehensive_memory.md` before adding the new connector layer. (Commit: optimind-journal `81bc3e8`.)
2. **Phase 1** — `optimind/` schema work: bumped `user_profile.schema.json` to v1.1 (with enum `["1.0", "1.1"]` for migration window); added `mechanism.schema.json`; updated `optimind_interface.md` with the three-tier architecture section; added `mech.<domain>.<slug>` keyword to `journal_entry.schema.md` grep-signal table. (Commit: optimind `fcea47f`.)
3. **Phase 2** — `optimind-journal/` full migration: 21 mechanism records carved out of `comprehensive_memory.md` §§1–4 with anchors + sources + last_reviewed + confidence; new §5 Knowledge Architecture (~6 lines); 23 rules in `user_profile.json` migrated (19/23 with `why_brief`, 17/23 with `mechanism_ref`, 23/23 with `last_reviewed`); existing `topic:system` pointer rule superseded with the new self-referential rule per §3B-3; `schema_version` bumped 1.0 → 1.1. JSON Schema validation: ✓. (Commit: optimind-journal `f62398d`.)
4. **Phase 3** — agents + runtime: CLAUDE.md "Critical write contracts" expanded 3 → 4 (added KB-sync contract); turn-start procedure HEAVY-read step added connector-walk; analyst override added Method §K (re-validation + sync-walk + coverage report); scheduler override added hot-path read pattern; nutritionist override added populate-on-create rule. (Commit: optimind-journal `f5acf9e`.)
5. **Phase 4** — close-out: this ADR + the `CHANGELOG.md` entry promoting the v1.1 schema + the disposition of the working proposal copy in `optimind-journal/proposals/`.

## Related

- Proposal source (now superseded): `optimind-journal/proposals/2026-06-07-knowledge-base-normalization.md` (private; flipped to `IMPLEMENTED` 2026-06-07; working copy retained at `proposals/implemented/` for breadcrumb)
- Deliberation thread: `optimind-journal/journal/2026-06-06.md` (entries 11:18 / 11:46 / 12:05 / 12:19 / 16:11) and `journal/2026-06-07.md` (Phase 0 approval at 20:33)
- v1.0 → v1.1 migration script: `optimind/migrations/user_profile_1to1.1.py` (TODO — current migration was done inline via `/tmp/migrate_profile_v1_1.py`; promote to repo if a second similar bump is needed)
- Article rewrite TODO: `twyoon/.../files-are-the-memory/index.md` — the §3 "Memory Is a Hard Problem" section and the closing "See the system" section need updating to describe the three-tier model. The cold→warm shower correction becomes the worked example.
