from src.graph.state import OptiMindState
from src.agents.library.reflector_agent import reflector_agent
from src.memory.store import memory_store
from src.memory.schemas import PreferenceRule
from langchain_core.messages import AIMessage

def reflector_node(state: OptiMindState):
    """
    Analyzes the user's last message to extract and store preferences.
    """
    messages = state["messages"]
    last_message = messages[-1]
    
    # Run the reflector agent
    action = reflector_agent.run(last_message.content)
    
    if not action:
        return {"messages": [AIMessage(content="I didn't detect any specific preference to save.")]}
        
    if action.action == "add":
        # Create a new rule object
        new_rule = PreferenceRule(
            topic=action.topic,
            rule=action.rule,
            confidence=action.confidence
        )
        memory_store.add_rule(new_rule)
        response_text = f"Analyzed: Saved new preference for **{action.topic}**: *{action.rule}*"
        
    elif action.action == "delete":
        deleted = memory_store.delete_rule(action.topic, action.rule)
        if deleted:
            response_text = f"Analyzed: Removed preference about **{action.rule}** from **{action.topic}**."
        else:
            response_text = f"Analyzed: Couldn't find a matching rule for **{action.rule}** in **{action.topic}** to delete."
    else:
        response_text = "Analyzed: Unsure whether to save or delete. Could you rephrase?"
        
    return {"messages": [AIMessage(content=response_text)]}
