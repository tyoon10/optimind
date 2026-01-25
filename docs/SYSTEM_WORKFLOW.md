# OptiMind System Workflow (Cloud Architecture)

This document explains the lifecycle of a single interaction in the **OptiMind** system once migrated to the cloud.

## The "Hacker's Cycle"
The core philosophy is **"Git as Brain"**. The application state is not in a database; it is in the Git commit history.

```mermaid
sequenceDiagram
    participant User as 📱 User (Slack)
    participant Cloud as ☁️ Cloud Run (OptiMind)
    participant Git as 🐙 GitHub (Memory)
    participant AI as ✨ Gemini 3 Flash (Brain)

    Note over Cloud: 1. Cold Start (Boot)
    Cloud->>Git: git clone https://github.com/Start...
    Cloud->>Cloud: Load "Memory" (Markdown Files)
    
    User->>Cloud: "Build a 1-hour workout plan based on my history"
    
    Note over Cloud: 2. Context Loading
    Cloud->>Git: git pull (Check for updates)
    Cloud->>Cloud: Read last 30 days of Journals
    Cloud->>AI: Send User Input + Workout History
    
    Note over AI: 3. Reasoning
    AI->>AI: Analyzes past leg days, recovery, and goals.
    AI-->>Cloud: "Response: Here is a Leg Day plan focused on hypertrophy..."
    
    Note over Cloud: 4. Memory Commitment
    Cloud->>Cloud: Append Plan to /data/journal/2026-01-18.md
    Cloud->>Git: git add .
    Cloud->>Git: git commit -m "Created workout plan"
    Cloud->>Git: git push
    
    Cloud-->>User: "Here is your plan: 1. Squats..."
```

## Component Roles

### 1. 📱 Slack (The Interface)
*   **Role**: The **User Interface**. It serves as both the input terminal and the display for the Agent's intelligence.
*   **Interaction**:
    *   **Input**: Sends your questions ("Plan my day") to Cloud Run.
    *   **Output**: Renders the Agent's rich markdown responses, workout plans, and daily schedules.

### 2. ☁️ Google Cloud Run (The Body)
*   **Role**: The "Executor". It is a serverless container that wakes up when Slack knocks.
*   **Key Feature**: It has **Amnesia**. Every time it starts, it is a blank slate.
*   **The Fix**: On startup, it uses your `GITHUB_PAT` to **Clone** your repository. This gives it "Instant Memory".

### 3. ✨ Gemini 3 Flash (The Brain)
*   **Role**: The "Processor". It takes the massive amount of text (Context) gathered by the Body and decides what to do.
*   **Interaction**: The Body sends: `[System Instructions] + [Last 30 Days of Journals] + [User Input]`. Gemini replies with the answer + any actions.

### 4. 🐙 GitHub (The Memory)
*   **Role**: The "Hippocampus" (Long-term storage).
*   **Interaction**:
    *   **Read**: When the bot wakes up, it reads the repo to know who you are.
    *   **Write**: When the bot learns something (e.g., you worked out), it **Commits and Pushes** that fact to the repo.
    *   **Benefit**: If Cloud Run crashes or restarts, nothing is lost. The memory is safely in GitHub.
