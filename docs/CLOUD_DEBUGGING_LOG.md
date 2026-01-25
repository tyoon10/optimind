# Cloud Run Deployment & Debugging Log (Rev 1 - 24)

**Date:** January 18, 2026
**Project:** OptiMind (OptimAll)
**Environment:** Google Cloud Run + GitHub (Journal)

## 📌 Executive Summary
The migration from a local Python script to a 24/7 Cloud Native Agent involved solving three fundamental challenges:
1.  **Ephemeral Memory**: Using Git to provide persistent memory in a container that wipes itself on restart.
2.  **Event Handling**: Managing Slack's 3-second timeout requirement vs. LLM's long processing time.
3.  **Serverless Resource Model**: Identifying why the agent "froze" mid-thought (CPU Throttling).

---

## 📅 Phase 1: The Git Sync Struggle (Rev 1 - 15)
**Goal:** Make the bot remember conversations by syncing markdown files to GitHub.

### 🔴 The Problem
Cloud Run containers are ephemeral. Each deployment (or restart) wipes local files. We needed the bot to `git clone` its memory on startup and `git push` after every message.

### 🔧 Challenges & Fixes
*   **"Dubious Ownership" Error**:
    *   *Symptom:* Git refused to operate in `/app/data/journal`.
    *   *Root Cause:* Docker runs as root, but Git is cautious about permissions.
    *   *Fix:* Added `RUN git config --global --add safe.directory '*'` to Dockerfile.
*   **Authentication Failures**:
    *   *Symptom:* `could not read Username for 'https://github.com'`.
    *   *Approach:* Tried storing credentials in `.git/config` (failed on restart).
    *   *Final Fix:* Injected the **Personal Access Token (PAT)** directly into the remote URL (`https://PAT@github.com/...`) at runtime in `journal.py`.
*   **Merge Conflicts**:
    *   *Symptom:* `Your local changes would be overwritten by merge`.
    *   *Root Cause:* We tried to `pull` (download) before `committing` our latest local log.
    *   *Fix:* Changed Sync Order to: **Add -> Commit -> Pull -> Push**.

---

## 📅 Phase 2: The "Triple Response" Bug (Rev 16 - 18)
**Goal:** Stop the bot from replying to the same message 3 times.

### 🔴 The Problem
Slack requires an HTTP 200 OK response within **3 seconds**. The LLM takes ~10 seconds to "think." Because we didn't reply in 3s, Slack assumed failure and retried the webhook 3 times.

### 🔧 The Logic Trap
1.  **Naive Approach**: Process message -> Send to LLM -> Reply to Slack. (Too slow, triggers retries).
2.  **Async Fix (The Catalyst for Phase 3)**:
    *   We moved the LLM processing to a **Background Task** (`asyncio.create_task`).
    *   We immediately returned `200 OK` to Slack.
    *   *Result:* Triple response fixed. Bot only replies once.
    *   *Unintended Consequence:* **Massive Latency (See Phase 3).**

---

## 📅 Phase 3: The 9-Minute "Black Hole" (Rev 19 - 23)
**Goal:** Solve why the bot took 9 minutes to reply, despite being "fixed."

### 🔴 The Symptom
*   User sends: `9:54 PM`
*   Bot replies: `10:03 PM` (9-minute delay)
*   Logs: Show a massive gap. The request arrives, silent for 9 mins, then finishes.

### 🕵️‍♂️ Investigation & False Leads
1.  **Hypothesis A: "Traffic Jam"**: Maybe the Load Balancer is slow updating to the new revision?
    *   *Test:* "Speed check". Result: Still slow. (Disproven).
2.  **Hypothesis B: "Cold Start"**: Maybe the container takes 9 minutes to boot?
    *   *Test:* Checked startup logs. Boot time is <4 seconds. (Disproven).
3.  **Diagnosis (The Smoking Gun)**:
    *   Deployed **Revision 22 (Tracer)** with high-fidelity logging (`DEBUG: Webhook Received`).
    *   *Log Proof:* Request arrived at `21:54:50`. Processing started at `21:54:50`.
    *   **BUT** the next log entry was `22:03:51`.
    *   *Conclusion:* The code literally *stopped executing* for 9 minutes.

### ✅ The Root Cause: CPU Throttling
Cloud Run (by default) **allocates CPU only during the HTTP Request**.
1.  We received the webhook.
2.  We started the background task.
3.  We returned `200 OK` to Slack.
4.  **Cloud Run saw the request finish and cut the CPU to 0%.** 🥶
5.  The background task froze mid-air.
6.  9 minutes later, a health check or another event woke the CPU up briefly, allowing the task to finish.

### 🚀 The Fix (Rev 23)
*   Added `--no-cpu-throttling` to the deployment command.
*   *Result:* CPU stays allocated even after the HTTP response is sent.
*   *Latency:* **<15 seconds.**

---

## 📅 Phase 4: Time Travel (Rev 24)
**Goal:** Fix the bot thinking it was tomorrow.

### 🔴 The Problem
*   The bot created `2026-01-19.md` while it was still `Jan 18` in New York (EST).
*   *Root Cause:* Servers run on **UTC**. `datetime.date.today()` returns the UTC date. When it's 8 PM EST, it's 1 AM UTC (Tomorrow).

### ✅ The Fix
*   Forced strict **Timezone Awareness**.
*   Updated `_get_daily_file_path` to convert `now()` to `US/Eastern` before extracting the date.
*   *Result:* Files and Logs align perfectly with the User's reality.

---

## 🏆 Final Architecture
*   **Compute**: Google Cloud Run (Always-On CPU).
*   **Memory**: Git-backed Markdown Journal (Persistent).
*   **Input**: Slack Events API (Async/Non-blocking).
*   **Logic**: Gemini 3 Flash (via Vertex AI/Studio).
*   **Time**: Synchronized to EST.
