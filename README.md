# OptiMind: AI Personal Assistant

> **Status — Public design archive.** This repo is the engineering record of OptiMind: schemas, agent prompts, dashboard, the v3 SDK reference implementation, and the design thinking behind them. The personal data that runs through the system lives in a separate, private companion repo.
>
> **Active runtime:** `github.com/tyoon10/optimind-journal` (private). The agent runs via the Claude Code mobile/desktop app directly on that journal repo — no Slack, no server, no 24/7 host. CLAUDE.md, personal agent overrides, and the user's rule store live alongside the journal files.
>
> **What this repo contains:**
> - `schemas/` — canonical JSON Schemas + the role / interface contracts that bind both repos.
> - `routines/` — paste-ready prompts for the three scheduled cloud CC Routines (Morning Brief / Reflection / Weekly Review).
> - `.claude/agents/` — generic subagent definitions (analyst / nutritionist / scheduler) that the private repo layers personal overrides on.
> - `dashboard/` — SvelteKit static PWA, deployed to Cloudflare Pages; structured-capture surface for the journal.
> - `optimind-sdk/` — v3 Python rebuild on the Claude Agent SDK. The canonical reference for the dual-write contract, the daily-log algorithm, and the structured-logging tools. Useful as a reference even though the production path no longer runs it as a server.
> - `docs/USER_FLOW_PLAN.md` — the living design doc: goals, flows, surface decisions, the §9 engineering-decision log.
> - `migrations/` — schema-migration scripts; one per `schema_version` bump.
>
> **History:** The repo originally hosted a Gemini 3 Flash + LangChain + FastAPI + Slack-Bolt server (v1–v2, Jan–Feb 2026, submitted to the Gemini 3 Hackathon, deployed to Cloud Run). That stack was abandoned once Claude Code mobile became a viable interface, and the entire server + tunnel + Cloud Run scaffolding was removed. The v1/v2 working artifacts (debug logs, deploy guides, PowerShell scripts) live in a personal off-repo archive, not here.

---

## 🧭 How this repo fits with `optimind-journal`

OptiMind is split across two repos that bind at runtime:

| Repo | Visibility | Role |
|---|---|---|
| `optimind` (this repo) | Public | **The SYSTEM** — schemas, prompts, dashboard code, generic agent definitions, design docs |
| `optimind-journal` | Private | **The DATA** — `CLAUDE.md` (active system prompt), `user_profile.json`, `state.json`, `comprehensive_memory.md`, `journal/YYYY-MM-DD.md`, `daily/YYYY-MM-DD.json`, personal `.claude/agents/` overrides |

The clean abstraction: anything that describes *how the agent thinks* lives here; anything that describes *what the user specifically does, takes, or believes* lives in the private journal. A reader of this repo learns the architecture without learning the user's personal protocol.

### Where each artifact type lives

| Artifact type | Lives in | Update cadence |
|---|---|---|
| Canonical schemas | `optimind/schemas/` (public) | Rare; bump `schema_version` on breaking changes; add a migration in `optimind/migrations/` |
| Routine prompts (source of truth) | `optimind/routines/*.md` (public) | When the workflow changes; **manually re-paste to claude.ai UI** to take effect |
| Routine prompts (running) | claude.ai Routines configuration UI | Re-pasted from `optimind/routines/*.md` when behavior should track the repo |
| Generic agent personas | `optimind/.claude/agents/*.md` (public) | When a persona's domain scope changes |
| Personal agent overrides | `optimind-journal/.claude/agents/*.md` (private) | When the user's specific context for the persona changes |
| Active system prompt | `optimind-journal/CLAUDE.md` (private) | Anytime the chat agent's behavior contract changes — highest-leverage knob |
| Reference system prompt (public, templated) | `optimind-sdk/CLAUDE.md` (public) | Periodically synced — the *generic* parts of the journal CLAUDE.md, with personal context as `{{TEMPLATE}}` placeholders |
| User rules | `optimind-journal/user_profile.json` (private) | Via the Reflection routine or explicit user edit |
| System mode + constraints | `optimind-journal/state.json` (private) | Via chat commands or routine writes |
| Conversation history (verbatim) | `optimind-journal/journal/YYYY-MM-DD.md` (private) | Every chat turn |
| Structured logs | `optimind-journal/daily/YYYY-MM-DD.json` (private) | Every dual-write |
| Dashboard code | `optimind/dashboard/` (public) | **Auto-deploys to Cloudflare Pages on push to `main`** |
| Engineering decisions | `optimind/docs/USER_FLOW_PLAN.md` §9 (public) | One entry per architecture decision |
| Personal protocol changes | `optimind-journal/user_profile.json` + journal entries (private) | When the user changes their own protocol |

### Six governance rules for ongoing updates

