from src.config import config
from src.agents.base import BaseAgent
import time
import sys

# Force UTF-8 for console output
sys.stdout.reconfigure(encoding='utf-8')

print(f"DEBUG: Configured Model in src.config: '{config.GEMINI_MODEL}'")

if "3.0" not in config.GEMINI_MODEL and "preview" not in config.GEMINI_MODEL:
     print("WARNING: Model name doesn't look like 3.0-preview. Check .env precedence?")

agent = BaseAgent("Tester", "You are a test bot. Say exactly: 'System Operational: Gemini 3.0 Active'.")

try:
    print("DEBUG: Sending request to Vertex AI...")
    start = time.time()
    response = agent.run("Status check")
    duration = time.time() - start
    print(f"DEBUG: Response received in {duration:.2f}s")
    print(f"DEBUG: Content: {response.content}")
except Exception as e:
    print(f"ERROR: Model invocation failed: {e}")
