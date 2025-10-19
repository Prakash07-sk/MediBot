# Vector Database Agent for ChromaDB Hybrid Search
from database.chromadb_connector import ChromaDBConnector
from utils import logger
from typing import Dict, Any

class VectorDBAgent:
    """
    Specialized agent for handling vector database queries using hybrid search
    """
    
    def __init__(self, initial_state: dict):
        self.state = initial_state
        self.chromadb = ChromaDBConnector()
    
    async def generate_response(self) -> str:
        """
        Generate response using hybrid search on ChromaDB.
        Only return the embedded found queried data, do not call DynamicAgent.
        """
        user_query = self.state.get("input", "")
        logger.info(f"[VectorDBAgent] Processing query: {user_query}")
        
        try:
            logger.info(f"[VectorDBAgent] Checking ChromaDB connection...")
            # Check ChromaDB connection status before proceeding
            db_status = self.chromadb.get_connection_status()
            logger.info(f"[VectorDBAgent] DB Status: {db_status}")
            
            if not db_status.get("connected", False):
                available_collections = db_status.get("collections", [])
                error_msg = db_status.get("error", "Unknown error")
                
                if available_collections:
                    logger.error(f"[VectorDBAgent] ChromaDB connected but collection not found. Available collections: {available_collections}")
                    return (
                        f"I can connect to the medical database, but the expected collection is not available. "
                        f"Available collections: {', '.join(available_collections)}. "
                        f"Please ensure the data ingestion process has completed successfully."
                    )
                else:
                    logger.error(f"[VectorDBAgent] ChromaDB connection failed: {error_msg}")
                    return (
                        "I am unable to access the medical database at the moment. "
                        "The database may not be properly set up or the data ingestion process may not have completed. "
                        "Please try again later or contact support if the issue persists."
                    )
            
            # Perform hybrid search
            logger.info(f"[VectorDBAgent] Performing hybrid search...")
            search_results = self.chromadb.hybrid_search(
                query_text=user_query,
                n_results=5,
                alpha=0.7  # 70% semantic, 30% keyword
            )
            logger.info(f"[VectorDBAgent] Hybrid search completed, got {len(search_results.get('documents', []))} results")
            
            # Extract relevant documents
            documents = search_results.get('documents', [])
            metadatas = search_results.get('metadatas', [])
            
            if not documents:
                return "I couldn't find any relevant information in the medical database for your query. Please try rephrasing your question or ask about a different medical topic."
            
            # Build context from search results and return it directly
            context = self._build_context_from_results(documents, metadatas)
            return context
            
        except Exception as e:
            import traceback
            error_traceback = traceback.format_exc()
            logger.error(f"[VectorDBAgent] Error during search: {str(e)}")
            logger.error(f"[VectorDBAgent] Full traceback: {error_traceback}")
            return f"I encountered an error while searching the medical database: {str(e)}. Please try again or rephrase your question."
    
    def _build_context_from_results(self, documents: list, metadatas: list) -> str:
        """Build context string from search results"""
        context_parts = []
        
        for i, doc in enumerate(documents, 1):
            # Handle metadata - it might be a list or dict depending on ChromaDB version
            metadata = metadatas[i-1] if i-1 < len(metadatas) else {}
            
            # Extract file information safely
            if isinstance(metadata, dict):
                file_name = metadata.get('file_name', f'Document {i}')
                file_type = metadata.get('file_type', 'unknown')
            else:
                file_name = f'Document {i}'
                file_type = 'unknown'
            
            # Truncate document if too long
            doc_preview = doc[:500] + "..." if len(doc) > 500 else doc
            
            context_parts.append(f"""
            Document {i} (Source: {file_name}, Type: {file_type}):
            {doc_preview}
            """)
        
        return "\n".join(context_parts)
    
    def _format_source_info(self, metadatas: list) -> str:
        """Format source information for citation"""
        sources = []
        seen_files = set()
        
        for metadata in metadatas:
            if isinstance(metadata, dict):
                file_name = metadata.get('file_name', 'Unknown')
            else:
                file_name = 'Unknown'
                
            if file_name not in seen_files:
                sources.append(file_name)
                seen_files.add(file_name)
        
        return ", ".join(sources) if sources else ""

# Factory function for creating VectorDBAgent
async def create_vector_db_agent(state: dict) -> str:
    """
    Factory function to create and run VectorDBAgent.
    Only return the embedded found queried data, do not call DynamicAgent.
    """
    agent = VectorDBAgent(state)
    return await agent.generate_response()
