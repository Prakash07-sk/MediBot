import chromadb
from utils import config

class ChromaDBConnector:
    def __init__(self):
        self.client = chromadb.HttpClient(host=config.CHROMADB_HOST, port=config.CHROMADB_PORT)
        self.collection = self.get_collection("documents")

    def query(self, query_texts: str, n_results: int):
        return self.collection.query(query_texts=[query_texts], n_results=n_results)
    
    def add(self, documents: str, metadatas: dict, ids: str):
        return self.collection.add(documents=documents, metadatas=metadatas, ids=ids)
    
    def get_collection(self, name: str):
        return self.client.get_collection(name)
    
    def get_client(self):
        return self.client
