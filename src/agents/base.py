from langchain_core.prompts import ChatPromptTemplate
# We will import the specific client class dynamically or conditionally
from src.config import config
import os

class BaseAgent:
    """Base class for all OptiMind agents."""
    
    def __init__(self, name: str, system_prompt: str):
        self.name = name
        self.system_prompt = system_prompt
        
        # HYBRID AUTHENTICATION LOGIC
        # If GOOGLE_API_KEY is present, use Google AI Studio (generative-ai)
        # This allows access to "Preview" models like Gemini 3 that might be gated on Vertex
        if config.GOOGLE_API_KEY:
            try:
                from langchain_google_genai import ChatGoogleGenerativeAI
                print(f"DEBUG: Agent '{name}' using Google AI Studio (API Key) with model {config.GEMINI_MODEL}")
                self.llm = ChatGoogleGenerativeAI(
                    model=config.GEMINI_MODEL,
                    google_api_key=config.GOOGLE_API_KEY,
                    temperature=0.0,
                    convert_system_message_to_human=True # Sometimes needed for older models, safe to keep
                )
            except ImportError:
                print("ERROR: GOOGLE_API_KEY found but 'langchain-google-genai' not installed.")
                print("Falling back to Vertex AI...")
                self._init_vertex()
        else:
            # Fallback to Vertex AI (Service Account)
            print(f"DEBUG: Agent '{name}' using Vertex AI (Service Account) with model {config.GEMINI_MODEL}")
            self._init_vertex()

    def _init_vertex(self):
        from langchain_google_vertexai import ChatVertexAI
        self.llm = ChatVertexAI(
            model_name=config.GEMINI_MODEL,
            project=config.GOOGLE_PROJECT_ID,
            location=config.GOOGLE_LOCATION,
            temperature=0.0
        )
    
    def get_chain(self):
        prompt = ChatPromptTemplate.from_messages([
            ("system", self.system_prompt),
            ("human", "{input}")
        ])
        return prompt | self.llm
        
    def run(self, input_text: str, **kwargs):
        # Inject current time if not provided, for consistent timezone handling
        if "current_time" not in kwargs:
            try:
                import datetime
                import pytz
                tz = pytz.timezone('US/Eastern')
                kwargs["current_time"] = datetime.datetime.now(tz).strftime("%A, %B %d, %Y at %I:%M %p %Z")
            except ImportError:
                pass
        
        chain = self.get_chain()
        result = chain.invoke({"input": input_text, **kwargs})
        
        # Global Normalization for Gemini 3 Compatibility
        # Gemini 3 often returns content as a list of parts (text/media) instead of a simple string.
        if hasattr(result, "content") and isinstance(result.content, list):
            clean_parts = []
            for p in result.content:
                # If part is a dict (or behaves like one) and has 'text', use it
                if isinstance(p, dict) and 'text' in p:
                    clean_parts.append(p['text'])
                # If part is an object with a 'text' attribute
                elif hasattr(p, "text"):
                    clean_parts.append(p.text)
                # Fallback to string, but try to parse if it looks like the specific dict in the screenshot
                else:
                    s = str(p)
                    clean_parts.append(s)
            
            result.content = " ".join(clean_parts)
            
        # Slack Formatting Normalization
        # Slack uses single * for bold, Gemini uses **.
        # Slack doesn't support ### headers, convert to *Bold*.
        if hasattr(result, "content") and isinstance(result.content, str):
            text = result.content
            # Replace **bold** with *bold*
            text = text.replace("**", "*")
            
            # Replace ### Header with *Header*
            import re
            # Regex to match ### Text -> *Text*
            text = re.sub(r'###\s*(.*?)(?:\n|$)', r'*\1*\n', text)
            
            result.content = text

        return result
