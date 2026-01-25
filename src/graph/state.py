from typing import TypedDict, Annotated, List, Union, Dict, Any
import operator

class OptiMindState(TypedDict):
    """
    Global State for the OptiMind Graph.
    
    Attributes:
        messages: The conversation history (list of LangChain messages).
        user_id: The ID of the user interacting (from Slack).
        next_agent: The name of the next agent to route to.
        user_profile: Start-up context or loaded preferences.
    """
    # 'messages' uses operator.add to append new messages rather than overwrite
    messages: Annotated[List[Any], operator.add]
    
    user_id: str
    next_agent: str
    
    # Shared memory/context
    user_profile: Dict[str, Any]
    
    # Optional: Error tracking
    error: Union[str, None]
