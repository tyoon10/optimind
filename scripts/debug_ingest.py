import os
import glob
import sys
sys.stdout.reconfigure(encoding='utf-8')

# Mock config to avoid importing the heavy one if possible, or just print before import
print("DEBUG: Starting debug script...")
try:
    BASE_DIR = os.getcwd()
    HISTORY_DIR = os.path.join(BASE_DIR, "Gemini conversation history")
    print(f"DEBUG: Looking in {HISTORY_DIR}")
    
    if not os.path.exists(HISTORY_DIR):
        print(f"DEBUG: Directory not found!")
    else:
        files = glob.glob(os.path.join(HISTORY_DIR, "*.txt"))
        print(f"DEBUG: Found {len(files)} files:")
        for f in files:
            print(f" - {os.path.basename(f)}")
            
    print("DEBUG: Now attempting imports...")
    from src.config import config
    print("DEBUG: Config imported.")
    from src.agents.library.reflector_agent import reflector_agent
    print("DEBUG: Reflector imported.")

except Exception as e:
    print(f"ERROR: {e}")
