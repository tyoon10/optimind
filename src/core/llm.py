from src.config import config

def get_llm(temperature=0.0):
    """
    Factory to return the appropriate LangChain LLM instance based on config.
    Prioritizes Google AI Studio (API Key) if available, falls back to Vertex AI.
    """
    if config.GOOGLE_API_KEY:
        try:
            from langchain_google_genai import ChatGoogleGenerativeAI
            print(f"DEBUG: Using Google AI Studio (API Key) with model {config.GEMINI_MODEL}")
            return ChatGoogleGenerativeAI(
                model=config.GEMINI_MODEL,
                google_api_key=config.GOOGLE_API_KEY,
                temperature=temperature,
                convert_system_message_to_human=True
            )
        except ImportError:
            print("ERROR: GOOGLE_API_KEY set but 'langchain-google-genai' missing.")
            # Fall through to Vertex
            
    # Fallback to Vertex AI
    from langchain_google_vertexai import ChatVertexAI
    print(f"DEBUG: Using Vertex AI (Service Account) with model {config.GEMINI_MODEL}")
    return ChatVertexAI(
        model_name=config.GEMINI_MODEL,
        project=config.GOOGLE_PROJECT_ID,
        location=config.GOOGLE_LOCATION,
        temperature=temperature
    )
