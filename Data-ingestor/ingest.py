# ingest.py
# Fully generic ingestion and semantic chunking for ChromaDB
# Version: 2.0 - Enhanced OCR and format support

import os
import time
from pathlib import Path
import chromadb
from langchain.text_splitter import RecursiveCharacterTextSplitter

# Document loaders
from langchain_community.document_loaders import TextLoader, PyPDFLoader
from langchain_community.document_loaders.word_document import Docx2txtLoader
from unstructured.partition.auto import partition

# OCR support for images and other formats
# pip install pillow pytesseract pdf2image
try:
    from PIL import Image
    import pytesseract
    OCR_AVAILABLE = True
    print("✅ OCR support enabled")
except ImportError as e:
    OCR_AVAILABLE = False
    print(f"⚠️ OCR support not available: {e}")
    print("💡 Install with: pip install pillow pytesseract pdf2image")

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

print("🚀 MediBot Data Ingestor v2.0 - Enhanced OCR and Format Support")
print(f"📁 Using data directory: {DATA_DIR}")

# --- Generic text extraction ---
def extract_text_generic(file_path: Path):
    if file_path.name.startswith("."):
        return ""  # skip hidden/system files

    print(f"🔍 Processing {file_path.name}...")
    text = ""
    
    # Method 1: Try unstructured partition (handles most formats including images)
    try:
        print(f"  📋 Trying unstructured partition for {file_path.name}")
        elements = partition(filename=str(file_path))
        text = "\n".join([el.text for el in elements if hasattr(el, "text") and el.text.strip()])
        if text:
            print(f"✅ Extracted text from {file_path.name} using unstructured partition")
            return text
        else:
            print(f"  ⚠️ Unstructured partition returned empty text for {file_path.name}")
    except Exception as e:
        print(f"⚠️ Unstructured partition failed for {file_path.name}: {e}")
    
    # Method 2: Try OCR for images if available
    if OCR_AVAILABLE and not text:
        try:
            print(f"  🖼️ Trying OCR for {file_path.name}")
            # Check if file is an image by trying to open with PIL
            with Image.open(file_path) as img:
                # If we can open it as an image, try OCR
                text = pytesseract.image_to_string(img)
                if text.strip():
                    print(f"✅ Extracted text from {file_path.name} using OCR")
                    return text.strip()
                else:
                    print(f"  ⚠️ OCR returned empty text for {file_path.name}")
        except Exception as e:
            print(f"  ⚠️ OCR failed for {file_path.name}: {e}")
    elif not OCR_AVAILABLE:
        print(f"  ⚠️ OCR not available for {file_path.name}")
    
    # Method 3: Fallback loaders for known text formats
    ext = file_path.suffix.lower()
    print(f"  📄 Trying fallback methods for {file_path.name} (extension: {ext})")
    try:
        if ext == ".txt":
            print(f"    📝 Using TextLoader for {file_path.name}")
            loader = TextLoader(str(file_path))
            docs = loader.load()
            text = "\n".join([d.page_content for d in docs])
        elif ext == ".pdf":
            print(f"    📄 Using PyPDFLoader for {file_path.name}")
            loader = PyPDFLoader(str(file_path))
            docs = loader.load()
            text = "\n".join([d.page_content for d in docs])
        elif ext in [".docx", ".doc"]:
            print(f"    📝 Using Docx2txtLoader for {file_path.name}")
            loader = Docx2txtLoader(str(file_path))
            docs = loader.load()
            text = "\n".join([d.page_content for d in docs])
        else:
            # For any other format, try to read as text (might work for some formats)
            print(f"    🔤 Trying to read {file_path.name} as plain text")
            try:
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    text = f.read()
                if text.strip():
                    print(f"✅ Extracted text from {file_path.name} as plain text")
                    return text
                else:
                    print(f"  ⚠️ Plain text reading returned empty for {file_path.name}")
            except Exception as e:
                print(f"⚠️ Could not extract text from {file_path.name} (format: {ext or 'unknown'}): {e}")
                text = ""
    except Exception as e:
        print(f"❌ Failed fallback loader for {file_path}: {e}")
        text = ""

    if not text:
        print(f"❌ No text extracted from {file_path.name}")
    return text

def load_documents_from_directory(directory):
    all_docs = []
    skipped_files = []
    
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
        else:
            skipped_files.append(file_path.name)
    
    if skipped_files:
        print(f"⚠️ Could not extract text from {len(skipped_files)} files:")
        for filename in skipped_files:
            print(f"  - {filename}")

    print(f"📄 Loaded {len(all_docs)} raw documents")
    
    # Show format breakdown
    format_counts = {}
    for doc in all_docs:
        file_type = doc["metadata"]["file_type"]
        format_counts[file_type] = format_counts.get(file_type, 0) + 1
    
    if format_counts:
        print("📊 Format breakdown:")
        for fmt, count in sorted(format_counts.items()):
            print(f"  - {fmt}: {count} files")
    
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
