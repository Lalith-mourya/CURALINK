"""
Health check route.

GET /health — reports status of API, Ollama, ChromaDB, and SQLite.
"""

from typing import Optional
from fastapi import APIRouter, Header

from groq import Groq
from core.config import get_settings
from core.rag_pipeline import get_chroma_client
from models.database import get_db_connection
from models.schemas import HealthResponse

router = APIRouter(prefix='', tags=['Health'])


@router.get('/health', response_model=HealthResponse)
async def health_check(
    x_groq_key: Optional[str] = Header(None, alias="x-groq-key"),
):
    """Check the health of all backend sub-systems."""
    settings = get_settings()

    # --- Groq (LLM Engine) ----------------------------------------------------
    ollama_status = 'unknown'
    try:
        key = x_groq_key
        if not key:
            raise ValueError("Groq API key not provided in header.")
        client = Groq(api_key=key)
        client.models.list()
        ollama_status = 'connected'
    except Exception as exc:
        ollama_status = f'error: {exc}'

    # --- ChromaDB -------------------------------------------------------------
    chroma_status = 'unknown'
    try:
        client = get_chroma_client()
        if client is not None:
            client.heartbeat()
            chroma_status = 'connected'
        else:
            chroma_status = 'not_initialised'
    except Exception as exc:
        chroma_status = f'error: {exc}'

    # --- SQLite ---------------------------------------------------------------
    db_status = 'unknown'
    try:
        conn = get_db_connection()
        conn.execute("SELECT 1")
        conn.close()
        db_status = 'connected'
    except Exception as exc:
        db_status = f'error: {exc}'

    return HealthResponse(
        api_status='running',
        ollama_status=ollama_status,
        chroma_status=chroma_status,
        db_status=db_status,
        groq_configured=bool(x_groq_key),
        resend_configured=False,
        twilio_configured=False,
    )
