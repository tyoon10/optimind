# OptiMind — Hermes dashboard plugin

A read-only record-integrity tab beside Workspaces. It answers one question at a
glance: **can the numbers be trusted today?**

## Why this exists

`journal/YYYY-MM-DD.md` and `daily/YYYY-MM-DD.json` are two representations of
the same day. When a structured write silently no-ops, the journal keeps the
data and the JSON does not — and every downstream count reads that silence as a
behavior miss. Four days of real data were lost that way before anything
noticed.

This tab shows the divergence directly, using the *same* engine that gates the
nightly Reflection (`optimind-journal/scripts/optimind_core.py`). It does not
reimplement the classification, so the tab and the CLI cannot disagree about
what a day is.

## Scope

Read-only, like the other plugins here — it never writes to the journal.
Capture and repair live in the OptiMind web app, which works from a phone; this
tab is the desk-side monitor.

| Endpoint | What it gives you |
|---|---|
| `GET /health` | Whether the journal checkout is reachable |
| `GET /integrity?days=N` | Per-day dual-write status for the window |
| `GET /day/{date}` | One day's structured record plus its Dashboard mirror lines |
| `GET /coverage?days=N` | Per-field capture counts, with lost writes counted separately |

## Statuses

| Glyph | Status | Meaning |
|---|---|---|
| `✓` | matched | Both records agree |
| `◑` | journal_only | The journal has it, the structured log lost it — **a write defect, not a missed habit** |
| `◐` | structured_only | The JSON has it, the audit log never recorded it |
| `!` | needs_input | The journal line is incomplete (no time, no dose) — only you can finish it |
| `—` | blackout / no_data | Nothing was captured |
| `●` | in_progress | The current NYC day, never counted as a miss |

Colour never carries meaning alone; each state pairs a hue with a glyph and a word.

## Install

The journal path comes from `OPTIMIND_JOURNAL_PATH` (the same variable the SDK
runtime uses). Nothing is hard-coded — this repo is public, the journal is not.

```bash
ln -s "$PWD/plugin" ~/.hermes/plugins/optimind
hermes plugins enable optimind
export OPTIMIND_JOURNAL_PATH=/path/to/optimind-journal
hermes dashboard          # backend routes mount at dashboard startup
```

Backend routes are registered only when the dashboard starts, so restart it
after enabling.

## Develop

```bash
node --check plugin/dashboard/dist/index.js
python3 -c "import ast; ast.parse(open('plugin/dashboard/plugin_api.py').read())"
```

`dist/index.js` is plain JS using `React.createElement` against
`window.__HERMES_PLUGIN_SDK__` — the Hermes plugin loader has no build step, so
there is no bundle to compile.
