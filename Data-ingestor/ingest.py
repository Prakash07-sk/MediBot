# ingest.py
# Fully generic ingestion and semantic chunking for ChromaDB

import os
import time
from pathlib import Path
import chromadb
from langchain.text_splitter import RecursiveCharacterTextSplitter

# Document loaders
from langchain_community.document_loaders import TextLoader, PyPDFLoader
from langchain_community.document_loaders.word_document import Docx2txtLoader
from unstructured.partition.auto import partition

# Optional OCR support (for images)
# pip install pillow pytesseract
# from unstructured.partition.image import partition_image

# --- Config ---
CHROMA_HOST = os.getenv("CHROMADB_HOST", "localhost")
CHROMA_PORT = int(os.getenv("CHROMADB_PORT", 5000))
COLLECTION_NAME = os.getenv("CHROMADB_COLLECTION", "medical_docs")

# --- Find data directory ---
POSSIBLE_DATA_DIRS = [
    "./data",
    "/app/data",
    "data",
    os.path.join(os.path.dirname(__file__), "data")
]

DATA_DIR = None
for possible_dir in POSSIBLE_DATA_DIRS:
    if os.path.exists(possible_dir):
        DATA_DIR = possible_dir
        break

if DATA_DIR is None:
    raise FileNotFoundError("Data directory not found")

print(f"📁 Using data directory: {DATA_DIR}")

# --- Generic text extraction ---
def extract_text_generic(file_path: Path):
    if file_path.name.startswith("."):
        return ""  # skip hidden/system files

    text = ""
    try:
        # Try unstructured first
        elements = partition(filename=str(file_path))
        text = "\n".join([el.text for el in elements if hasattr(el, "text") and el.text.strip()])
        if text:
            return text
    except Exception:
        pass  # fallback

    # Fallback loaders by extension
    ext = file_path.suffix.lower()
    try:
        if ext == ".txt":
            loader = TextLoader(str(file_path))
            docs = loader.load()
            text = "\n".join([d.page_content for d in docs])
        elif ext == ".pdf":
            loader = PyPDFLoader(str(file_path))
            docs = loader.load()
            text = "\n".join([d.page_content for d in docs])
        elif ext in [".docx", ".doc"]:
            loader = Docx2txtLoader(str(file_path))
            docs = loader.load()
            text = "\n".join([d.page_content for d in docs])
        else:
            print(f"⚠️ Skipping unsupported format: {file_path}")
            text = ""
    except Exception as e:
        print(f"❌ Failed fallback loader for {file_path}: {e}")
        text = ""

    return text

def load_documents_from_directory(directory):
    all_docs = []
    for file_path in Path(directory).glob("**/*"):
        if not file_path.is_file() or file_path.name.startswith("."):
            continue

        text = extract_text_generic(file_path)
        if text:
            all_docs.append({
                "page_content": text,
                "metadata": {
                    "source": str(file_path),
                    "file_name": file_path.name,
                    "file_type": file_path.suffix.lower().lstrip(".") or "unknown",
                }
            })

    print(f"📄 Loaded {len(all_docs)} raw documents")
    return all_docs

# --- Connect to ChromaDB ---
def wait_for_chroma(max_retries=10, delay=3):
    for attempt in range(max_retries):
        try:
            client = chromadb.HttpClient(host=CHROMA_HOST, port=CHROMA_PORT)
            client.list_collections()
            print("✅ Connected to ChromaDB")
            return client
        except Exception:
            try:
                client = chromadb.HttpClient(
                    host=CHROMA_HOST,
                    port=CHROMA_PORT,
                    settings=chromadb.Settings(anonymized_telemetry=False)
                )
                client.list_collections()
                print("✅ Connected to ChromaDB with settings")
                return client
            except Exception as e2:
                print(f"⚠️ Chroma not ready (attempt {attempt+1}/{max_retries}): {e2}")
                time.sleep(delay)
    raise RuntimeError("❌ Could not connect to ChromaDB")

client = wait_for_chroma()

# --- Create or get collection ---
existing = [c.name for c in client.list_collections()]
if COLLECTION_NAME not in existing:
    collection = client.create_collection(COLLECTION_NAME)
else:
    collection = client.get_collection(COLLECTION_NAME)

# --- Load documents ---
raw_docs = load_documents_from_directory(DATA_DIR)

# --- Chunk intelligently ---
splitter = RecursiveCharacterTextSplitter(
    chunk_size=350,  # tune based on typical document length
    chunk_overlap=50,
    separators=["\n## ", "\n\n", "\n", " "]
)

chunks = []
for doc in raw_docs:
    pieces = splitter.split_text(doc["page_content"])
    for idx, piece in enumerate(pieces):
        metadata = {**doc["metadata"], "chunk_index": idx}
        chunks.append({"page_content": piece, "metadata": metadata})

print(f"✂️ Total chunks: {len(chunks)}")

# --- Insert into ChromaDB ---
for i, chunk in enumerate(chunks):
    collection.add(
        ids=[f"doc_{i}"],
        documents=[chunk["page_content"]],
        metadatas=[chunk["metadata"]]
    )

print(f"✅ Ingested {len(chunks)} chunks into '{COLLECTION_NAME}'")
