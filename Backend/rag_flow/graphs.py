# RAG_Workflow/graphs.py
from pathlib import Path
import toml
from langgraph.graph import StateGraph
from typing_extensions import TypedDict, Annotated
from operator import add

# Import dynamic agents and router
from .Agents import DynamicAgent, RouterAgent
from utils import config

class GraphState(TypedDict):
    input: str
    messages: Annotated[list, add]
    prompt: str
    response: str
    routing_status: str
    progress_message: str
    conversation_history: list

class GraphFlow:
    def __init__(self, config_path=config.get_agent_prompt()):
        # --- Load config file ---
        if config_path is None:
            config_path = config.get_agent_prompt()
        config_file = Path(config_path)
        if not config_file.exists():
            raise FileNotFoundError(f"Config not found: {config_file}")

        self.config = toml.load(config_file)

        # --- Entry and End nodes dynamically ---
        self.initial_node = self.config.get("flow", {}).get("entry_node")
        self.end_node = self.config.get("flow", {}).get("final_node")
        if not self.initial_node or not self.end_node:
            raise ValueError("flow must define entry_node and final_node")

        # --- Extract agents dynamically ---
        agents_list = self.config.get("agents", [])
        if not agents_list:
            raise ValueError("No agents defined in config")

        self.dynamic_agents = {}
        self.node_prompts = {}
        self.node_types = {}
        for agent in agents_list:
            node_id = agent.get("name")
            role = agent.get("role", "")
            description = agent.get("description", "")
            prompt_text = agent.get("prompt", "")
            prompt = f"Role: {role}\nDescription: {description}\nPrompt: {prompt_text}"
            
            # Enhance supervisor prompt with dynamic routing options
            if node_id == self.initial_node:
                prompt = self._enhance_supervisor_prompt(prompt, agents_list)
            
            self.node_prompts[node_id] = prompt
            # Entry node = router, others = agent
            self.node_types[node_id] = "router" if node_id == self.initial_node else "agent"
            # Initialize DynamicAgent
            self.dynamic_agents[node_id] = DynamicAgent({
                "input": "",
                "messages": [],
                "prompt": prompt
            })

        # --- Extract flow edges dynamically ---
        edges_list = self.config.get("flow", {}).get("edges", [])
        self.edges = []
        if isinstance(edges_list, list):
            for edge in edges_list:
                src, dst = edge.get("from"), edge.get("to")
                if src and dst:
                    self.edges.append((src, dst))

        # --- Initialize StateGraph ---
        self.workflow = StateGraph(GraphState)
        self._build_graph()
        
        # Show dynamic configuration
        self._show_dynamic_configuration()

    def make_router_agent(self):
        """
        Create RouterAgent as a proper node that can update state
        """
        async def router_node(state):
            # Get current messages and input
            messages = list(state.get("messages", []))
            user_input = state.get("input", "")
            
            # Create RouterAgent with state
            router_agent = RouterAgent(state)
            route_decision = await router_agent.generate_response()
            
            # Add the router's response to messages
            messages.append(f"[router_agent] {route_decision}")
            
            return {
                "messages": messages,
                "response": router_agent.state.get("response", ""),  # Get updated response from RouterAgent
                "routing_status": router_agent.state.get("routing_status", ""),
                "progress_message": router_agent.state.get("progress_message", ""),
                "input": user_input,
                "route_decision": route_decision  # Store route decision for conditional edge
            }
        
        return router_node

    def make_agent(self, node_id):
        """
        Wraps each node into a DynamicAgent call or specialized agent
        """
        async def agent(state):
            
            # Get current messages and input
            messages = list(state.get("messages", []))
            user_input = state.get("input", "")
            
            # Update state with node prompt
            node_prompt = self.node_prompts.get(node_id, "")
            
            # Get conversation history from state
            conversation_history = state.get("conversation_history", [])
            
            # For specialized agents (not supervisor), include conversation history in input
            if node_id != self.initial_node and messages:
                # Create context from previous messages for specialized agents
                conversation_context = "\n".join(messages)
                
                # Add formatted conversation history if available
                history_context = ""
                if conversation_history:
                    history_context = f"\n\nPrevious User Conversations:\n" + "\n".join(conversation_history)
                
                agent_input = f"Original Query: {user_input}\n\nConversation History:\n{conversation_context}{history_context}\n\nPlease provide your response based on the above context."
            else:
                # For supervisor, include conversation history in input
                history_context = ""
                if conversation_history:
                    history_context = f"\n\nPrevious User Conversations:\n" + "\n".join(conversation_history)
                agent_input = f"{user_input}{history_context}"
            
            # Preserve existing state values from previous nodes (especially router)
            state_with_prompt = {
                "input": agent_input,
                "messages": messages,
                "prompt": node_prompt,
                "response": state.get("response", ""),  # Preserve router response
                "routing_status": state.get("routing_status", ""),  # Preserve routing status
                "progress_message": state.get("progress_message", ""),  # Preserve progress message
                "conversation_history": conversation_history  # Pass conversation history
            }

            # Process node via DynamicAgent
            dynamic_agent = self.dynamic_agents.get(node_id)
            if dynamic_agent:
                dynamic_agent.state = state_with_prompt
                result = await dynamic_agent.generate_response()
                
                # Add the agent's response to messages
                messages.append(f"[{node_id}] {result}")
                
                
                return {
                    "messages": messages, 
                    "prompt": node_prompt,
                    "response": result,
                    "routing_status": state.get("routing_status", ""),  # Preserve routing status
                    "progress_message": state.get("progress_message", ""),  # Preserve progress message
                    "input": user_input  # Preserve original input
                }
            else:
                messages.append(f"[{node_id}] No DynamicAgent found")
                return {
                    "messages": messages, 
                    "prompt": node_prompt,
                    "response": "",
                    "routing_status": state.get("routing_status", ""),  # Preserve routing status
                    "progress_message": state.get("progress_message", ""),  # Preserve progress message
                    "input": user_input  # Preserve original input
                }

        return agent

    def _enhance_supervisor_prompt(self, base_prompt, agents_list):
        """
        Enhance supervisor prompt with dynamic routing options based on available agents
        """
        # Get all available routing targets
        routing_targets = []
        routing_descriptions = []
        
        for agent in agents_list:
            agent_name = agent.get("name")
            # Skip supervisor and response agents
            if agent_name == self.initial_node or agent_name == self.end_node:
                continue
                
            role = agent.get("role", "")
            description = agent.get("description", "")
            
            # Extract routing keywords
            routing_key = agent_name.lower().replace("_agent", "")
            routing_targets.append(routing_key)
            
            # Create description based on agent role and description
            if description:
                # Extract first line of description for routing guidance
                desc_lines = description.strip().split('\n')
                routing_desc = desc_lines[0] if desc_lines else f"Handle {role} related queries"
                routing_descriptions.append(f"- '{routing_key}' -> {routing_desc}")
        
        # Enhance the base prompt with dynamic routing options
        if routing_targets and routing_descriptions:
            enhanced_prompt = f"""{base_prompt}

DYNAMIC ROUTING OPTIONS (based on available agents):
Return only **one word** from: {', '.join([f"'{target}'" for target in routing_targets])}.
Do NOT include JSON or extra text.

{chr(10).join(routing_descriptions)}

Choose the most appropriate routing option based on the user's query."""
        else:
            enhanced_prompt = base_prompt
        
        return enhanced_prompt

    def _create_dynamic_route_mapping(self):
        """
        Create dynamic route mapping based on available agents in config
        """
        route_mapping = {}
        
        for agent_name in self.dynamic_agents.keys():
            # Skip supervisor and response agents from routing targets
            if agent_name == self.initial_node or agent_name == self.end_node:
                continue
                
            # Extract routing keywords from agent name and role
            agent_config = None
            for agent in self.config.get("agents", []):
                if agent.get("name") == agent_name:
                    agent_config = agent
                    break
            
            if agent_config:
                # Add agent name as routing key
                route_mapping[agent_name.lower()] = agent_name
                
                # Add role-based keywords
                role = agent_config.get("role", "").lower()
                if role:
                    route_mapping[role] = agent_name
                
                # Extract keywords from description
                description = agent_config.get("description", "").lower()
                if "vector" in description or "database" in description:
                    route_mapping["vector_db"] = agent_name
                    route_mapping["database"] = agent_name
                if "tools" in description or "operations" in description:
                    route_mapping["tools"] = agent_name
                    route_mapping["operations"] = agent_name
                if "fallback" in description or "default" in description:
                    route_mapping["fallback"] = agent_name
                    route_mapping["fallback_agent"] = agent_name
        
        return route_mapping

    def _find_fallback_agent(self):
        """
        Dynamically find the fallback agent from available agents
        """
        # Look for agents with 'fallback' in name or role
        for agent_name in self.dynamic_agents.keys():
            if agent_name == self.initial_node or agent_name == self.end_node:
                continue
                
            if "fallback" in agent_name.lower():
                return agent_name
                
            # Check role in config
            for agent in self.config.get("agents", []):
                if agent.get("name") == agent_name:
                    role = agent.get("role", "").lower()
                    description = agent.get("description", "").lower()
                    if "fallback" in role or "fallback" in description:
                        return agent_name
        
        # If no fallback found, return the first non-supervisor, non-response agent
        for agent_name in self.dynamic_agents.keys():
            if agent_name != self.initial_node and agent_name != self.end_node:
                return agent_name
        
        # Last resort - return response agent
        return self.end_node

    def _get_available_routing_targets(self):
        """
        Dynamically get all available routing targets (excluding supervisor and response agents)
        """
        targets = []
        for agent_name in self.dynamic_agents.keys():
            if agent_name != self.initial_node and agent_name != self.end_node:
                targets.append(agent_name)
        
        return targets

    def _show_dynamic_configuration(self):
        """
        Display the current dynamic configuration for debugging
        """
        pass

    def _build_graph(self):
        """
        Build a simple linear graph with conditional routing
        """
        # --- Add all nodes ---
        for node_id in self.dynamic_agents.keys():
            self.workflow.add_node(node_id, self.make_agent(node_id))
        
        # --- Add RouterAgent as a proper node ---
        self.workflow.add_node("router_agent", self.make_router_agent())

        # --- Use the route decision from the router node ---
        async def route_to_agent(state):
            """Route using the route decision from the router node"""
            
            try:
                # Get route decision from the router node
                route_decision = state.get("route_decision", "")
                route_decision = str(route_decision).strip().lower()
                
                
                # Dynamically create route mapping based on available agents
                route_mapping = self._create_dynamic_route_mapping()
                
                # Clean up the route decision and find matching agent
                next_node = self._find_fallback_agent()  # dynamic fallback
                for key, agent in route_mapping.items():
                    if key in route_decision:
                        next_node = agent
                        break
                
                return next_node
                
            except Exception as e:
                fallback_agent = self._find_fallback_agent()
                return fallback_agent

        # --- Set up the flow: supervisor -> router_agent -> specialized agents -> response ---
        # Get available routing targets dynamically
        available_targets = self._get_available_routing_targets()
        
        # Create route map dynamically
        route_map = {}
        for agent_name in available_targets:
            route_map[agent_name] = agent_name

        # Add edge from supervisor to router_agent
        self.workflow.add_edge(self.initial_node, "router_agent")
        
        # Add conditional edges from router_agent to specialized agents
        if available_targets:
            self.workflow.add_conditional_edges(
                "router_agent",
                route_to_agent,
                route_map
            )

        # --- Connect all specialized agents directly to response_agent ---
        for agent_name in available_targets:
            if agent_name != self.end_node:
                self.workflow.add_edge(agent_name, self.end_node)

        # --- Set entry and finish nodes ---
        self.workflow.set_entry_point(self.initial_node)
        self.workflow.set_finish_point(self.end_node)

        # --- Compile workflow ---
        self.app = self.workflow.compile()

    async def run(self, user_query: str, conversation_history: list = None):
        """
        Execute the graph with a given user query and conversation history
        
        Args:
            user_query: The current user's query
            conversation_history: List of previous conversation entries (role, content)
        """
        initial_prompt = self.node_prompts.get(self.initial_node, "")
        
        # Format conversation history for context
        formatted_history = []
        if conversation_history:
            for entry in conversation_history:
                # Access Pydantic model attributes directly
                role = entry.role if hasattr(entry, 'role') else ""
                content = entry.content if hasattr(entry, 'content') else ""
                formatted_history.append(f"{role}: {content}")
        
        state = {
            "input": user_query,
            "messages": [],
            "prompt": initial_prompt,
            "response": "",
            "routing_status": "",
            "progress_message": "",
            "conversation_history": formatted_history
        }

        result = await self.app.ainvoke(state)
        
        # Extract only the final response from response_agent
        messages = result.get("messages", [])
        final_response = None
        
        # Find the last response_agent message
        for msg in reversed(messages):
            if f"[{self.end_node}]" in msg:
                final_response = msg.split(f"[{self.end_node}] ", 1)[-1].strip()
                break
        
        if final_response:
            return {
                "response": final_response
            }
        else:
            # Fallback if no response_agent message found
            return {
                "response": result.get("response", "No response generated")
            }
