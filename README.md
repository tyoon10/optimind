# OptiMind: AI Personal Assistant

> **Status — Archived (2026-04-19).** This repo is a design/engineering record of two completed iterations of OptiMind. The active version is no longer here.
>
> **Active version:** `github.com/tyoon10/optimind-journal` — a Claude Code native workflow. The agent runs via the Claude Code mobile/desktop app directly on a private journal repo; no Slack, no server, no deployment. CLAUDE.md, subagents (`nutritionist`, `scheduler`, `analyst`), and rule storage live alongside the journal files.
>
> **What's in this repo:**
> - `src/` — v1-v2 (Jan–Feb 2026): Gemini 3 Flash + LangChain + FastAPI + Slack-Bolt. Submitted to the Gemini 3 Hackathon. Deployed to Cloud Run.
> - `optimind-sdk/` — v3.0 (Mar 2026): Rebuilt on the Claude Agent SDK. See [`optimind-sdk/ARCHITECTURE.md`](optimind-sdk/ARCHITECTURE.md) for the full problem-driven redesign. Never deployed — superseded by the Claude Code mobile workflow before production cutover.
>
> **Why the Slack/server architecture was abandoned:** once Claude Code mobile became a viable interface, the entire server+tunnel+Cloud Run stack was infrastructure for a problem that no longer existed. The agent reads/writes the journal markdown files directly.

---

**OptiMind** was a local-first, privacy-focused AI assistant that integrated with Slack to help manage schedule, nutrition, and health.

The documentation below covers the original Gemini 3 Flash + LangChain version (v1-v2), which is the submission form for the Gemini 3 Hackathon.

## 🚀 How to Start (After Restarting Laptop)

### Option 1: The Easy Way (One-Click)
1.  Open PowerShell or Terminal.
2.  Navigate to this folder: `cd /path/to/OptiMind`
3.  Run the startup script:
    ```powershell
    .\start_optimind.ps1
    ```
4.  Two new windows will pop up (Server + Tunnel).

### Option 2: The Manual Way
If you prefer running commands yourself, open two separate terminal windows:

**Window 1: The Brain (Server)**
```bash
python -m uvicorn src.main:app --host 0.0.0.0 --port 8000 --reload
```

**Window 2: The Bridge (Tunnel)**
```bash
.\cloudflared.exe tunnel --url http://localhost:8000
```

---

## ⚠️ Important: Connecting to Slack
Because we are using a free "Quick Tunnel," **your URL changes every time you restart.**

1.  Look at the likely output in the **Tunnel Window**:
    ```
    +--------------------------------------------------------------------------------+
    |  Your quick tunnel has been created! Visit it at (it may take some time to be reachable):  |
    |  https://some-random-name.trycloudflare.com                                    |
    +--------------------------------------------------------------------------------+
    ```
2.  Copy that URL (e.g., `https://example-123.trycloudflare.com`).
3.  Go to [api.slack.com/apps](https://api.slack.com/apps) -> Your App -> **Event Subscriptions**.
4.  Update the **Request URL** to:
    `https://[YOUR-NEW-URL].trycloudflare.com/slack/events`
5.  Wait for it to say "Verified" and click **Save Changes** (bottom right).

## 📊 Features
*   **Orchestrator**: Intelligently routes your questions.
*   **Memory**: Logs every interaction to `data/journal/` for long-term recall.
*   **Experts**: Specialized agents for Scheduling, Nutrition, and Health.

## 🛠️ Troubleshooting
*   **"No Response"**: Check the Server window. Did it crash?
*   **"Slack Verification Failed"**: Ensure the Tunnel is running and you copied the URL correctly (https + /slack/events).
*   **"Sunrise is Wrong"**: The bot now reads `data/journal`. You can manually edit today's markdown file to correct facts if needed.

---

## 🏆 Gemini 3 Competition Submission

**OptiMind** is submitted for the Gemini 3 Hackathon.

### 🔑 Configuration (Env Vars)
To run this project, you need the following environment variables in a `.env` file or your deployment environment:
*   `GOOGLE_API_KEY`: Your Gemini API Key.
*   `SLACK_BOT_TOKEN`: Information from your Slack App.
*   `SLACK_APP_TOKEN`: App-level token.
*   `SLACK_SIGNING_SECRET`: Signing secret.

> **Note on Privacy:** This repository does NOT include the User's personal journal (`data/journal`) or `user_profile.json` as they contain private health and professional data.
>
> If you run this without `GITHUB_PAT` and `JOURNAL_REPO_URL` configured, OptiMind will default to **Memory-Only Mode**, creating a fresh, empty journal locally for testing purposes.
