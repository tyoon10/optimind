from src.config import config
from langchain_google_vertexai import ChatVertexAI
import sys

def test_api():
    print(f"--- Testing Gemini API Connection ---")
    print(f"Project ID: {config.GOOGLE_PROJECT_ID}")
    print(f"Location: {config.GOOGLE_LOCATION}")
    print(f"Model: {config.GEMINI_MODEL}")
    
    if not config.GOOGLE_PROJECT_ID:
        print("ERROR: GOOGLE_PROJECT_ID is not set in .env")
        return

    try:
        llm = ChatVertexAI(
            model_name=config.GEMINI_MODEL,
            project=config.GOOGLE_PROJECT_ID,
            location=config.GOOGLE_LOCATION,
        )
        print("Sending request...")
        response = llm.invoke("Hello! Are you online?")
        print(f"\nSUCCESS! Response:\n{response.content}")
    except Exception as e:
        print(f"\nFAILED. Error details:\n{e}")

if __name__ == "__main__":
    test_api()
