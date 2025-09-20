# RAG_Workflow/Agents/DynamicAgent.py
import asyncio
from utils import config
from utils.tools import execute_tool
from utils.vector_db_service import vector_db_service
from middleware.LLM_Middleware import LLM_Middleware

class DynamicAgent:
    """
    A generic dynamic agent that runs a prompt through LiteLLM.
    The state must include:
    - input: user query
    - messages: list of conversation messages
    - prompt: system prompt for the agent
    """
    def __init__(self, initial_state: dict):
        self.state = initial_state
        self.llm_middleware = LLM_Middleware()

    async def generate_response(self):
        """
        Return just a single string for router nodes,
        or full message for normal agents.
        """

        # Check if there's a previous response from router
        previous_response = self.state.get("response", "")
        routing_status = self.state.get("routing_status", "")
        
        # Build context with previous response if available
        if previous_response and routing_status:
            # Special handling for vector_db routing
            if "vector_db" in routing_status:
                # Check if database is connected and search for data
                db_status = vector_db_service.get_connection_status()
                
                if db_status["connected"]:
                    # Database is connected - search for relevant data
                    search_results = await vector_db_service.search_doctor_info(self.state["input"])
                    
                    if search_results.get("found"):
                        # Format the database results for the LLM
                        db_context = "Database search results:\n"
                        for result in search_results["results"]:
                            db_context += f"- {result['content']}\n"
                            if result.get("metadata"):
                                db_context += f"  Metadata: {result['metadata']}\n"
                        
                        context = f"""
Previous Router Response: {previous_response}
Routing Status: {routing_status}
Current Prompt: {self.state["prompt"]}

{db_context}

Based on the above database results, provide a helpful and accurate response to the user's query.
"""
                    else:
                        context = f"""
Previous Router Response: {previous_response}
Routing Status: {routing_status}
Current Prompt: {self.state["prompt"]}

Database search completed but no matching information was found for the query: "{self.state["input"]}"
Please inform the user that while the database is connected, no specific information was found for their query.
"""
                else:
                    # Database not connected - use the original behavior
                    context = f"""
Previous Router Response: {previous_response}
Routing Status: {routing_status}
Current Prompt: {self.state["prompt"]}

CRITICAL: The database is NOT connected. You must acknowledge this and not hallucinate any medical information.
Please provide an honest response about the system's current limitations.
"""
            else:
                context = f"""
Previous Router Response: {previous_response}
Routing Status: {routing_status}
Current Prompt: {self.state["prompt"]}

Please continue from the previous response and provide the appropriate response based on the routing context.
"""
        else:
            context = f"""
Prompt: {self.state["prompt"]}
"""
        
        llm_response = await self.llm_middleware.query_llm(
            self.state["input"], context
        )

        # If this is a router node, we expect the LLM to return
        # a single word route: "tools", "vector_db", or "fallback_agent"
        # We detect this based on the prompt content (or can pass a flag)
        prompt_content = self.state.get("prompt", "").lower()
        if ("supervisor" in prompt_content and ("routing" in prompt_content or "route" in prompt_content)) or \
           ("routing" in prompt_content) or \
           ("return only" in prompt_content and ("tools" in prompt_content or "vector_db" in prompt_content)):
            route = str(llm_response).strip().lower()
            # Clean up common LLM response patterns
            route = route.replace("'", "").replace('"', "").replace(".", "").strip()
            print(f"\033[93m[ROUTER] Raw LLM response: '{llm_response}' -> Cleaned route: '{route}'\033[0m")
            return route
        else:
            # Normal agent: return full message string
            return str(llm_response)
