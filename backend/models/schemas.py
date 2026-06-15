"""
Pydantic models / schemas for API requests and responses.
"""

from typing import List
from pydantic import BaseModel


class PatientProfile(BaseModel):
    """Patient profile information."""
    name: str
    age: int
    gender: str = ''
    height: float = 0.0
    weight: float = 0.0
    phone: str
    email: str = ''
    doctor_name: str = ''
    doctor_email: str = ''
    doctor_phone: str = ''
    emergency_contact: str = ''
    medicines: List[str] = []
    special_instructions: str = ''
    medical_issue: str = ''
    patient_id: str = ''
    blood_group: str = ''
    address: str = ''
    profile_status: str = 'Active'
    created_at: str = ''
    last_login: str = ''


class ChatRequest(BaseModel):
    """Incoming chat request payload."""
    message: str
    patient_profile: PatientProfile
    message_history: List[dict] = []


class ChatResponse(BaseModel):
    """Chat endpoint response."""
    reply: str
    risk_level: str
    escalation_status: dict = {}
    timestamp: str


class RiskTestRequest(BaseModel):
    """Request body for the risk-test endpoint."""
    message: str


class RiskTestResponse(BaseModel):
    """Response from the risk-test endpoint."""
    risk_level: str
    keywords_found: List[str]
    explanation: str


class DocumentUploadResponse(BaseModel):
    """Response after uploading a document."""
    status: str
    filename: str
    chunks_indexed: int


class LogEntry(BaseModel):
    """A single incident log entry."""
    id: int
    patient_name: str
    patient_phone: str
    doctor_name: str
    doctor_email: str
    risk_level: str
    risky_text: str
    email_sent: bool
    call_status: str
    created_at: str


class HealthResponse(BaseModel):
    """Health-check response showing status of each sub-system."""
    api_status: str
    ollama_status: str
    chroma_status: str
    db_status: str
    groq_configured: bool = False
    resend_configured: bool = False
    twilio_configured: bool = False
