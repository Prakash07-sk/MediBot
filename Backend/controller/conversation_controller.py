from rag_flow.graphs import GraphFlow

class ConversationController:
    def __init__(self):
        self.graph_flow =   GraphFlow()
    async def chat_data(self, payload):
        llm_response = await self.graph_flow.run(payload.query)
        # Return the response directly without additional wrapping
        return llm_response
    
controller = ConversationController()