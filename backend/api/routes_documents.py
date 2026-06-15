"""
Document management routes.

POST /documents/upload   — upload and ingest a patient document.
GET  /documents/list/{patient_name} — list uploaded files.
"""

import os
from typing import List, Optional
from fastapi import APIRouter, File, Form, UploadFile, HTTPException, Header

from core.rag_pipeline import ingest_document
from models.schemas import DocumentUploadResponse

router = APIRouter(prefix='/documents', tags=['Documents'])

from dotenv import load_dotenv

# Load environment variables from .env
for env_path in [".env", "../.env", "../../.env"]:
    if os.path.exists(env_path):
        load_dotenv(env_path)
        break

DB_PATH = os.getenv("DB_PATH", "./incidents.db")
CHROMA_PATH = os.getenv("CHROMA_PATH", "./chroma_store")
PATIENTS_DIR = os.getenv("PATIENTS_DIR", "./data/patients")

PATIENT_DOCS_DIR = PATIENTS_DIR


def verify_document_access(
    patient_phone: str,
    x_user_role: Optional[str] = None,
    x_user_phone: Optional[str] = None,
) -> None:
    role = x_user_role or "doctor"  # Default to doctor for legacy test scripts
    if role not in ("patient", "doctor"):
        raise HTTPException(status_code=403, detail="Unauthorized role")
    if role == "patient":
        if not x_user_phone or x_user_phone != patient_phone:
            raise HTTPException(status_code=403, detail="Access denied. Cannot access another patient's documents.")


@router.post('/upload', response_model=DocumentUploadResponse)
async def upload_document(
    file: UploadFile = File(...),
    patient_name: str = Form(...),
    patient_phone: str = Form(...),
    x_user_role: Optional[str] = Header(None),
    x_user_phone: Optional[str] = Header(None),
):
    """Upload a document, save to disk, and ingest into the vector store."""
    verify_document_access(patient_phone, x_user_role, x_user_phone)
    try:
        # Ensure patient directory exists using name and phone to prevent conflicts
        folder_name = f"{patient_name}_{patient_phone}".replace('/', '').replace('\\', '').strip()
        patient_dir = os.path.join(PATIENT_DOCS_DIR, folder_name)
        os.makedirs(patient_dir, exist_ok=True)

        # Save file to disk
        file_path = os.path.join(patient_dir, file.filename)
        contents = await file.read()
        with open(file_path, 'wb') as f:
            f.write(contents)

        # Determine doc_type from extension
        ext = os.path.splitext(file.filename)[1].lower().lstrip('.')
        doc_type = ext if ext in ('pdf', 'txt', 'docx') else 'other'

        # Ingest into ChromaDB
        chunks_indexed = ingest_document(
            file_path=file_path,
            patient_name=patient_name,
            patient_phone=patient_phone,
            doc_type=doc_type,
        )

        return DocumentUploadResponse(
            status='success',
            filename=file.filename,
            chunks_indexed=chunks_indexed,
        )

    except Exception as exc:
        print(f"[Documents] Upload failed: {exc}")
        raise HTTPException(status_code=500, detail=f"Document upload failed: {exc}")


@router.get('/list/{patient_phone}', response_model=List[str])
async def list_documents(
    patient_phone: str,
    patient_name: str = "",
    x_user_role: Optional[str] = Header(None),
    x_user_phone: Optional[str] = Header(None),
):
    """List all uploaded documents for a given patient by phone and optional name."""
    verify_document_access(patient_phone, x_user_role, x_user_phone)
    folder_name = f"{patient_name}_{patient_phone}".replace('/', '').replace('\\', '').strip()
    patient_dir = os.path.join(PATIENT_DOCS_DIR, folder_name)

    # Fallback suffix match check for robust lookups
    if not os.path.isdir(patient_dir) and os.path.isdir(PATIENT_DOCS_DIR):
        for d in os.listdir(PATIENT_DOCS_DIR):
            if d.endswith(f"_{patient_phone}"):
                patient_dir = os.path.join(PATIENT_DOCS_DIR, d)
                break

    if not os.path.isdir(patient_dir):
        return []
    return [
        f for f in os.listdir(patient_dir)
        if os.path.isfile(os.path.join(patient_dir, f))
    ]


@router.delete('/{patient_phone}')
async def delete_document(
    patient_phone: str,
    filename: str,
    patient_name: str = "",
    x_user_role: Optional[str] = Header(None),
    x_user_phone: Optional[str] = Header(None),
):
    """Delete an uploaded document from both disk and ChromaDB vector store."""
    verify_document_access(patient_phone, x_user_role, x_user_phone)
    try:
        from core.rag_pipeline import delete_document_from_rag
        
        folder_name = f"{patient_name}_{patient_phone}".replace('/', '').replace('\\', '').strip()
        patient_dir = os.path.join(PATIENT_DOCS_DIR, folder_name)

        # Fallback suffix match check for robust lookups
        if not os.path.isdir(patient_dir) and os.path.isdir(PATIENT_DOCS_DIR):
            for d in os.listdir(PATIENT_DOCS_DIR):
                if d.endswith(f"_{patient_phone}"):
                    patient_dir = os.path.join(PATIENT_DOCS_DIR, d)
                    break

        if not os.path.isdir(patient_dir):
            raise HTTPException(status_code=404, detail="Patient document directory not found")

        file_path = os.path.join(patient_dir, filename)
        if not os.path.isfile(file_path):
            raise HTTPException(status_code=404, detail="File not found")

        # Delete file from disk
        os.remove(file_path)

        # Delete chunks from RAG
        delete_document_from_rag(patient_phone, filename)

        return {"status": "success", "message": f"Document '{filename}' deleted successfully."}
    except HTTPException:
        raise
    except Exception as exc:
        print(f"[Documents] Delete failed: {exc}")
        raise HTTPException(status_code=500, detail=f"Document deletion failed: {exc}")


