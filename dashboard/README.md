# OptiMind Dashboard

Structured daily-logging PWA (Task 6). Static SvelteKit app on **Cloudflare Pages** that
writes to the private **`optimind-journal`** repo via the **GitHub API** — no backend,
no 24/7 host. Each submission is a **dual-write** (mirrors `optimind-sdk` `do_log_field`):

- `daily/<date>.json` — structured record (schema: `optimind/schemas/daily_log.schema.json`)
- `journal/<date>.md` — a `### HH:MM | Dashboard` mirror line

so dashboard logs reach the same reflection / long-term-memory pipeline as chat logs.

## Architecture

| Concern | Choice |
|---|---|
| Framework | SvelteKit (client-rendered SPA, prerendered shell) + `adapter-cloudflare` |
| Writes | raw `fetch` to the GitHub Contents API, isolated in `src/lib/writeDaily.ts` |
| Auth | **GitHub OAuth (PKCE)**, isolated in `src/lib/auth.ts`; secret-bearing token exchange in the `/api/oauth/token` **Pages Function** |
| Pure logic | `src/lib/daily.ts` (the TS mirror of `do_log_field`), unit-tested |
| Styling | plain CSS for the scaffold (Tailwind is a fast-follow) |
| Offline | **deferred to iteration 2** — v1 requires connectivity |

## Setup

1. **Register a GitHub OAuth App** (Settings → Developer settings → OAuth Apps):
   - Homepage: your Pages URL (e.g. `https://optimind.pages.dev`)
   - Authorization callback URL: `…/auth/callback`
   - Note the **Client ID**; generate a **Client Secret**.
2. **Local env:** `cp .env.example .env` and fill the `PUBLIC_*` values.
3. `npm install`
4. `npm run dev` — open the printed URL. (OAuth needs the callback URL to match; for local,
   add `http://localhost:5173/auth/callback` as a second callback on the OAuth app and set
   `PUBLIC_OAUTH_REDIRECT` accordingly. The token exchange needs `GITHUB_CLIENT_SECRET` in the
   environment — for local, run via `wrangler pages dev` or export it.)

## Deploy (Cloudflare Pages)

- Connect the repo; build dir `optimind/dashboard`, build command `npm run build`, output `.svelte-kit/cloudflare`.
- Set the `PUBLIC_*` vars as build env, and `GITHUB_CLIENT_SECRET` as an **encrypted** Pages secret.

## Verify

- `npm run test` — pure dual-write logic (matches `do_log_field`).
- `npm run check` — types.
- Manual: connect GitHub → log a caffeine → confirm `daily/<date>.json` + the `Dashboard`
  mirror line appear in `optimind-journal`, and the daily file validates against the schema.

## Scope (v1)

"Today" view only: protocol checklist + sleep / caffeine / meal / workout forms. No trends,
no rule management, no offline queue yet (§7.6 / §10.3 Task 6).
