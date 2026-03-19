import asyncio
from datetime import datetime
import pytz
from langchain_core.messages import SystemMessage, HumanMessage, AIMessageChunk
from langchain_core.prompts import ChatPromptTemplate
from src.core.llm import get_llm
from src.core.state import state_manager
from src.memory.store import memory_store
from src.core.memory.journal import journal_manager
from src.config import config

class OptiMindAgent:
    """
    OptiMind 2.0: The Consolidated Cognitive Agent.
    Replaces the multi-agent Star Topology with a single, state-aware brain.
    """
    
    SYSTEM_PROMPT_TEMPLATE = \
    """
    You are OptiMind, a High-Performance Cognitive Companion.
    Your Goal: Optimize the user's biological and professional output using "First Principles" thinking.

    You are NOT a simple chatbot. You are a **Performance Architect** who synthesizes:
    1.  **Biology:** (Nutrition, Sleep, Circadian Rhythms, Neurochemistry)
    2.  **Productivity:** (Deep Work, Flow States, Scheduling)
    3.  **Strategy:** (Learning, Career)

    ### CURRENT ACTIVE STATE (The Context):
    System Mode: {system_mode}
    Constraints: {constraints}
    Current Focus: {focus}

    ### PERMANENT USER RULES (The Law):
    {user_profile}

    ### MEMORY CONTEXT (Recent Logs):
    {journal_history}

    ### CORE DIRECTIVES:
    1.  **Holistic Reasoning:** Never treat a problem in isolation. A schedule problem is often a sleep problem. A focus problem is often a nutrition problem.
    2.  **Chain of Thought:** Before answering complex queries, PLAN. Think: "What domains are involved? Is there a biological conflict?"
    3.  **Tone:** Disciplined, Data-Driven, Scientific, Encouraging but Strict.
    4.  **Safety:** Verify facts. Do not promote fads. Stick to consensus biology (e.g., Huberman, Attia) where applicable.
    5.  **Slack Formatting:**
        *   Do NOT use `#` or `###` for headers (Slack does not support them).
        *   Use `*Bold Text*` for headers.
        *   Use `•` for lists.
        *   Keep responses concise and visually clean.

    Current Time: {current_time}
    """

    def __init__(self):
        self.llm = get_llm(temperature=0.3)
        
    def _get_current_time(self):
        tz = pytz.timezone('US/Eastern') # Hardcoded for NYC user base, can be config'd
        return datetime.now(tz).strftime("%A, %B %d, %Y at %I:%M %p %Z")

    async def run(self, user_input: str, user_id: str = "default") -> str:
        # 0. Start-of-Turn Sync (Pull Only)
        # Ensures new server instances get latest laptop changes BEFORE thinking.
        journal_manager.sync(push=False)

        # 1. Fetch State
        active_state = state_manager.get_state()
        
        # 2. Fetch Memory (Episodic)
        # Fetch last 5 days for context (covers weekend gaps and trend data)
        journal_history = journal_manager.get_recent_context(days=5)

        # 3. Fetch User Profile (Explicit Rules)
        user_profile = memory_store.get_context_str()
        
        # 4. Log User Input (Async/Fire-and-forget strictly better, but here sync for MVP)
        # We log strictly as "User" input.
        journal_manager.log_interaction("User", user_input)
        
        # 5. Construct Prompt
        prompt = ChatPromptTemplate.from_messages([
            ("system", self.SYSTEM_PROMPT_TEMPLATE),
            ("human", "{input}")
        ])
        
        chain = prompt | self.llm
        
        # 6. Execute with retry (handles transient 503s from Gemini preview models)
        invoke_params = {
            "system_mode": active_state.get("system_mode", "STANDARD"),
            "constraints": active_state.get("active_constraints", []),
            "focus": active_state.get("current_focus", {}),
            "journal_history": journal_history,
            "user_profile": user_profile,
            "current_time": self._get_current_time(),
            "input": user_input
        }

        max_retries = 3
        for attempt in range(max_retries):
            try:
                response_msg = await chain.ainvoke(invoke_params)

                content = response_msg.content

                # Gemini 3.0 / Multimodal list handling
                if isinstance(content, list):
                    parsed_parts = []
                    for part in content:
                        if isinstance(part, dict) and 'text' in part:
                            parsed_parts.append(part['text'])
                        else:
                            parsed_parts.append(str(part))
                    content = "".join(parsed_parts)
                else:
                    content = str(content)

                # 7. Log Agent Response (Local Write)
                journal_manager.log_interaction("OptiMind", content)

                # 8. Sync is handled by the caller (slack.py) AFTER posting to Slack.
                # This keeps response latency low while ensuring sync completes reliably.

                return content

            except Exception as e:
                err_str = str(e)
                is_retryable = "503" in err_str or "UNAVAILABLE" in err_str or "overloaded" in err_str.lower()
                if is_retryable and attempt < max_retries - 1:
                    wait = 2 ** attempt  # 1s, 2s
                    print(f"WARNING: LLM attempt {attempt + 1} failed (503). Retrying in {wait}s...")
                    await asyncio.sleep(wait)
                    continue
                return f"I encountered a cognitive error: {err_str}"

optimind = OptiMindAgent()
