import chromadb
from utils import config, logger

class ChromaDBConnector:
    def __init__(self, collection_name: str = "medical_docs"):
        try:
            # Try basic connection first
            self.client = chromadb.HttpClient(
                host=config.CHROMADB_HOST, 
                port=config.CHROMADB_PORT
            )
            logger.info(f"[ChromaDBConnector] ChromaDB client created with basic settings")
        except Exception as e:
            try:
                # Try with minimal settings if basic fails
                self.client = chromadb.HttpClient(
                    host=config.CHROMADB_HOST, 
                    port=config.CHROMADB_PORT,
                    settings=chromadb.Settings(
                        anonymized_telemetry=False
                    )
                )
                logger.info(f"[ChromaDBConnector] ChromaDB client created with settings")
            except Exception as e2:
                logger.error(f"[ChromaDBConnector] All connection attempts failed: {e2}")
                logger.warning(f"[ChromaDBConnector] Creating mock client for development")
                self.client = None
                self.collection = None
                return

        self.collection_name = collection_name
        logger.info(f"[ChromaDBConnector] Getting collection: {collection_name}")
        try:
            self.collection = self.get_collection(collection_name)
            logger.info(f"[ChromaDBConnector] Collection '{collection_name}' found successfully")
        except Exception as e:
            logger.warning(f"[ChromaDBConnector] Collection '{collection_name}' not found: {e}")
            logger.info(f"[ChromaDBConnector] Available collections will be checked when needed")
            self.collection = None
        logger.info(f"[ChromaDBConnector] ChromaDBConnector initialized successfully")

    def query(self, query_text: str, n_results: int = 3):
        """Basic query - kept for backward compatibility"""
        if self.collection is None:
            return {"documents": [], "metadatas": [], "ids": [], "distances": []}
        return self.collection.query(query_texts=[query_text], n_results=n_results)

    def hybrid_search(self, query_text: str, n_results: int = 5, alpha: float = 0.7):
        """
        Hybrid search (currently semantic only).
        """
        if self.collection is None:
            return {"documents": [], "metadatas": [], "ids": [], "distances": []}
        logger.info(f"[ChromaDBConnector] Using semantic search only for query: {query_text}")
        return self.collection.query(query_texts=[query_text], n_results=n_results)

    def add(self, documents: list, metadatas: list, ids: list, embeddings: list = None):
        """Add documents to the collection"""
        if self.collection is None:
            logger.error("[ChromaDBConnector] No collection available to add documents.")
            return None
        if embeddings:
            return self.collection.add(documents=documents, metadatas=metadatas, ids=ids, embeddings=embeddings)
        else:
            return self.collection.add(documents=documents, metadatas=metadatas, ids=ids)

    def get_collection(self, name: str):
        """Get a collection by name"""
        if self.client is None:
            return None
        return self.client.get_collection(name)

    def get_client(self):
        """Return the raw ChromaDB client"""
        return self.client

    def get_connection_status(self):
        """Check connection status"""
        if self.client is None:
            return {"connected": False, "error": "ChromaDB client not initialized"}
        try:
            collections = self.client.list_collections()
            available_collections = [col.name for col in collections]
            connected = any(col.name == self.collection_name for col in collections)
            if not connected and available_collections:
                logger.info(f"[ChromaDBConnector] Collection '{self.collection_name}' not found. Available collections: {available_collections}")
                logger.info(f"[ChromaDBConnector] Using available collection: {available_collections[0]}")
                self.collection_name = available_collections[0]
                self.collection = self.get_collection(available_collections[0])
                connected = True
            return {
                "connected": connected, 
                "collections": available_collections,
                "current_collection": self.collection_name if connected else None
            }
        except Exception as e:
            return {"connected": False, "error": str(e)}