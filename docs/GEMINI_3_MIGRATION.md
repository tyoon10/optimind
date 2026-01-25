# Gemini 3 Migration & Hybrid Authentication Guide

## 1. The Issue: "404 Publisher Model Not Found"
When attempting to use `gemini-3-flash-preview` on Google Cloud Vertex AI, we encountered a persistent `404 Not Found` error.

**Why?**
*   **Vertex AI (Enterprise)**: Access to "Preview" models is often gated by project allowlists, region quotas (e.g., `us-central1`), or delayed rollout schedules for enterprise customers.
*   **Google AI Studio (Developer/Prosumer)**: Often grants earlier access to experimental/preview models via API Keys.

## 2. The Solution: Hybrid Authentication
We implemented a **Hybrid Provider Strategy** in `src/agents/base.py`.

### Principles
The system now dynamically selects the LLM provider based on available credentials:

1.  **Primary Check (Google AI Studio)**:
    *   Does `GOOGLE_API_KEY` exist in `.env`?
    *   **Yes**: Initialize `ChatGoogleGenerativeAI` (via `langchain-google-genai`).
    *   **Benefit**: Unlocks Gemini 3 Flash/Pro Preview immediate access.

2.  **Fallback (Vertex AI)**:
    *   If no API Key, default to `ChatVertexAI` (via `langchain-google-vertexai`).
    *   **Benefit**: Uses Service Account credentials (`GOOGLE_APPLICATION_CREDENTIALS`). Best for production stability with Generally Available (GA) models like Gemini 2.0 Flash.

## 3. Backend Architecture Walkthrough

```mermaid
graph TD
    User((User)) -->|Msg| Slack[Slack Cloud]
    Slack -->|Webhook Request| Tunnel[Cloudflare Tunnel]
    Tunnel -->|Forward| Local[Local FastAPI Server :8000]
    Local -->|Event| Orch[Orchestrator Node]
    
    subgraph "The Agent Brain"
        Orch -->|Route| Agent{BaseAgent}
        
        Agent -->|Auth Check| Config[src/config.py]
        
        Config -->|Has API Key?| AIStudio[Google AI Studio Provider]
        Config -->|No Key| Vertex[Vertex AI Provider]
    end
    
    AIStudio -->|Access| Gem3[Gemini 3 Flash (Preview)]
    Vertex -->|Access| Gem2[Gemini 2.0 Flash (Stable)]
```

## 4. API Dynamics
*   **Slack -> Bot**: Slack sends HTTP POST events.
*   **Bot -> Google**:
    *   **Vertex Mode**: Uses IAM (Identity & Access Management) tokens derived from your JSON key file.
    *   **Studio Mode**: Sends the `x-goog-api-key` header with every prompt.

## 5. How to Verify
To ensure you get a response through Slack:
1.  **Server must be running**: `python -m uvicorn src.main:app ...`
2.  **Tunnel must be valid**: `cloudflared tunnel ...`
3.  **Model must accept prompt**: `verify_model.py` proved this works.
