import json
import os
from datetime import datetime
from src.config import config

class ActiveStateManager:
    """
    Manages the 'Active State Object' – a persistent JSON that tracks the user's
    current mode, constraints, and immediate focus (The 'Memory Governor').
    """
    
    DEFAULT_STATE = {
        "system_mode": "STANDARD", # STANDARD, EXAM_MODE, DEEP_WORK, RECOVERY
        "active_constraints": [], # e.g. ["No Caffeine after 2 PM", "Leg Injury"]
        "current_focus": {
            "title": "None",
            "deadline": None
        },
        "last_updated": None
    }
    
    def __init__(self, filename="state.json"):
        self.filepath = os.path.join(config.DATA_DIR, filename)
        self._ensure_file()
        
    def _ensure_file(self):
        if not os.path.exists(self.filepath):
            self.save_state(self.DEFAULT_STATE)
            
    def get_state(self) -> dict:
        try:
            with open(self.filepath, 'r') as f:
                return json.load(f)
        except (json.JSONDecodeError, FileNotFoundError):
            return self.DEFAULT_STATE
            
    def save_state(self, state: dict):
        state["last_updated"] = datetime.now().isoformat()
        with open(self.filepath, 'w') as f:
            json.dump(state, f, indent=2)
            
    def update_mode(self, mode: str):
        state = self.get_state()
        state["system_mode"] = mode
        self.save_state(state)
        
    def add_constraint(self, constraint: str):
        state = self.get_state()
        if "active_constraints" not in state:
            state["active_constraints"] = []
        if constraint not in state["active_constraints"]:
            state["active_constraints"].append(constraint)
            self.save_state(state)
            
    def clear_constraints(self):
        state = self.get_state()
        state["active_constraints"] = []
        self.save_state(state)

state_manager = ActiveStateManager()
