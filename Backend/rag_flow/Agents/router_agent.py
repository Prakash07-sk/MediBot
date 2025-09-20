from utils import logger
from utils.vector_db_service import vector_db_service
from .dynamic_agent import DynamicAgent

async def router_function(state: dict):
    """
    Fully dynamic router function.
    Uses the prompt assigned to this node in state (from POML).
    Returns a single string route: "tools", "vector_db", or "fallback_agent"
    """

    print(f"\033[93m[ROUTER_AGENT] Processing routing decision\033[0m")
    user_input = state.get("input", "")
    node_prompt = state.get("prompt", "")
    messages = list(state.get("messages", []))

    logger.info(f"[RouterAgent] Processing input: {user_input}")

    dynamic_agent = DynamicAgent({
        "input": user_input,
        "messages": messages,
        "prompt": node_prompt
    })
    route_decision = await dynamic_agent.generate_response()
    
    # Clean up the route decision
    route_decision = str(route_decision).strip().lower()
    route_decision = route_decision.replace("'", "").replace('"', "").replace(".", "").strip()

    # Special logging and state updates for vector_db and tools routing
    if "vector_db" in route_decision:
        logger.info(f"[RouterAgent] VECTOR_DB CAPTURED - Routing to vector database agent")
        print(f"\033[92m[ROUTER_AGENT] VECTOR_DB CAPTURED - Decision: '{route_decision}'\033[0m")
        
        # Check database connection status and update message accordingly
        db_status = vector_db_service.get_connection_status()
        
        if db_status["connected"]:
            state["response"] = "Routing to vector database agent - searching ChromaDB for medical information..."
        else:
            state["response"] = "Routing to vector database agent for medical information. Note: ChromaDB database is currently not connected - system will acknowledge this limitation."
        
        state["routing_status"] = "vector_db_in_progress"
        
    if "tools" in route_decision:
        logger.info(f"[RouterAgent] TOOLS CAPTURED - Routing to tools agent")
        print(f"\033[92m[ROUTER_AGENT] TOOLS CAPTURED - Decision: '{route_decision}'\033[0m")
        
        # Update state with progress message for tools routing
        state["response"] = "This is tools routing - processing operational request. Process is under progress..."
        state["routing_status"] = "tools_in_progress"
        
    if "fallback_agent" in route_decision:
        logger.info(f"[RouterAgent] FALLBACK CAPTURED - Routing to fallback agent")
        print(f"\033[92m[ROUTER_AGENT] FALLBACK CAPTURED - Decision: '{route_decision}'\033[0m")
        
        # Update state with progress message for fallback routing
        state["response"] = "This query is being handled by the fallback agent for general assistance."
        state["routing_status"] = "fallback_in_progress"

    # Return **only a string** for LangGraph
    return route_decision
