"""
RAG (Retrieval-Augmented Generation) pipeline.

Uses ChromaDB for vector storage and SentenceTransformers for embeddings.
Ollama provides the LLM for response generation.
"""

import os
import json
from dotenv import load_dotenv

# Load environment variables from .env
for env_path in [".env", "../.env", "../../.env"]:
    if os.path.exists(env_path):
        load_dotenv(env_path)
        break

from datetime import datetime
from typing import List, Optional

import chromadb
from groq import Groq

from core.config import get_settings

DB_PATH = os.getenv("DB_PATH", "./incidents.db")
CHROMA_PATH = os.getenv("CHROMA_PATH", "./chroma_store")
PATIENTS_DIR = os.getenv("PATIENTS_DIR", "./data/patients")

# ---------------------------------------------------------------------------
# Module-level singletons (initialised by init_rag())
# ---------------------------------------------------------------------------
_chroma_client: Optional[chromadb.ClientAPI] = None
_collection: Optional[chromadb.Collection] = None
_local_model = None

COLLECTION_NAME = 'patient_docs'

RAG_SYSTEM_PROMPT = (
    "You are a healthcare support assistant. "
    "Answer ONLY from the provided context documents. "
    "If the context doesn't contain relevant information, say "
    "\"I don't have enough information about that. Please consult your doctor.\" "
    "Keep answers concise and under 3 sentences. "
    "Never give direct medical advice. "
    "Always recommend consulting the doctor for important decisions."
)

def get_embeddings(texts: List[str]) -> List[List[float]]:
    """Get embeddings using Hugging Face Inference API, falling back to local SentenceTransformer if needed."""
    api_url = "https://api-inference.huggingface.co/models/sentence-transformers/all-MiniLM-L6-v2"
    headers = {"Content-Type": "application/json"}
    hf_token = os.getenv("HF_TOKEN")
    if hf_token:
        headers["Authorization"] = f"Bearer {hf_token}"
    
    payload = {"inputs": texts, "options": {"wait_for_model": True}}
    try:
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(api_url, data=data, headers=headers, method="POST")
        import urllib.error
        with urllib.request.urlopen(req, timeout=12) as response:
            res_body = response.read().decode("utf-8")
            res_json = json.loads(res_body)
            if isinstance(res_json, list) and len(res_json) > 0:
                if isinstance(res_json[0], float):
                    return [res_json]
                elif isinstance(res_json[0], list):
                    return res_json
    except Exception as e:
        print(f"[RAG] HF Inference API failed: {e}. Falling back to local SentenceTransformer.")

    # Local fallback
    global _local_model
    if _local_model is None:
        print("[RAG] Loading local SentenceTransformer model (fallback)...")
        from sentence_transformers import SentenceTransformer
        _local_model = SentenceTransformer(get_settings().EMBEDDING_MODEL)
    return _local_model.encode(texts).tolist()


# ---------------------------------------------------------------------------
# Initialisation
# ---------------------------------------------------------------------------
def init_rag() -> None:
    """Initialise ChromaDB persistent client."""
    global _chroma_client, _collection

    settings = get_settings()

    # Ensure the persist directory exists
    os.makedirs(CHROMA_PATH, exist_ok=True)

    _chroma_client = chromadb.PersistentClient(path=CHROMA_PATH)
    _collection = _chroma_client.get_or_create_collection(name=COLLECTION_NAME)

    print(f"[RAG] ChromaDB initialised at {settings.CHROMA_PERSIST_DIR}")


def get_chroma_client() -> Optional[chromadb.ClientAPI]:
    """Return the ChromaDB client (for health checks)."""
    return _chroma_client


# ---------------------------------------------------------------------------
# Document ingestion helpers
# ---------------------------------------------------------------------------
def _read_file(file_path: str) -> str:
    """Read text content from PDF, DOCX, or plain-text files."""
    ext = os.path.splitext(file_path)[1].lower()

    if ext == '.pdf':
        from PyPDF2 import PdfReader
        reader = PdfReader(file_path)
        return '\n'.join(page.extract_text() or '' for page in reader.pages)

    if ext == '.docx':
        from docx import Document
        doc = Document(file_path)
        return '\n'.join(para.text for para in doc.paragraphs)

    # Default: plain text
    with open(file_path, 'r', encoding='utf-8') as fh:
        return fh.read()


def _chunk_text(text: str, chunk_size: int = 500, overlap: int = 50) -> List[str]:
    """Split *text* into overlapping chunks of approximately *chunk_size* characters."""
    chunks: List[str] = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        chunks.append(text[start:end])
        start += chunk_size - overlap
    return [c.strip() for c in chunks if c.strip()]


