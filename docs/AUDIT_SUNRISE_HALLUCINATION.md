# Audit: Sunrise Time Hallucination & Memory Failure

## 1. Interaction Summary
*   **User Goal**: Adjust routine based on "Manhattan Sunrise" time.
*   **Failure 1 (Hallucination)**: Agent guessed sunrise time (5:26 AM) instead of knowing it.
*   **Correction**: User stated sunrise is 7:16 AM.
*   **Failure 2 (Memory Ignored)**: Agent acknowledged correction ("Memory Updated!"), but subsequent routine generation *ignored* it.
*   **Failure 3 (Repeated Hallucination)**: Agent re-stated sunrise is 5:26 AM later.

## 2. Root Cause Analysis

### A. Memory Retrieval Mismatch
*   **Observation**: The Reflector saved the rule under `topic="environment"` (inferred from log).
*   **Code Defect**: `scheduler_expert_node` in `experts.py` **only fetches** `topic="scheduling"`.
*   **Result**: The Scheduler never saw the "environment" rule about sunrise. It was flying blind.

### B. Lack of Ground Truth (Tools)
*   **Observation**: The model "hallucinated" 5:26 AM because it has no internet access or weather tool.
*   **Defect**: LLMs cannot know real-time data like "Sunrise today" without a tool.

## 3. Remediation Plan

### Short-Term Fix (Code Patch)
1.  **Broaden Context**: Update `scheduler_expert_node` to fetch **ALL** rules (`memory_store.get_context_str(topic=None)`) or at least include `environment` + `scheduling`.
    *   *Why*: Pruning context is good for tokens, but strict siloing kills intelligence. A "Sunrise" fact (Environment) implies a "Wake Up" adjustment (Schedule).

### Long-Term Architecture (Recommended)
1.  **Add Search Tool**: Integrate `Google Search` or `OpenMeteo` tool so the agent can look up "Sunrise in Manhattan today".
2.  **Vector Store**: Move from JSON topics to semantic search (RAG). The agent would query "Sunrise time rules" and retrieve the relevant `environment` rule automatically.

## 4. Next Steps
I recommend applying the **Short-Term Fix** immediately:
*   Modify `src/graph/nodes/experts.py` to allow the Scheduler to see `environment` rules.
*   This will fix the immediate "ignoring my correction" bug.
