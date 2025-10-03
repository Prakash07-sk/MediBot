# RAG_Workflow/Agents/DynamicAgent.py
import asyncio
from utils import logger
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
        
        # Build context with previous response if available

        # Print the prompt in green color
        context = f"""
            Prompt: {self.state["prompt"]}
            Response: {self.state["response"]}
            """
                
        llm_response = await self.llm_middleware.query_llm(
            self.state["input"], context
        )
        self.state["response"] = llm_response
        return llm_response