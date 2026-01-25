from typing import List, Optional, Literal
from datetime import datetime
from pydantic import BaseModel, Field

class MemoryAction(BaseModel):
    """The type of operation to perform on memory."""
    action: Literal["add", "delete"] = Field(..., description="Whether to add a new rule or delete an existing one.")
    topic: str = Field(..., description="Domain of the rule")
    rule: str = Field(..., description="The content to add or the keywords to match for deletion.")
    confidence: float = Field(1.0, description="Confidence score.")

class PreferenceRule(BaseModel):
    """A specific rule or preference learned from the user."""
    topic: str = Field(..., description="Domain of the rule (e.g., 'nutrition', 'scheduling')")
    rule: str = Field(..., description="The content of the rule (e.g., 'No caffeine after 2 PM')")
    source: Optional[str] = Field("user_interaction", description="Where this rule came from")
    created_at: datetime = Field(default_factory=datetime.now)
    confidence: float = Field(1.0, description="Confidence score 0.0-1.0")

class UserProfile(BaseModel):
    """The aggregate profile of the user."""
    name: str = "User"
    rules: List[PreferenceRule] = []
    
    def get_rules_by_topic(self, topic: str) -> List[PreferenceRule]:
        """Filter rules by topic."""
        return [r for r in self.rules if r.topic == topic]
