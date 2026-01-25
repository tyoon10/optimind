import os
import glob
import sys
# Force UTF-8 output for Windows console to avoid encoding errors with emojis/special chars
sys.stdout.reconfigure(encoding='utf-8')

# Delayed imports to debug hang
# from src.config import config
# from src.agents.library.reflector_agent import reflector_agent
# from src.memory.store import memory_store
# from src.memory.schemas import MemoryAction

def ingest_file(filepath):
    """Reads a file and extracts rules using ReflectorAgent."""
    # Lazy imports
    from src.memory.store import memory_store
    
    filename = os.path.basename(filepath)
    print(f"\n--- Processing: {filename} ---")
    
    with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
        content = f.read()

    # Define strict extraction model
    from src.agents.base import BaseAgent
    from langchain_core.prompts import ChatPromptTemplate
    from src.memory.schemas import PreferenceRule
    from typing import List
    from pydantic import BaseModel
    
    print(f"DEBUG: Initializing extraction agent for {filename}...")
    
    class BulkRules(BaseModel):
        rules: List[PreferenceRule]

    ingest_prompt = """You are a Knowledge Extractor.
    Read the following conversation log and extract every explicit user preference, rule, or habit.
    
    Ignore:
    - Casual chit chat
    - Questions asked by the user (unless they imply a preference)
    - General facts
    
    Extract ONLY:
    - Specific diet preferences (e.g., "I eat Bell & Evans chicken")
    - Schedule constraints (e.g., "Wake up at 5am")
    - Medical/Health context (e.g., "I have knee pain")
    - Work preferences
    
    Source file: {source}
    
    Conversation Content:
    {content}
    """
    
    # Ad-hoc agent for bulk extraction
    extractor = BaseAgent("extractor", ingest_prompt)
    structured_llm = extractor.llm.with_structured_output(BulkRules)
    
    prompt = ChatPromptTemplate.from_messages([("system", ingest_prompt)])
    chain = prompt | structured_llm
    
    try:
        # We might need to truncate content if it's too huge, but usually txt chat logs fit in 128k context.
        result = chain.invoke({"content": content, "source": filename})
        if result and result.rules:
            for rule in result.rules:
                # Deduplication check? (Simple fuzzy string check done by store?)
                # For now, just add.
                rule.source = filename # Override source
                memory_store.add_rule(rule)
                print(f"[+] Added: {rule.rule} ({rule.topic})")
        else:
            print("No rules found.")
            
    except Exception as e:
        print(f"Error processing {filename}: {e}")

def main():
    print("DEBUG: Starting ingestion script...")
    
    # Import config here
    print("DEBUG: Loading config...")
    from src.config import config
    HISTORY_DIR = os.path.join(config.BASE_DIR, "Gemini conversation history")
    
    if not os.path.exists(HISTORY_DIR):
        print(f"Directory not found: {HISTORY_DIR}")
        return

    files = glob.glob(os.path.join(HISTORY_DIR, "*.txt"))
    print(f"Found {len(files)} conversation logs.")
    
    for f in files:
        ingest_file(f)

if __name__ == "__main__":
    main()
