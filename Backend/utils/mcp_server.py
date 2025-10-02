import httpx
import json
from typing import Dict, Any, Optional
from .config import config
from .logger import logger


class MCPServer:
    """
    MCP Server class for making HTTP calls to get tool details.
    Handles communication with the MCP server to execute tools.
    """
    
    def __init__(self):
        self.base_url = config.MCP_SERVER_URL
        self.timeout = 30.0
        
    async def call_tool(self, tool_payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Make an HTTP call to the MCP server with the provided tool payload.
        
        Returns:
            Dict[str, Any]: The response from the MCP server
            
        Raises:
            httpx.HTTPError: If the HTTP request fails
            Exception: If there's an error processing the response
        """
        try:
            url = f"{self.base_url}/{tool_payload.get('tool', '')}"
            
            logger.info(f"Making MCP server call to: {url}")
            logger.debug(f"Tool payload: {json.dumps(tool_payload, indent=2)}")
            
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                method = tool_payload.get("method", "POST").upper()
                if method == "GET":
                    response = await client.get(
                        url,
                        params=tool_payload.get("data", {}),
                        headers={
                            "Content-Type": "application/json",
                            "Accept": "application/json"
                        }
                    )
                else:
                    # For POST/PUT/etc, send JSON body
                    response = await client.request(
                        method,
                        url,
                        json=tool_payload,
                        headers={
                            "Content-Type": "application/json",
                            "Accept": "application/json"
                        }
                    )
                
                # Raise an exception for HTTP error status codes
                response.raise_for_status()
                
                # Log the raw response for debugging
                raw_response = response.text
                logger.info(f"MCP server call successful. Status: {response.status_code}")
                logger.debug(f"Raw response: {raw_response}")
                
                # Check if response is empty
                if not raw_response or raw_response.strip() == "":
                    logger.warning("MCP server returned empty response")
                    return {"error": "Empty response from MCP server", "status_code": response.status_code}
                
                # Try to parse JSON response
                try:
                    result = response.json()
                    logger.debug(f"Parsed response: {json.dumps(result, indent=2)}")
                    return result
                except json.JSONDecodeError as json_error:
                    logger.error(f"Response is not valid JSON: {raw_response}")
                    logger.error(f"JSON decode error: {str(json_error)}")
                    return {
                        "error": "Invalid JSON response from MCP server",
                        "raw_response": raw_response,
                        "status_code": response.status_code
                    }
                
        except httpx.HTTPError as e:
            logger.error(f"HTTP error calling MCP server: {str(e)}")
            return {"error": f"HTTP error: {str(e)}", "status_code": getattr(e.response, 'status_code', None) if hasattr(e, 'response') else None}
        except Exception as e:
            logger.error(f"Unexpected error calling MCP server: {str(e)}")
            return {"error": f"Unexpected error: {str(e)}"}
    
    async def get_tool_details(self, tool_name: str, method: str = "GET", 
                             action: str = "list", data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Convenience method to get tool details with simplified parameters.
        
        Args:
            tool_name (str): Name of the tool to call
            method (str): HTTP method (GET, POST, etc.)
            action (str): Action to perform on the tool
            data (Optional[Dict[str, Any]]): Additional data for the tool call
            
        Returns:
            Dict[str, Any]: The response from the MCP server
        """
        payload = {
            "method": method,
            "tool": tool_name,
            "action": action,
            "data": data or {}
        }
        
        return await self.call_tool(payload)
    
    


# Create a singleton instance
mcp_server = MCPServer()
