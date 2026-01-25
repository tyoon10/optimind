from typing import Optional
from langchain_core.prompts import ChatPromptTemplate
from src.agents.base import BaseAgent
from src.memory.schemas import MemoryAction, PreferenceRule

REFLECTOR_SYSTEM_PROMPT = """You are the 'Reflector' agent for OptiMind.
Your goal is to listen to the user's input and extract explicit preferences, rules, or facts they state about themselves.

You can perform two actions:
1. 'add': New rule or preference.
2. 'delete': Remove an existing rule (e.g. "I'm not vegan anymore", "Remove the gluten rule").

Examples:
User: "I hate meetings before 9am."
Output: action="add", topic="scheduling", rule="No meetings before 9am", confidence=1.0

User: "Actually, I prefer almond milk in my smoothies."
Output: action="add", topic="nutrition", rule="Prefer almond milk in smoothies", confidence=1.0

User: "Remove the gluten intolerance rule. I was testing."
Output: action="delete", topic="nutrition", rule="gluten", confidence=1.0

User: "Draft a PRD for the dashboard."
Output: null (This is a task, not a preference)

IMPORTANT:
- If the user implies a strong preference, set confidence=1.0. 
- If the user is unsure ("maybe", "I think"), set confidence=0.5.
- NEVER set confidence=0.0 for a successfully extracted rule.
"""

class ReflectorAgent(BaseAgent):
    def __init__(self):
        super().__init__(name="reflector", system_prompt=REFLECTOR_SYSTEM_PROMPT)
        # Use structured output to force the LLM to adhere to the MemoryAction schema
        self.structured_llm = self.llm.with_structured_output(MemoryAction)

    def run(self, input_text: str) -> Optional[MemoryAction]:
        """
        Analyzes input and returns a MemoryAction if found, else None.
        """
        try:
            prompt = ChatPromptTemplate.from_messages([
                ("system", self.system_prompt),
                ("human", "{input}")
            ])
            chain = prompt | self.structured_llm
            result = chain.invoke({"input": input_text})
            
            # Post-processing enforcement
            if result and result.confidence <= 0.0:
                 result.confidence = 1.0
            
            # Allow Reflector to be lazy; if it returns invalid/empty stuff:
            if result and not result.rule:
                return None
            
            return result
        except Exception as e:
            # If extraction fails (or model refuses), return None
            print(f"Reflector extraction failed/ignored: {e}")
            return None

reflector_agent = ReflectorAgent()
