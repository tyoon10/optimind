# OptiMind: AI Personal Assistant

**OptiMind** is a local-first, privacy-focused AI assistant powered by Google's Gemini 3 Flash. It integrates with Slack to help manage your schedule, nutrition, and health.

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
