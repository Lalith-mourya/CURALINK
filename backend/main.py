"""
Healthcare Chatbot API — main application entry point.

Creates the FastAPI app, registers middleware, includes all routers,
and handles startup / shutdown lifecycle events.
"""

import os
import uvicorn
from typing import Optional
from dotenv import load_dotenv

# Load environment variables from .env
for env_path in [".env", "../.env", "../../.env"]:
    if os.path.exists(env_path):
        load_dotenv(env_path)
        break

DB_PATH = os.getenv("DB_PATH", "./incidents.db")
CHROMA_PATH = os.getenv("CHROMA_PATH", "./chroma_store")
PATIENTS_DIR = os.getenv("PATIENTS_DIR", "./data/patients")
from fastapi import FastAPI, Header
from fastapi.middleware.cors import CORSMiddleware

from core.config import get_settings
from models.database import init_db
from core.rag_pipeline import init_rag

from api.routes_chat import router as chat_router
from api.routes_documents import router as documents_router
from api.routes_logs import router as logs_router
from api.routes_risk import router as risk_router
from api.routes_health import router as health_router
from api.routes_patients import router as patients_router
from routers.auth import router as auth_router

# ---------------------------------------------------------------------------
# App factory
# ---------------------------------------------------------------------------
app = FastAPI(
    title='Healthcare Chatbot API',
    description=(
        'A patient-support chatbot backend with RAG-powered responses, '
        'two-layer risk classification, email/telephony escalation, '
        'and incident logging.'
    ),
    version='1.0.0',
)

# ---------------------------------------------------------------------------
# CORS (development — allow all origins)
# ---------------------------------------------------------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=['*'],
    allow_credentials=True,
    allow_methods=['*'],
    allow_headers=['*'],
)

# ---------------------------------------------------------------------------
# Register routers
# ---------------------------------------------------------------------------
app.include_router(chat_router)
app.include_router(documents_router)
app.include_router(logs_router)
app.include_router(risk_router)
app.include_router(health_router)
app.include_router(patients_router)
app.include_router(auth_router)


# ---------------------------------------------------------------------------
# Lifecycle events
# ---------------------------------------------------------------------------
@app.on_event('startup')
async def startup_event():
    """Initialise database and RAG pipeline on startup."""
    print("[Startup] Initialising database …")
    init_db()
    print("[Startup] Initialising RAG pipeline …")
    init_rag()
    print("[Startup] Healthcare Chatbot API is ready.")


@app.on_event('shutdown')
async def shutdown_event():
    """Cleanup on shutdown."""
    print("[Shutdown] Healthcare Chatbot API shutting down.")


# ---------------------------------------------------------------------------
# Root endpoint
# ---------------------------------------------------------------------------
@app.get('/')
async def root(x_user_doctor_id: Optional[str] = Header(None)):
    """Root endpoint — simple liveness check."""
    return {
        'message': 'Healthcare Chatbot API is running',
        'doctor_id_header_supported': True
    }


# ---------------------------------------------------------------------------
# Direct execution
# ---------------------------------------------------------------------------
if __name__ == '__main__':
    settings = get_settings()
    uvicorn.run(
        'main:app',
        host=settings.API_HOST,
        port=settings.API_PORT,
        reload=True,
    )
