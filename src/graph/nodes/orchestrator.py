from langchain_core.messages import SystemMessage, HumanMessage
from langchain_core.prompts import ChatPromptTemplate
from langchain_google_vertexai import ChatVertexAI
from src.graph.state import OptiMindState
from src.config import config
from src.memory.store import memory_store
from src.memory.journal import journal_manager

# Initialize LLM
# Initialize LLM with Hybrid Auth
if config.GOOGLE_API_KEY:
    try:
        from langchain_google_genai import ChatGoogleGenerativeAI
        print(f"DEBUG: Orchestrator using Google AI Studio (API Key) with model {config.GEMINI_MODEL}")
        llm = ChatGoogleGenerativeAI(
            model=config.GEMINI_MODEL,
            google_api_key=config.GOOGLE_API_KEY,
            temperature=0.0,
            max_retries=3,
            convert_system_message_to_human=True
        )
    except ImportError:
        print("ERROR: GOOGLE_API_KEY found but 'langchain-google-genai' not installed.")
        llm = ChatVertexAI(
            model_name=config.GEMINI_MODEL,
            project=config.GOOGLE_PROJECT_ID,
            location=config.GOOGLE_LOCATION,
            temperature=0.0,
            max_retries=3
        )
else:
    print(f"DEBUG: Orchestrator using Vertex AI (Service Account) with model {config.GEMINI_MODEL}")
    llm = ChatVertexAI(
        model_name=config.GEMINI_MODEL,
        project=config.GOOGLE_PROJECT_ID,
        location=config.GOOGLE_LOCATION,
        temperature=0.0
    )

# Orchestrator Prompt
ORCHESTRATOR_SYSTEM_PROMPT = """You are the Orchestrator for OptiMind.
Your job is to route the user's request to the appropriate expert.

Available Experts:
1. 'scheduler_agent': For calendar, routines, timeblocking, productivity coaching.
2. 'nutritionist_agent': For meal plans, food sourcing, grocery brands, macros.
3. 'medical_agent': For supplements, dermatology, physical therapy, biology/science questions.
4. 'product_manager_agent': For work projects, PRDs, specs, brainstorming.
5. 'reflector_agent': If the user is providing FEEDBACK, or stating a new preference.
6. 'chit_chat': For simple greetings or out-of-scope queries.

Context (User Rules):
{user_rules}

Context (Recent History):
{journal_history}

Current Time: {current_time}

Return ONLY the name of the next agent (e.g., 'scheduler_agent') or 'chit_chat' if you should reply directly.
"""

def orchestrator_node(state: OptiMindState):
    """
    Decides which agent should handle the input.
    """
    messages = state["messages"]
    last_message = messages[-1]
    print(f"DEBUG: Orchestrator thinking on: {last_message.content}")

    # 1. Log the User's Input - MOVED TO MAIN.PY for reliability
    # if isinstance(last_message, HumanMessage):
    #     journal_manager.log_interaction("User", last_message.content)

    # 2. Get relevant context
    user_rules = memory_store.get_context_str()
    journal_history = journal_manager.get_recent_context(days=7) # Flood with 7 days of history
    
    prompt = ChatPromptTemplate.from_messages([
        ("system", ORCHESTRATOR_SYSTEM_PROMPT),
        ("human", "{input}")
    ])
    
    chain = prompt | llm
    
    # In a real scenario, we might use structured output or tool calling for routing.
    # For MVP, we ask for a string.
    import datetime
    import pytz

    # Hardcode EST for MVP (or get from config if available)
    tz = pytz.timezone('US/Eastern')
    current_time_str = datetime.datetime.now(tz).strftime("%A, %B %d, %Y at %I:%M %p %Z") # e.g. Sunday, January 18, 2026 at 02:09 PM EST

    response = chain.invoke({
        "user_rules": user_rules,
        "journal_history": journal_history,
        "input": last_message.content,
        "current_time": current_time_str
    })
    

        
    # Handle Gemini 3's structured output (list of parts or dict-like string)
    content = response.content
    if isinstance(content, list):
        content = " ".join([str(p) for p in content])
    else:
        content = str(content)
        
    print(f"DEBUG: Raw Orchestrator Output -> {content}")

    # Valid agent list
    valid_agents = [
        "scheduler_agent",
        "nutritionist_agent",
        "medical_agent",
        "product_manager_agent",
        "reflector_agent",
        "chit_chat"
    ]
    
    # Simple substring search for the first valid agent name found in the content
    route = "chit_chat" # Default
    for agent in valid_agents:
        if agent in content:
            route = agent
            break
            
    print(f"DEBUG: Parsed Orchestrator Route -> {route}")
    
    # Return state update
    return {"next_agent": route}
