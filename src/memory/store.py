import json
import os
from typing import List
from src.config import config
from src.memory.schemas import UserProfile, PreferenceRule

class MemoryStore:
    """
    A simple file-based memory store for the MVP.
    Stores user preferences in a JSON file.
    """
    def __init__(self, file_path: str = "data/journal/user_profile.json"):
        # If path is relative, join with BASE_DIR. If absolute, use as is.
        # Note: data/journal is relative to BASE_DIR
        self.file_path = os.path.join(config.BASE_DIR, file_path)
        self.profile = self._load()

    def _load(self) -> UserProfile:
        """Load profile from JSON file."""
        if not os.path.exists(self.file_path):
            return UserProfile()
        
        try:
            with open(self.file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            return UserProfile(**data)
        except Exception as e:
            print(f"Error loading memory: {e}")
            return UserProfile()

    def save(self):
        """Save current profile to JSON file."""
        with open(self.file_path, "w", encoding="utf-8") as f:
            f.write(self.profile.model_dump_json(indent=2))

    def add_rule(self, rule: PreferenceRule):
        """Add a new rule and save."""
        self.profile.rules.append(rule)
        self.save()

    def delete_rule(self, topic: str, content: str) -> bool:
        """
        Delete a rule if it matches the topic and contains the content string using fuzzy match.
        Returns True if something was deleted.
        """
        initial_count = len(self.profile.rules)
        # Filter out rules that match the topic AND contain the content (case-insensitive)
        self.profile.rules = [
            r for r in self.profile.rules 
            if not (r.topic == topic and content.lower() in r.rule.lower())
        ]
        
        if len(self.profile.rules) < initial_count:
            self.save()
            return True
        return False

    def get_context_str(self, topic: str = None) -> str:
        """Get a formatted string of rules for the LLM context."""
        rules = self.profile.rules
        if topic:
            rules = [r for r in rules if r.topic == topic]
            
        if not rules:
            return "No specific preferences found."
            
        return "\n".join([f"- [{r.topic}] {r.rule}" for r in rules])

# Global instance
memory_store = MemoryStore()
