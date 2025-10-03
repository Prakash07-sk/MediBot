
from utils.logger import logger
from .dynamic_agent import DynamicAgent
from utils import config, json_parser, mcp_server
import toml
from datetime import datetime

class ToolsAgent:
    def __init__(self, initial_state: dict):
        self.state = {
            **initial_state,
            "prompt": self.generate_tools_prompt()
        }

        self.dynamic_agent = DynamicAgent(self.state)

    async def generate_response(self) -> dict:
        """
        Generate response using LLM with tools processing
        Returns a dictionary with the parsed tool payloadz̄
        """

        try:
            # Get the raw response from the LLM
            raw_response = await self.dynamic_agent.generate_response()
            print(f"[ToolsAgent] raw_response: {raw_response} (type: {type(raw_response)})")
            
            # Parse the JSON from the response using the JSON parser
            parsed_payload = json_parser.parse_tool_payload(raw_response)
            print(f"[ToolsAgent] parsed_payload: {parsed_payload} (type: {type(parsed_payload)})")
            
            # Call MCP server with the parsed payload
            mcp_response = await self.connect_mcp_server(parsed_payload)
            
            return mcp_response

        except Exception as e:
            logger.error(f"[ToolsAgent] Error: {str(e)}")
            return {"error": f"Error processing tools request: {str(e)}"}

    def generate_tools_prompt(self):

        # Read the tools.poml file to get the tools_payload
        tools_path = config.get_tools()
        # Load the agent prompt and extract only the tools_agent section


        agent_prompt_path = config.get_agent_prompt()
        with open(agent_prompt_path, "r", encoding="utf-8") as f:
            agent_prompt_data = f.read()

        # Parse the POML (TOML) file to extract only the tools_agent data
        parsed = toml.loads(agent_prompt_data)
        tools_prompt = ""
        for agent in parsed.get("agents", []):
            if agent.get("name") == "mcp_payload_agent":
                tools_prompt = agent.get("prompt", "")
                break
        with open(tools_path, "r", encoding="utf-8") as f:
            tools_payload = f.read()
        prompt = f"""
        {tools_prompt}
        current_date = {datetime.now().strftime("%Y-%m-%d")}
        current_time = {datetime.now().strftime("%H:%M:%S")}
        available_tools = {tools_payload}
        """
        return prompt

    async def connect_mcp_server(self, tool_payload: dict):
        return await mcp_server.call_tool(tool_payload)