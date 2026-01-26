from langgraph.graph import StateGraph, END
from src.graph.state import OptiMindState
from src.graph.nodes.orchestrator import orchestrator_node
from src.graph.nodes.reflector import reflector_node
from src.graph.nodes.experts import (
    scheduler_expert_node, 
    nutritionist_expert_node, 
    medical_expert_node, 
    product_manager_expert_node,
    chit_chat_expert_node
)

def build_graph():
    """Constructs the main OptiMind agent graph."""
    
    workflow = StateGraph(OptiMindState)
    
    # Add Nodes
    workflow.add_node("orchestrator", orchestrator_node)
    workflow.add_node("reflector_agent", reflector_node)
    
    # Experts
    workflow.add_node("scheduler_agent", scheduler_expert_node)
    workflow.add_node("nutritionist_agent", nutritionist_expert_node)
    workflow.add_node("medical_agent", medical_expert_node)
    workflow.add_node("product_manager_agent", product_manager_expert_node)
    workflow.add_node("chit_chat", chit_chat_expert_node)
    
    # Set Entry Point
    workflow.set_entry_point("orchestrator")
    
    # Conditional Routing Logic
    def route_request(state: OptiMindState):
        route = state.get("next_agent")
        
        # Whitelist of valid agent names
        valid_agents = [
            "scheduler_agent", 
            "nutritionist_agent", 
            "medical_agent", 
            "product_manager_agent", 
            "reflector_agent",
            "chit_chat"
        ]
        
        if route in valid_agents:
            return route
            
        return "chit_chat" # Default fallback to chit_chat instead of END
 
    # Add Edges
    workflow.add_conditional_edges(
        "orchestrator",
        route_request,
        {
            "scheduler_agent": "scheduler_agent",
            "nutritionist_agent": "nutritionist_agent",
            "medical_agent": "medical_agent",
            "product_manager_agent": "product_manager_agent",
            "reflector_agent": "reflector_agent",
            "chit_chat": "chit_chat",
            END: END
        }
    )
    
    # Experts return to END (for now)
    workflow.add_edge("scheduler_agent", END)
    workflow.add_edge("nutritionist_agent", END)
    workflow.add_edge("medical_agent", END)
    workflow.add_edge("product_manager_agent", END)
    workflow.add_edge("reflector_agent", END)
    workflow.add_edge("chit_chat", END)
    
    # Experts return to END (for now)
    workflow.add_edge("scheduler_agent", END)
    workflow.add_edge("nutritionist_agent", END)
    workflow.add_edge("medical_agent", END)
    workflow.add_edge("product_manager_agent", END)
    workflow.add_edge("reflector_agent", END)
    
    return workflow.compile()

graph = build_graph()
