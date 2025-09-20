# RAG_Workflow/Agents/DynamicAgent.py
import asyncio
from utils import config
from utils.tools import execute_tool
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
