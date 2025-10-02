from utils import logger
from datetime import datetime
from .vector_db_agent import VectorDBAgent
from .tools_agent import ToolsAgent
from .dynamic_agent import DynamicAgent

class RouterAgent:
    """
    Router agent class that maintains state properly.
    """
    def __init__(self, initial_state: dict):
        self.state = initial_state

    async def generate_response(self):
        """
        Dynamic router function.
        Returns a string route: "tools", "vector_db", or "fallback_agent"
        """
        user_input = self.state.get("input", "")
        node_prompt = self.state.get("prompt", "")
        messages = self.state.get("messages", [])

        # The route decision should already be in the messages from the supervisor agent
        # Look for the route decision in the messages
        route_decision = None
        for message in messages:
            if message.startswith('[supervisor_agent]'):
                route_decision = message.replace('[supervisor_agent]', '').strip()
                break
        
        if not route_decision:
            logger.error("[RouterAgent] No route decision found in messages")
            return "fallback_agent"
        
        
        # Clean up the route decision
        route_decision = str(route_decision).strip().lower()
        route_decision = route_decision.replace("'", "").replace('"', "").replace(".", "").strip()

        if "vector_db" in route_decision:
            try:
                vector_db_agent = VectorDBAgent({
                    "input": user_input,
                    "messages": messages,
                    "prompt": node_prompt
                })
                vector_result = await vector_db_agent.generate_response()
                
                # Store the search results in state["response"] - now it will be preserved!
                self.state["response"] = vector_result
                self.state["routing_status"] = "vector_db_completed"
                return "vector_db_agent"

            except Exception as e:
                import traceback
                self.state["response"] = f"I encountered an error while searching the medical database: {str(e)}. Please try again or rephrase your question."
                self.state["routing_status"] = "vector_db_error"
                return "vector_db_agent"

        elif "tools" in route_decision:
            try:

                # In Python, to mimic JS's {...state, input: user_input}, use dict unpacking:
                tools_agent = ToolsAgent({
                    **self.state,
                    "input": user_input,
                    "messages": messages,
                })

                tools_result = await tools_agent.generate_response()

                print(f"[RouterAgent] Tools agentsswssss: {tools_agent}")

                self.state["response"] = tools_result
                self.state["routing_status"] = "tools_completed"
                return "tools_agent"
            except Exception as e:
                self.state["response"] = f"I encountered an error while processing the request: {str(e)}. Please try again or rephrase your question."
                self.state["routing_status"] = "tools_error"
                return "tools_agent"
        else:
            logger.info(f"[RouterAgent] No specific route matched, returning original route_decision: '{route_decision}'")

        return route_decision

# Keep the function for backward compatibility
async def router_function(state: dict):
    """
    Wrapper function to maintain compatibility with existing code.
    """
    router_agent = RouterAgent(state)
    return await router_agent.generate_response()
