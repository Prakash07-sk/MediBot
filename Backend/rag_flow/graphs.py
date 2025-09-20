# RAG_Workflow/graphs.py
from pathlib import Path
import toml
from langgraph.graph import StateGraph
from typing_extensions import TypedDict, Annotated
from operator import add

# Import dynamic agents and router
from .Agents import DynamicAgent, router_function
from utils import config

class GraphState(TypedDict):
    input: str
    messages: Annotated[list, add]
    prompt: str
    response: str
    routing_status: str
    progress_message: str

class GraphFlow:
    def __init__(self, config_path=config.get_agent_prompt()):
        # --- Load config file ---
        if config_path is None:
            config_path = config.get_agent_prompt()
        print(f"\033[92m The config path is: {config_path}\033[0m")
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
            prompt = agent.get("prompt", "")
            
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

    def make_agent(self, node_id):
        """
        Wraps each node into a DynamicAgent call
        """
        async def agent(state):
            print(f"\033[94m[AGENT] Processing node: {node_id}\033[0m")
            
            # Get current messages and input
            messages = list(state.get("messages", []))
            user_input = state.get("input", "")
            
            # Update state with node prompt
            node_prompt = self.node_prompts.get(node_id, "")
            
            # For specialized agents (not supervisor), include conversation history in input
            if node_id != self.initial_node and messages:
                # Create context from previous messages for specialized agents
                conversation_context = "\n".join(messages)
                agent_input = f"Original Query: {user_input}\n\nConversation History:\n{conversation_context}\n\nPlease provide your response based on the above context."
            else:
                # For supervisor, use original input
                agent_input = user_input
            
            # Preserve existing state values from previous nodes (especially router)
            state_with_prompt = {
                "input": agent_input,
                "messages": messages,
                "prompt": node_prompt,
                "response": state.get("response", ""),  # Preserve router response
                "routing_status": state.get("routing_status", ""),  # Preserve routing status
                "progress_message": state.get("progress_message", "")  # Preserve progress message
            }

            # Process node via DynamicAgent
            dynamic_agent = self.dynamic_agents.get(node_id)
            if dynamic_agent:
                dynamic_agent.state = state_with_prompt
                result = await dynamic_agent.generate_response()
                
                # Add the agent's response to messages
                messages.append(f"[{node_id}] {result}")
                
                print(f"\033[94m[AGENT] {node_id} completed with result: {result[:100]}...\033[0m")
                
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
        
        print(f"\033[96m[DYNAMIC_PROMPT] Enhanced supervisor prompt with {len(routing_targets)} routing options\033[0m")
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
        
        print(f"\033[95m[DYNAMIC_MAPPING] Created route mapping: {route_mapping}\033[0m")
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
                print(f"\033[93m[FALLBACK] No dedicated fallback found, using: {agent_name}\033[0m")
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
        
        print(f"\033[95m[TARGETS] Available routing targets: {targets}\033[0m")
        return targets

    def _show_dynamic_configuration(self):
        """
        Display the current dynamic configuration for debugging
        """
        print(f"\033[96m" + "="*60 + "\033[0m")
        print(f"\033[96m[DYNAMIC CONFIG] GraphFlow Configuration Summary\033[0m")
        print(f"\033[96m" + "="*60 + "\033[0m")
        
        print(f"\033[93m[FLOW] Entry Node: {self.initial_node}\033[0m")
        print(f"\033[93m[FLOW] Final Node: {self.end_node}\033[0m")
        
        print(f"\033[94m[AGENTS] Total Agents: {len(self.dynamic_agents)}\033[0m")
        for agent_name in self.dynamic_agents.keys():
            agent_type = "SUPERVISOR" if agent_name == self.initial_node else "RESPONSE" if agent_name == self.end_node else "ROUTING_TARGET"
            print(f"\033[94m  - {agent_name} ({agent_type})\033[0m")
        
        # Show routing mapping
        route_mapping = self._create_dynamic_route_mapping()
        print(f"\033[95m[ROUTING] Dynamic Route Mapping:\033[0m")
        for key, target in route_mapping.items():
            print(f"\033[95m  - '{key}' -> {target}\033[0m")
        
        fallback = self._find_fallback_agent()
        print(f"\033[93m[FALLBACK] Default Fallback Agent: {fallback}\033[0m")
        
        print(f"\033[96m" + "="*60 + "\033[0m")

    def _build_graph(self):
        """
        Build a simple linear graph with conditional routing
        """
        # --- Add all nodes ---
        for node_id in self.dynamic_agents.keys():
            self.workflow.add_node(node_id, self.make_agent(node_id))
            print(f"\033[93m[NODE] Added node: {node_id}\033[0m")

        # --- Use the dedicated router_function for routing decisions ---
        async def route_to_agent(state):
            """Route using the dedicated router_function from router_agent.py"""
            
            # Prepare state for router_function
            router_state = {
                "input": state.get("input", ""),
                "messages": state.get("messages", []),
                "prompt": self.node_prompts.get(self.initial_node, "")
            }
            
            try:
                # Call the router_function to get routing decision
                route_decision = await router_function(router_state)
                route_decision = str(route_decision).strip().lower()
                
                print(f"\033[92m[ROUTER] Router function raw decision: '{route_decision}'\033[0m")
                
                # Dynamically create route mapping based on available agents
                route_mapping = self._create_dynamic_route_mapping()
                
                # Clean up the route decision and find matching agent
                next_node = self._find_fallback_agent()  # dynamic fallback
                for key, agent in route_mapping.items():
                    if key in route_decision:
                        next_node = agent
                        break
                
                print(f"\033[92m[ROUTER] Final routing decision: '{route_decision}' -> routing to: '{next_node}'\033[0m")
                return next_node
                
            except Exception as e:
                fallback_agent = self._find_fallback_agent()
                print(f"\033[91m[ROUTER ERROR] Router function failed: {e}, defaulting to {fallback_agent}\033[0m")
                return fallback_agent

        # --- Set up the flow: supervisor -> router_function -> specialized agents -> response ---
        # Get available routing targets dynamically
        available_targets = self._get_available_routing_targets()
        
        # Create route map dynamically
        route_map = {}
        for agent_name in available_targets:
            route_map[agent_name] = agent_name

        # Add conditional edges from supervisor using router_function
        if available_targets:
            self.workflow.add_conditional_edges(
                self.initial_node,
                route_to_agent,
                route_map
            )
            print(f"\033[95m[ROUTING] Added conditional routing from {self.initial_node} to: {available_targets}\033[0m")

        # --- Connect all specialized agents directly to response_agent ---
        for agent_name in available_targets:
            if agent_name != self.end_node:
                self.workflow.add_edge(agent_name, self.end_node)
                print(f"\033[95m[EDGE] Added edge: {agent_name} -> {self.end_node}\033[0m")

        # --- Set entry and finish nodes ---
        self.workflow.set_entry_point(self.initial_node)
        self.workflow.set_finish_point(self.end_node)

        # --- Compile workflow ---
        self.app = self.workflow.compile()

    async def run(self, user_query: str):
        """
        Execute the graph with a given user query and return only the final response
        """
        initial_prompt = self.node_prompts.get(self.initial_node, "")
        state = {
            "input": user_query,
            "messages": [],
            "prompt": initial_prompt,
            "response": "",
            "routing_status": "",
            "progress_message": ""
        }

        print(f"\033[96m[WORKFLOW] Starting execution with query: '{user_query}'\033[0m")
        result = await self.app.ainvoke(state)
        print(f"\033[96m[WORKFLOW] Execution completed\033[0m")
        
        # Extract only the final response from response_agent
        messages = result.get("messages", [])
        final_response = None
        
        # Find the last response_agent message
        for msg in reversed(messages):
            if f"[{self.end_node}]" in msg:
                final_response = msg.split(f"[{self.end_node}] ", 1)[-1].strip()
                break
        
        if final_response:
            print(f"\033[96m[FINAL] Returning final response: {final_response[:100]}...\033[0m")
            return {
                "response": final_response,
                "routing_status": result.get("routing_status", ""),
                "progress_message": result.get("progress_message", "")
            }
        else:
            # Fallback if no response_agent message found
            print(f"\033[91m[ERROR] No final response found, returning full result\033[0m")
            return {
                "response": result.get("response", "No response generated"),
                "routing_status": result.get("routing_status", ""),
                "progress_message": result.get("progress_message", "")
            }