from pydantic import BaseModel

class UpdateDocumentRequest(BaseModel):
    content: str


@router.get('/content/{patient_phone}')
async def get_document_content(
    patient_phone: str,
    filename: str,
    patient_name: str = "",
    x_user_role: Optional[str] = Header(None),
    x_user_phone: Optional[str] = Header(None),
):
    """Retrieve the text content of a patient document (extracting text if PDF or DOCX)."""
    verify_document_access(patient_phone, x_user_role, x_user_phone)
    try:
        from core.rag_pipeline import _read_file
        
        folder_name = f"{patient_name}_{patient_phone}".replace('/', '').replace('\\', '').strip()
        patient_dir = os.path.join(PATIENT_DOCS_DIR, folder_name)

        # Fallback suffix match check for robust lookups
        if not os.path.isdir(patient_dir) and os.path.isdir(PATIENT_DOCS_DIR):
            for d in os.listdir(PATIENT_DOCS_DIR):
                if d.endswith(f"_{patient_phone}"):
                    patient_dir = os.path.join(PATIENT_DOCS_DIR, d)
                    break

        if not os.path.isdir(patient_dir):
            raise HTTPException(status_code=404, detail="Patient document directory not found")

        file_path = os.path.join(patient_dir, filename)
        if not os.path.isfile(file_path):
            raise HTTPException(status_code=404, detail="File not found")

        text = _read_file(file_path)
        return {"content": text}
    except HTTPException:
        raise
    except Exception as exc:
        print(f"[Documents] Failed to get content: {exc}")
        raise HTTPException(status_code=500, detail=f"Failed to retrieve document content: {exc}")


@router.post('/update/{patient_phone}')
async def update_document_content(
    patient_phone: str,
    filename: str,
    data: UpdateDocumentRequest,
    patient_name: str = "",
    x_user_role: Optional[str] = Header(None),
    x_user_phone: Optional[str] = Header(None),
):
    """Update the text content of a document, replacing it with a .txt version if originally binary."""
    verify_document_access(patient_phone, x_user_role, x_user_phone)
    try:
        from core.rag_pipeline import delete_document_from_rag, ingest_document
        
        folder_name = f"{patient_name}_{patient_phone}".replace('/', '').replace('\\', '').strip()
        patient_dir = os.path.join(PATIENT_DOCS_DIR, folder_name)

        # Fallback suffix match check for robust lookups
        if not os.path.isdir(patient_dir) and os.path.isdir(PATIENT_DOCS_DIR):
            for d in os.listdir(PATIENT_DOCS_DIR):
                if d.endswith(f"_{patient_phone}"):
                    patient_dir = os.path.join(PATIENT_DOCS_DIR, d)
                    break

        if not os.path.isdir(patient_dir):
            raise HTTPException(status_code=404, detail="Patient document directory not found")

        original_path = os.path.join(patient_dir, filename)
        if not os.path.isfile(original_path):
            raise HTTPException(status_code=404, detail="Original file not found")

        # Determine target filename (force .txt if originally binary)
        base, ext = os.path.splitext(filename)
        ext = ext.lower()
        
        if ext == '.txt':
            target_filename = filename
            target_path = original_path
        else:
            target_filename = f"{base}.txt"
            target_path = os.path.join(patient_dir, target_filename)
            
            # Delete the original binary file from disk
            os.remove(original_path)
            # Delete the original binary file chunks from RAG
            delete_document_from_rag(patient_phone, filename)

        # Write new content to disk
        with open(target_path, 'w', encoding='utf-8') as f:
            f.write(data.content)

        # Delete existing target text chunks from RAG if any (to prevent duplicates if it already existed)
        delete_document_from_rag(patient_phone, target_filename)

        # Ingest new content into ChromaDB
        chunks_indexed = ingest_document(
            file_path=target_path,
            patient_name=patient_name or "Unknown",
            patient_phone=patient_phone,
            doc_type="txt",
        )

        return {
            "status": "success",
            "filename": target_filename,
            "chunks_indexed": chunks_indexed,
            "message": f"Document updated successfully. Saved as '{target_filename}'."
        }
    except HTTPException:
        raise
    except Exception as exc:
        print(f"[Documents] Update failed: {exc}")
        raise HTTPException(status_code=500, detail=f"Document update failed: {exc}")
