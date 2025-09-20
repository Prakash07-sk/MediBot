from rag_flow.graphs import GraphFlow
from utils.logger import logger
class ConversationController:
    def __init__(self):
        self.graph_flow =   GraphFlow()
    async def chat_data(self, payload):
        llm_response = await self.graph_flow.run(payload.query)
        logger.info(f"LLM Response: {llm_response}")
        return llm_response
    
controller = ConversationController()