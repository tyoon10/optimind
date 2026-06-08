# Architecture Decision Records (ADRs)

Cross-cutting architectural decisions for OptiMind. Each ADR is a permanent, immutable record of a load-bearing choice — the *why* a thing is shaped the way it is, captured at the moment of the decision.

## What goes in an ADR

- Cross-cutting decisions that affect both repos (`optimind` + `optimind-journal`) or multiple subsystems within one repo.
- Decisions whose context would otherwise be lost — when reading the code three months later wouldn't reveal the reasoning.
- Decisions explicitly promoted from a proposal (`optimind-journal/proposals/<date>-<topic>.md`) after approval and implementation.

What does **not** go here:
- Small refactors or local code decisions (use commit messages + the §9 decision log in `USER_FLOW_PLAN.md`).
- Open proposals — those live in `optimind-journal/proposals/` until approved.
- Tactical day-to-day choices.

## Numbering convention

Sequential, zero-padded: `ADR-0001-<short-slug>.md`, `ADR-0002-<short-slug>.md`, etc. Once assigned, the number is permanent and never re-used — even if the ADR is later superseded.

## Status conventions

Each ADR carries a `Status` field:

| Status | Meaning |
|---|---|
| `proposed` | Author wants this to be the chosen direction; awaiting review |
| `accepted` | The decision is current; the system reflects it |
| `superseded by ADR-NNNN` | A newer ADR replaces this one; keep this file for historical context |
| `deprecated` | The decision is no longer current and nothing replaced it; the relevant subsystem was removed |

## Template

New ADRs SHOULD follow this skeleton:

```markdown
# ADR-NNNN: <short title>

| Field | Value |
|---|---|
| Status | accepted / superseded by ... / deprecated |
| Date | YYYY-MM-DD (accepted date) |
| Authors | name(s) |
| Promoted from | optimind-journal/proposals/<file>.md (if applicable) |
| Implementing commits | optimind: SHA, optimind-journal: SHA |

## Context
What problem was being solved? What constraints applied?

## Decision
What did we choose, in one paragraph?

## Rationale
Why this option, and not the alternatives?

## Consequences
What follows from this decision? What becomes harder, what becomes easier?

## Related
Links to other ADRs, proposals, commits, blog posts.
```

## Current ADRs

| # | Title | Status | Date |
|---|---|---|---|
| [0001](./ADR-0001-knowledge-base-normalization.md) | Knowledge-base normalization — three-tier model with mechanism connector | accepted | 2026-06-07 |