1. **The "could a stranger read this?" test.** Before committing to `optimind/`, ask whether the change reveals anything specific to the user's personal protocol. If yes, either generalize the change or move it to `optimind-journal/`. If no, commit freely. Engineering scaffolds and generic patterns are public; specific brands, doses, and behavioral fingerprints are private.

2. **Schema changes flow downhill, with migrations.** When you change a schema in `optimind/schemas/`, write a migration script in `optimind/migrations/` that updates `user_profile.json` or `daily/*.json` in `optimind-journal`. Bump `schema_version`. The Reflection routine's version check will catch any drift.

3. **Routine prompt edits don't auto-deploy.** `optimind/routines/*.md` is the canonical record; the runtime version lives in the claude.ai Routines UI. When you edit a file, decide explicitly whether to re-paste. Two valid choices — track the public repo (the generalized prompt runs), or diverge intentionally (a more-specific prompt runs while the public file shows the generalized version).

4. **`CLAUDE.md` edits are immediately consequential.** A push to `optimind-journal/CLAUDE.md` takes effect on every future Routine fire and every new chat session. The system prompt is sealed at session start, so existing chats keep the old version — **start a fresh chat to pick up a major CLAUDE.md change.** Other file edits (`user_profile.json`, `state.json`) propagate via the turn-start procedure and don't need a chat restart.

5. **Dashboard edits are deployments.** A push to `optimind/dashboard/` triggers a Cloudflare Pages build. Treat `dashboard/` as production code — feature-flag if unsure, don't push half-finished work to `main`.

6. **Engineering decisions in `optimind`; personal protocol decisions in `optimind-journal`.** Engineering: *"we picked OAuth over PAT"* → `docs/USER_FLOW_PLAN.md` §9. Personal: *"I changed my supplement schedule"* → `optimind-journal/user_profile.json`. Don't mix them — engineering history is the public archive's value; protocol history belongs in the private data layer.

### One pitfall worth naming

`optimind-sdk/CLAUDE.md` is **not** the runtime system prompt. It's a reference template with `{{USER_NAME}}` / `{{USER_CITY}}` placeholders — what a developer adapting this repo to their own use would fill in. The *actual* runtime prompt that drives the cloud chat sessions is `optimind-journal/CLAUDE.md`. When you evolve runtime behavior, edit the journal version; periodically sync the generic parts back into the SDK reference.

---

## 🔧 Working in this repo

### Schemas (`schemas/`)

The four canonical contracts — `user_profile.schema.json`, `daily_log.schema.json`, `journal_entry.schema.md`, `optimind_interface.md` — are the public API between this repo and the journal. Both repos reference these as the single source of truth. Bump `schema_version` on breaking changes; write a migration in `migrations/` before rolling forward.

### Routines (`routines/`)

Three paste-ready Markdown prompts plus a default protocol JSON. Each file's fenced `text` block is what gets pasted into the claude.ai Routines UI. Editing a file here is documentation; re-paste manually to update the running Routine.

### Dashboard (`dashboard/`)

SvelteKit static PWA. GitHub OAuth (PKCE) via `dashboard/src/lib/auth.ts` + a Cloudflare Pages Function at `dashboard/src/routes/api/oauth/token/+server.ts` for the code→token exchange (GitHub's token endpoint has no CORS). Writes to `optimind-journal` via the GitHub REST API, following the dual-write contract in `optimind-sdk/src/tools/daily.py`.

Local dev:
```bash
cd dashboard
npm install
cp .env.example .env   # fill in PUBLIC_GITHUB_CLIENT_ID + PUBLIC_OAUTH_REDIRECT
npm run dev            # http://localhost:5173
```

Deployment: pushes to `main` trigger a Cloudflare Pages build. `GITHUB_CLIENT_SECRET` lives in Pages → Settings → Variables/Secrets, **never** in the repo.

### `optimind-sdk/` (v3 Python reference)

The canonical reference for the dual-write contract (`src/tools/daily.py:do_log_field`) and the structured-logging tool surface. See [`optimind-sdk/ARCHITECTURE.md`](optimind-sdk/ARCHITECTURE.md) for the problem-driven redesign.

```bash
cd optimind-sdk
pip install -r requirements.txt
cp .env.example .env   # set OPTIMIND_JOURNAL_PATH
pytest                 # runs the reference-implementation tests
```

---

## 🔐 Privacy

This repo contains **no personal data**. The user's rules, conversation history, structured logs, and active system prompt all live in the private `optimind-journal` repo. `.env.example` files are templates only — see `.gitignore` for the `data/` + `*.json` + `.env` carve-out that protects against accidental commits.

If you fork this repo to build your own personal-assistant variant, you'll create your own private journal repo and bind it to your fork via `OPTIMIND_JOURNAL_PATH` (per `schemas/optimind_interface.md`).
