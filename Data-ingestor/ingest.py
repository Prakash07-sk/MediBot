# ingest.py
# Multi-format document ingestion script for ChromaDB
# Supports: TXT, DOCX, DOC, PDF, XLSX, XLS, PPTX, PPT files
# Features: File-type-specific chunking, enhanced metadata, error handling
import os
import time
import chromadb
from langchain_community.document_loaders import (
    DirectoryLoader, 
    TextLoader, 
    PyPDFLoader
)
from langchain_community.document_loaders.word_document import Docx2txtLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from pathlib import Path

# --- Config from env ---
CHROMA_HOST = os.getenv("CHROMADB_HOST", "localhost")
CHROMA_PORT = int(os.getenv("CHROMADB_PORT", 5000))
COLLECTION_NAME = os.getenv("CHROMADB_COLLECTION", "medical_docs")

# Try multiple possible data directory paths
POSSIBLE_DATA_DIRS = [
    "./data",
    "/app/data", 
    "data",
    os.path.join(os.path.dirname(__file__), "data")
]

# Find the correct data directory
DATA_DIR = None
for possible_dir in POSSIBLE_DATA_DIRS:
    if os.path.exists(possible_dir):
        DATA_DIR = possible_dir
        break

if DATA_DIR is None:
    print("❌ Could not find data directory. Tried:")
    for dir_path in POSSIBLE_DATA_DIRS:
        print(f"   - {dir_path}")
    print("Current working directory:", os.getcwd())
    print("Script location:", __file__)
    raise FileNotFoundError("Data directory not found")

print(f"📁 Using data directory: {DATA_DIR}")

# Test if we can access the files
test_files = list(Path(DATA_DIR).glob("*"))
print(f"🔍 Test - Files in data directory: {[str(f) for f in test_files]}")

# --- File type mapping ---
# Using lightweight loaders that don't require heavy ML dependencies
FILE_LOADERS = {
    '.txt': TextLoader,
    '.docx': Docx2txtLoader,
    '.doc': Docx2txtLoader,  # Note: .doc files may need conversion to .docx
    '.pdf': PyPDFLoader,
    # Note: Excel and PowerPoint loaders removed to avoid heavy dependencies
    # You can add them back if needed, but they may pull in heavy ML libraries
}

def get_loader_for_file(file_path):
    """Get the appropriate loader for a file based on its extension."""
    file_ext = Path(file_path).suffix.lower()
    return FILE_LOADERS.get(file_ext, TextLoader)

def load_documents_from_directory(directory):
    """Load all supported documents from a directory."""
    all_docs = []
    directory_path = Path(directory)
    
    print(f"🔍 Looking for files in: {directory_path.absolute()}")
    
    if not directory_path.exists():
        print(f"⚠️ Directory {directory} does not exist")
        return all_docs
    
    # List all files in directory for debugging
    all_files = list(directory_path.glob("**/*"))
    print(f"📂 All files in directory: {[str(f) for f in all_files]}")
    
    # Get all files with supported extensions
    supported_extensions = list(FILE_LOADERS.keys())
    print(f"🔍 Looking for extensions: {supported_extensions}")
    
    files = []
    for ext in supported_extensions:
        found_files = list(directory_path.glob(f"**/*{ext}"))
        files.extend(found_files)
        print(f"   {ext}: {[str(f) for f in found_files]}")
    
    print(f"📁 Found {len(files)} supported files: {[str(f) for f in files]}")
    
    for file_path in files:
        try:
            loader_class = get_loader_for_file(file_path)
            print(f"📄 Loading {file_path} with {loader_class.__name__}")
            
            # Load the document
            loader = loader_class(str(file_path))
            docs = loader.load()
            all_docs.extend(docs)
            
        except Exception as e:
            print(f"❌ Error loading {file_path}: {e}")
            continue
    
    return all_docs

# --- Wait for ChromaDB to be ready ---
def wait_for_chroma(max_retries=10, delay=3):
    for attempt in range(max_retries):
        try:
            # Try with basic settings first
            client = chromadb.HttpClient(host=CHROMA_HOST, port=CHROMA_PORT)
            client.list_collections()  # test connection
            print("✅ Connected to ChromaDB")
            return client
        except Exception as e:
            # If basic connection fails, try with settings
            try:
                client = chromadb.HttpClient(
                    host=CHROMA_HOST, 
                    port=CHROMA_PORT,
                    settings=chromadb.Settings(
                        anonymized_telemetry=False
                    )
                )
                client.list_collections()  # test connection
                print("✅ Connected to ChromaDB with settings")
                return client
            except Exception as e2:
                print(f"⚠️ Chroma not ready (attempt {attempt+1}/{max_retries}): {e2}")
                time.sleep(delay)
    raise RuntimeError("❌ Could not connect to ChromaDB after retries")

# --- Connect ---
client = wait_for_chroma()

# --- Create or get collection ---
if COLLECTION_NAME not in [c.name for c in client.list_collections()]:
    collection = client.create_collection(COLLECTION_NAME)
else:
    collection = client.get_collection(COLLECTION_NAME)

# --- Load all supported document types ---
docs = load_documents_from_directory(DATA_DIR)
print(f"📄 Loaded {len(docs)} documents from all supported file types")

# --- Split documents into chunks ---
# Configure chunking based on file type for better results
def get_chunking_config(file_path):
    """Get chunking configuration based on file type."""
    file_ext = Path(file_path).suffix.lower()
    
    if file_ext in ['.pdf']:
        # PDFs often have structured content, smaller chunks
        return {"chunk_size": 400, "chunk_overlap": 50}
    elif file_ext in ['.docx', '.doc']:
        # Word documents may have mixed content, medium chunks
        return {"chunk_size": 600, "chunk_overlap": 75}
    else:
        # Default for text files
        return {"chunk_size": 500, "chunk_overlap": 50}

# Split documents with file-type-specific chunking
texts = []
for doc in docs:
    source_path = doc.metadata.get("source", "")
    chunk_config = get_chunking_config(source_path)
    
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_config["chunk_size"],
        chunk_overlap=chunk_config["chunk_overlap"],
        length_function=len,
        separators=["\n\n", "\n", " ", ""]
    )
    
    doc_chunks = splitter.split_documents([doc])
    texts.extend(doc_chunks)

print(f"✂️ Split into {len(texts)} chunks with file-type-specific configurations")

# --- Embeddings ---
# Use ChromaDB's default embedding function (much lighter than sentence-transformers)
# ChromaDB will automatically generate embeddings if we don't provide them
# This is the most lightweight approach

# --- Insert into ChromaDB ---
for i, doc in enumerate(texts):
    source_path = doc.metadata.get("source", "unknown")
    file_ext = Path(source_path).suffix.lower()
    file_type = file_ext[1:] if file_ext else "unknown"
    
    # Enhanced metadata
    metadata = {
        "source": source_path,
        "file_type": file_type,
        "file_name": Path(source_path).name,
        "chunk_index": i
    }
    
    # Add any additional metadata from the original document
    if hasattr(doc, 'metadata'):
        metadata.update(doc.metadata)
    
    collection.add(
        ids=[f"doc_{i}"],
        documents=[doc.page_content],
        metadatas=[metadata]
        # Note: ChromaDB will automatically generate embeddings using its default embedding function
        # This is much more lightweight than sentence-transformers
    )

print(f"✅ Ingested {len(texts)} chunks into ChromaDB collection '{COLLECTION_NAME}'")
