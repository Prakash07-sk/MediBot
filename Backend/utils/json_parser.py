import json
import re
from typing import Dict, Any
from .logger import logger


class JSONParser:
    """
    Utility class for parsing JSON from LLM responses.
    Handles various response formats and extracts clean JSON objects.
    """
    
    @staticmethod
    def clean_json_string(json_str: str) -> str:
        """
        Clean up JSON string to handle common issues like escaped underscores.
        
        Args:
            json_str (str): Raw JSON string
            
        Returns:
            str: Cleaned JSON string
        """
        # Fix escaped underscores in the JSON string
        json_str = json_str.replace('\\_', '_')
        
        # Remove any trailing whitespace
        json_str = json_str.strip()
        
        return json_str
    
    @staticmethod
    def parse_tool_payload(raw_response: str) -> Dict[str, Any]:
        """
        Parse the tool payload from the LLM response.
        Extracts JSON from the response, handling cases where the LLM adds explanations.
        
        Args:
            raw_response (str): Raw response from the LLM
            
        Returns:
            Dict[str, Any]: Parsed tool payload
        """
        try:
            if isinstance(raw_response, str):
                # Clean the response
                cleaned_response = raw_response.strip()
                
                # Method 1: Try to find the first complete JSON object by counting braces
                start_idx = cleaned_response.find('{')
                if start_idx != -1:
                    # Find the matching closing brace
                    brace_count = 0
                    end_idx = start_idx
                    
                    for i, char in enumerate(cleaned_response[start_idx:], start_idx):
                        if char == '{':
                            brace_count += 1
                        elif char == '}':
                            brace_count -= 1
                            if brace_count == 0:
                                end_idx = i + 1
                                break
                    
                    if brace_count == 0:  # Found complete JSON object
                        json_str = cleaned_response[start_idx:end_idx]
                        # Clean up the JSON string
                        json_str = JSONParser.clean_json_string(json_str)
                        logger.info(f"Extracted JSON string: {json_str}")
                        return json.loads(json_str)
                
                # Method 2: Try to split on common patterns that indicate end of JSON
                # Look for patterns like "Note:", "Explanation:", code blocks, etc.
                split_patterns = [
                    r'\n\s*Note:',
                    r'\n\s*Explanation:',
                    r'\n\s*The above',
                    r'\n\s*This response',
                    r'\n\s*If not',
                    r'\n\s*```',  # Code blocks
                    r'\n\s*The user query',
                    r'\n\s*We determine',
                ]
                
                for pattern in split_patterns:
                    parts = re.split(pattern, cleaned_response, flags=re.IGNORECASE)
                    if len(parts) > 1:
                        json_part = parts[0].strip()
                        if json_part.startswith('{') and json_part.endswith('}'):
                            # Clean up the JSON string
                            json_part = JSONParser.clean_json_string(json_part)
                            logger.info(f"Split-based extraction: {json_part}")
                            return json.loads(json_part)
                
                # Method 3: Try to parse the entire response
                return json.loads(cleaned_response)
            
            elif isinstance(raw_response, dict):
                return raw_response
            else:
                raise ValueError(f"Unexpected response type: {type(raw_response)}")
                
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON from response: {raw_response}")
            logger.error(f"JSON decode error: {str(e)}")
            
            # Try multiple extraction patterns
            patterns = [
                r'```json\s*(\{.*?\})\s*```',  # JSON in code blocks
                r'```\s*(\{.*?\})\s*```',     # JSON in generic code blocks
                r'(\{[^{}]*"method"[^{}]*\})', # Look for JSON with method field
                r'(\{.*?"method".*?\})',       # More flexible method field search
                r'(\{[^}]*"tool"[^}]*\})',    # Look for JSON with tool field
            ]
            
            for pattern in patterns:
                match = re.search(pattern, raw_response, re.DOTALL)
                if match:
                    try:
                        json_str = match.group(1)
                        # Clean up the JSON string
                        json_str = JSONParser.clean_json_string(json_str)
                        logger.info(f"Pattern match found: {json_str}")
                        return json.loads(json_str)
                    except json.JSONDecodeError:
                        continue
            
            # If all parsing attempts fail, return a default error payload
            return {
                "error": "Failed to parse tool payload from LLM response",
                "raw_response": raw_response
            }
        
        except Exception as e:
            logger.error(f"Unexpected error parsing tool payload: {str(e)}")
            return {
                "error": f"Unexpected error parsing tool payload: {str(e)}",
                "raw_response": raw_response
            }
    
    @staticmethod
    def extract_json_from_response(response: str) -> Dict[str, Any]:
        """
        Extract JSON from a response string using multiple methods.
        
        Args:
            response (str): Response string that may contain JSON
            
        Returns:
            Dict[str, Any]: Extracted JSON as dictionary
        """
        return JSONParser.parse_tool_payload(response)
    
    @staticmethod
    def is_valid_json(json_str: str) -> bool:
        """
        Check if a string is valid JSON.
        
        Args:
            json_str (str): String to validate
            
        Returns:
            bool: True if valid JSON, False otherwise
        """
        try:
            json.loads(json_str)
            return True
        except (json.JSONDecodeError, TypeError):
            return False


# Create a singleton instance for easy importing
json_parser = JSONParser()
