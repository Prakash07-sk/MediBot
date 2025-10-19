from rag_flow.graphs import GraphFlow
from utils.logger import logger

class ConversationController:
    """
    Controller class for managing conversation flow using the GraphFlow RAG pipeline.

    This controller initializes a GraphFlow instance and provides an async method
    to process chat data payloads, returning the LLM's response.

    Attributes:
        graph_flow (GraphFlow): The main graph-based workflow for handling conversations.
    """

    def __init__(self):
        """
        Initialize the ConversationController with a GraphFlow instance.
        """
        self.graph_flow = GraphFlow()

    async def chat_data(self, payload):
        """
        Process a chat payload and return the LLM response.

        Args:
            payload: An object containing the user's query and conversation history.

        Returns:
            dict: The response from the LLM, as returned by GraphFlow.run().
        """
        # Pass both query and conversation history to the graph flow
        llm_response = await self.graph_flow.run(
            user_query=payload.query,
            conversation_history=payload.conversation_history
        )
        logger.info(f"LLM Response: {llm_response}")
        return llm_response

# Singleton instance of the ConversationController for use in the application
controller = ConversationController()