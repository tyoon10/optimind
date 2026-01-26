import asyncio
import sys
import os

# Ensure src is in path
sys.path.append(os.getcwd())

from src.core.agent import optimind
from src.config import config

async def main():
    print(f"🧠 OptiMind CLI (Env: {config.ENV})")
    print("------------------------------------------------")
    print("Type 'exit' to quit.\n")

    # Optional: Set a temporary "CLI" mode if you wanted
    # state_manager.update_mode("CLI_TESTING") 

    while True:
        try:
            user_input = input("You: ")
            if user_input.lower() in ["exit", "quit"]:
                break
            
            print("OptiMind: ...", end="\r")
            
            # Call the agent directly
            response = await optimind.run(user_input, user_id="CLI_USER")
            
            print(f"OptiMind: {response}\n")
            
        except KeyboardInterrupt:
            break
        except Exception as e:
            print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(main())
