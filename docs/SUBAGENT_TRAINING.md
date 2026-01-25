# Teaching OptiMind: A Guide to Calibration

There are **3 Levels** to teaching your subagents. Use the lowest level possible for the fastest results.

## Level 1: Explicit Rules (The "Law")
*Best for: Permanent preferences, hard boundaries, and facts.*

*   **Mechanism**: The **Reflector Agent** listens to every message. If you state a preference clearly, it saves it to the `user_memory.json` file.
*   **How to Teach**: Just tell the bot directly using keywords like "Always", "Never", or "I prefer".
*   **Examples**:
    *   *"I am a vegan."* (Nutritionist will never suggest eggs again).
    *   *"Never schedule meetings before 10 AM."* (Scheduler will block that time).
    *   *"My preferred cloud provider is GCP, not AWS."* (Product Manager will bias towards Google).

## Level 2: Contextual History (The "Experience")
*Best for: Nuance, tone, and evolving projects.*

*   **Mechanism**: The **Journal (Git)**. Every time you have a conversation, it is logged. Before answering, agents read the last 7 days of logs to understand *what happened recently*.
*   **How to Teach**: Correct the bot in the chat. It will "remember" the correction for the near future.
*   **Examples**:
    *   *Bot*: "Let's schedule that for 6 AM."
    *   *You*: "No, I'm doing the Solar-Sync protocol now. 6 AM is too early."
    *   *Bot (Next time)*: Will see that conversation in the logs and know you are on "Solar-Sync".

## Level 3: System Prompts (The "DNA")
*Best for: Fundamental personality changes, new capabilities, or deep role-playing.*

*   **Mechanism**: The `src/agents/library/*.py` files. These contain the "System Prompt" (the instructions that define who the agent is).
*   **How to Teach**: Edit the Python code directly.
*   **Where to find them**:
    *   `src/agents/library/scheduler_agent.py`
    *   `src/agents/library/nutritionist_agent.py`
    *   etc.
*   **Example**: Changing the Scheduler from a "Gentle Coach" to a "Drill Sergeant".
    *   *Old Prompt*: "Be encouraging and helpful."
    *   *New Prompt*: "You are a Navy SEAL commander. Accept no excuses. Use short sentences."

---

## How to "Update the Knowledge Base"
Since your Knowledge Base is split between **Memory** (Rules) and **Journal** (Logs), here is the workflow:

1.  **To Add a New Fact**: Just say it. *"Update knowledge base: My gym is 'Equinox' and it closes at 9 PM."* The Reflector should catch this.
2.  **To Correct a Wrong Assumption**: Say *"Delete the rule about X"*. The Reflector can remove old rules.
3.  **To Upload Documents**: Currently, this requires pasting the text into the chat (so it goes into the Journal) or manually adding a markdown file to the `docs/` folder and asking I (the Developer) to make the agents read it.
