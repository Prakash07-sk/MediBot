import litellm

from utils import config, logger


class LLM_Middleware:
    def __init__(self):
        self.model = config.LLM_SERVER_MODEL
        self.openai_api_key = config.openai_api_key
    
    async def query_llm(self, user_message: str, prompt: str):
        """
        Calls LiteLLM to handle multiple providers (OpenAI, Anthropic, etc.)
        """
        
        # If no API key, return a mock response for testing
        if not self.openai_api_key:
            logger.error("OpenAI API key is not set")
            raise Exception("OpenAI API key is not set")


        try:
            # Example with OpenAI model from env
            response = await litellm.acompletion(
                api_key=self.openai_api_key,
                model=self.model,
                temperature=0.2,
                messages=[
                    {"role": "system", "content": prompt},
                    {"role": "user", "content": user_message}
                ],
                functions = [] , # TODO: Load tools from config
                drop_params=True
            )

            # Example: If response includes tool call
            if "function_call" in response.get("choices", [{}])[0]["message"]:
                fn_call = response["choices"][0]["message"]["function_call"]
                return {"tool": {"name": fn_call["name"], "arguments": fn_call["arguments"]}}

            else:
                return response["choices"][0]["message"]["content"]
                
        except Exception as e:
            # Return error message if LLM call fails
            logger.error(f"Error calling LLM: {str(e)}")
            return f"Error calling LLM: {str(e)}"
    
llm_middleware = LLM_Middleware()