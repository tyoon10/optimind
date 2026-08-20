# OptiMind System Agent Contract

Read `README.md` and `../../HERMES.md` before changing this public architecture repository.

## Commands

- `cd dashboard && npm test` — dashboard unit tests
- `cd dashboard && npm run check` — Svelte and TypeScript validation
- `cd dashboard && npm run build` — production dashboard build
- `cd optimind-sdk && python3 -m pytest tests -q` — SDK tests when dependencies are available

## Rules

- This repository is public: never add personal protocols, journal entries, health records, credentials, or private user data.
- Schema changes require a version bump and migration before the private journal rolls forward.
- Dashboard pushes deploy production; do not commit, push, or deploy without explicit approval.
- Use this repository root for coding-agent work; Hermes coordinates from the parent initiative root.
