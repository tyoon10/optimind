from src.graph.state import OptiMindState
from src.memory.store import memory_store
from src.memory.journal import journal_manager
from src.agents.library.scheduler_agent import scheduler_agent
from src.agents.library.nutritionist_agent import nutritionist_agent
from src.agents.library.medical_agent import medical_agent
from src.agents.library.product_manager_agent import product_manager_agent
from langchain_core.messages import AIMessage

def scheduler_expert_node(state: OptiMindState):
    """Executes the Scheduler Expert logic."""
    print("DEBUG: Entering Scheduler Expert Node")
    messages = state["messages"]
    last_message = messages[-1].content
    
    # 1. Fetch Rules + History (Fix for Sunrise Amnesia)
    rules = memory_store.get_context_str(topic="scheduling")
    history = journal_manager.get_recent_context(days=3) # Give it 3 days of heavy context
    full_context = f"{rules}\n\n=== RECENT MEMORY LOGS ===\n{history}"
    
    # 2. Run Agent
    response = scheduler_agent.run(input_text=last_message, rules=full_context)
    
    # 3. Log Output
    journal_manager.log_interaction("Agent (Scheduler)", response.content)
    
    return {"messages": [response]}

def nutritionist_expert_node(state: OptiMindState):
    """Executes the Nutritionist Expert logic."""
    print("DEBUG: Entering Nutritionist Expert Node")
    messages = state["messages"]
    last_message = messages[-1].content
    rules = memory_store.get_context_str(topic="nutrition")
    response = nutritionist_agent.run(input_text=last_message, rules=rules)
    
    # Log Output
    journal_manager.log_interaction("Agent (Nutritionist)", response.content)
    
    return {"messages": [response]}

def medical_expert_node(state: OptiMindState):
    """Executes the Medical Science Expert logic."""
    print("DEBUG: Entering Medical Expert Node")
    messages = state["messages"]
    last_message = messages[-1].content
    rules = memory_store.get_context_str(topic="medical") 
    response = medical_agent.run(input_text=last_message, rules=rules)
    
    # Log Output
    journal_manager.log_interaction("Agent (Medical)", response.content)
    
    return {"messages": [response]}

def product_manager_expert_node(state: OptiMindState):
    """Executes the PM Expert logic."""
    print("DEBUG: Entering PM Expert Node")
    messages = state["messages"]
    last_message = messages[-1].content
    rules = memory_store.get_context_str(topic="work")
    response = product_manager_agent.run(input_text=last_message, rules=rules)
    
    # Log Output
    journal_manager.log_interaction("Agent (ProductManager)", response.content)
    
    return {"messages": [response]}

from src.agents.library.chit_chat_agent import chit_chat_agent

def chit_chat_expert_node(state: OptiMindState):
    """Executes the ChitChat logic."""
    print("DEBUG: Entering ChitChat Node")
    messages = state["messages"]
    last_message = messages[-1].content
    response = chit_chat_agent.run(input_text=last_message)
    
    # Log Output
    journal_manager.log_interaction("Agent (ChitChat)", response.content)
    
    return {"messages": [response]}