# ---------------------------------------------------------------------------
# Ingest
# ---------------------------------------------------------------------------
def ingest_document(file_path: str, patient_name: str, patient_phone: str, doc_type: str) -> int:
    """
    Read a document, chunk it, embed chunks, and store in ChromaDB.

    Returns the number of chunks indexed.
    """
    if _collection is None:
        raise RuntimeError("RAG pipeline not initialised. Call init_rag() first.")

    text = _read_file(file_path)
    if not text.strip():
        return 0

    chunks = _chunk_text(text)
    if not chunks:
        return 0

    embeddings = get_embeddings(chunks)
    upload_date = datetime.utcnow().isoformat()
    filename = os.path.basename(file_path)

    # Sanitise IDs by using patient_phone
    ids = [f"{patient_phone}_{doc_type}_{upload_date}_{i}" for i in range(len(chunks))]
    metadatas = [
        {
            'patient_name': patient_name,
            'patient_phone': patient_phone,
            'doc_type': doc_type,
            'upload_date': upload_date,
            'filename': filename,
        }
        for _ in chunks
    ]

    _collection.add(
        ids=ids,
        embeddings=embeddings,
        documents=chunks,
        metadatas=metadatas,
    )

    print(f"[RAG] Ingested {len(chunks)} chunks from '{file_path}' for patient '{patient_name}' ({patient_phone}) with filename metadata.")
    return len(chunks)


# ---------------------------------------------------------------------------
# Query
# ---------------------------------------------------------------------------
def query_documents(query: str, patient_phone: str, n_results: int = 3) -> List[str]:
    """
    Embed the *query*, search ChromaDB filtered by *patient_phone*, and return
    the most relevant document chunks.
    """
    if _collection is None:
        print("[RAG] Pipeline not initialised — returning empty results.")
        return []

    query_embedding = get_embeddings([query])

    try:
        results = _collection.query(
            query_embeddings=query_embedding,
            n_results=n_results,
            where={'patient_phone': patient_phone},
        )
    except Exception as exc:
        print(f"[RAG] ChromaDB query failed: {exc}")
        return []

    documents = results.get('documents', [[]])
    # ChromaDB returns a list-of-lists; flatten the first (only) query result
    return documents[0] if documents else []


# ---------------------------------------------------------------------------
# Response generation
# ---------------------------------------------------------------------------
def generate_response(
    query: str,
    context_chunks: List[str],
    patient_profile: dict,
    groq_key: str,
    model: str | None = None,
) -> str:
    """
    Generate an LLM response grounded on the retrieved *context_chunks*.
    """
    settings = get_settings()

    if context_chunks:
        context_block = '\n---\n'.join(context_chunks)
        user_content = (
            f"Patient: {patient_profile.get('name', 'Unknown')}, "
            f"Age: {patient_profile.get('age', 'N/A')}\n"
            f"Medicines: {', '.join(patient_profile.get('medicines', [])) or 'None listed'}\n"
            f"Special Instructions: {patient_profile.get('special_instructions', 'None')}\n\n"
            f"Context Documents:\n{context_block}\n\n"
            f"Patient Question: {query}"
        )
    else:
        user_content = (
            f"Patient: {patient_profile.get('name', 'Unknown')}, "
            f"Age: {patient_profile.get('age', 'N/A')}\n\n"
            f"No relevant documents were found for this patient.\n\n"
            f"Patient Question: {query}"
        )

    try:
        if not groq_key:
            raise ValueError("Groq API key not provided")
        client = Groq(api_key=groq_key)
        response = client.chat.completions.create(
            model=model or settings.GROQ_MODEL,
            messages=[
                {'role': 'system', 'content': RAG_SYSTEM_PROMPT},
                {'role': 'user', 'content': user_content},
            ],
            temperature=0.0,
        )
        return response.choices[0].message.content.strip()
    except Exception as exc:
        print(f"[RAG] Groq generation failed: {exc}")
        return (
            "I'm sorry, I'm unable to process your question right now. "
            "Please try again later or contact your doctor directly."
        )


def delete_document_from_rag(patient_phone: str, filename: str) -> None:
    """Delete all chunks for a specific patient and filename from ChromaDB."""
    global _collection
    if _collection is not None:
        try:
            # ChromaDB supports query by implicit AND inside dict
            _collection.delete(where={'patient_phone': patient_phone, 'filename': filename})
            print(f"[RAG] Deleted chunks for patient {patient_phone}, file '{filename}' from ChromaDB.")
        except Exception as exc:
            print(f"[RAG] Error deleting chunks from ChromaDB: {exc}")
