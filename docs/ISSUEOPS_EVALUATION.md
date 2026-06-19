> **⚠️ Superseded — historical record (pre-4.0.0).** This documents the original evaluation of an "IssueOps" architecture (GitHub Issues → GitHub Actions → Git state → Gemini 3 Flash), weighed against the then-current FastAPI/Slack server. IssueOps was rejected as the chat surface, but its three extracted principles — *the commit is the unit of progress*, *files > database for LLMs*, and *stateless intelligence* — outlived it and shaped the cloud-native model adopted in 4.0.0 (git-as-infrastructure, ephemeral stateless sessions, context-complete reads). The §5 decision to "stick with FastAPI/Slack for now" is itself superseded: Slack and the server were removed in 4.0.0. Retained for decision-history context; do not treat as current. For current architecture see `docs/USER_FLOW_PLAN.md`, `README.md`, and `CHANGELOG.md` [4.0.0].

# Architecture Evaluation: The "IssueOps" Model

## 1. System Overview
The proposed architecture replaces the traditional "Web Server + Database" stack with a "Repo + Runners" stack.
*   **Trigger**: GitHub Issue (User Input).
*   **Compute**: GitHub Actions (Serverless Python Scripts).
*   **State**: Git Repository (Markdown Files).
*   **Intelligence**: Gemini 3 Flash (Context-Aware Processor).

## 2. Comparative Analysis

| Dimension | OptiMind (Current) | IssueOps (Proposed) | Verdict |
| :--- | :--- | :--- | :--- |
| **Infrastructure** | **High Maintenance**. Requires `cloudflared` tunnel, active `uvicorn` process, local machine or VPS always on. | **Zero Maintenance**. Serverless. Runs only when triggered. No tunnels. | **IssueOps Wins** (for simplified operations). |
| **Latency** | **Real-Time**. Sub-second response parsing. Chat feels "Instant". | **Slow**. Runner cold-start + Setup time (~30s - 1m per reply). | **OptiMind Wins** (for conversation). |
| **UX** | **Conversational**. Slack is a chat app. Natural flow. | **Transactional**. GitHub Issues are forums. Good for logs, bad for chat. | **OptiMind Wins** (for assistant feel). |
| **Memory** | **Fragile JSON**. Hard to visualize history. | **Robust Git**. Human-readable, versioned, infinite history. | **IssueOps Wins** (for data integrity). |
| **Context** | **Filtered**. We limit tokens. | **Massive**. Reads entire repo state every run. | **IssueOps Wins** (for smarts). |

## 3. Lessons Extracted (The "Secret Sauce")

The brilliance of the "IssueOps" model isn't the GitHub UI (which is clunky for chat), but the **Backend Philosophy**:

### Lesson A: "The Commit" is the Unit of Progress
In IssueOps, every interaction results in a **Commit** to the repo. This guarantees that history is saved *before* the answer is given (or as part of it).
*   *Application*: OptiMind should treat every major interaction as a "Commit" to a journal file, not just a transient chat message.

### Lesson B: Files > Database for LLMs
LLMs read text. A database (SQL/JSON) requires serialization layers. A folder of Markdown files (`/journal/2024-01-17.md`) is **native** to the LLM. It can "read" the user's life directly.

### Lesson C: Stateless Intelligence
The IssueOps script dies after execution. It relies 100% on the *State Files* to know what's going on. This forces the system to be **Context-Complete** (no hidden RAM variables).
*   *Application*: OptiMind should maximize reliance on the `get_context()` call and minimize runtime variables.

## 4. Synthesis: The "OptiMind 2.0" Plan

We will **Hybridize** the two approaches:

1.  **Keep the Head (Slack/Local)**:
    *   Preserve the Chat Interface (Slack) and Speed (Local Server).
    *   *Reason*: "IssueOps" is too slow for a "Personal Assistant" who needs to say "Good morning" or answer quick questions.

2.  **Transplant the Heart (Memory)**:
    *   Delete the JSON Memory Store.
    *   Implement **Git-Based Markdown Journaling**.
    *   Every user message + Agent reply is logged to `braindump/{date}.md`.

3.  **Adopt the Brain (Context)**:
    *   Before answering, load the **Last 30 Days of Logs** into Gemini 3.
    *   This solves the "Sunrise Hallucination" because the "Sunrise is 7:16" fact would be in the loaded text.

## 5. Decision
*   **Infrastructure**: Stick with FastAPI/Slack (for now).
*   **Architecture**: Pivot Memory System to **Markdown Files**.
*   **Logic**: Pivot Prompting to **Full-Context Loading**.
