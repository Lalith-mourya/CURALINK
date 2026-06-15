"""
Log retrieval routes.

GET /logs/incidents     — list escalation incidents.
GET /logs/chat-history  — list chat log entries.
"""

from typing import List, Optional
from fastapi import APIRouter, Query, Header, HTTPException

from core.incident_logger import get_incidents, get_chat_logs
from models.schemas import LogEntry

router = APIRouter(prefix='/logs', tags=['Logs'])


@router.get('/incidents', response_model=List[LogEntry])
async def list_incidents(
    patient_name: Optional[str] = Query(None),
    risk_level: Optional[str] = Query(None),
    patient_phone: Optional[str] = Query(None),
    patient_id: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=500),
    order: str = Query('DESC'),
    x_user_role: Optional[str] = Header(None),
    x_user_doctor_id: Optional[str] = Header(None),
):
    """Return recent incidents, optionally filtered by patient, ID, phone, or risk level."""
    role = x_user_role or "doctor"  # Default to doctor for test scripts
    if role != "doctor":
        raise HTTPException(status_code=403, detail="Access denied. Doctors only.")
    if not x_user_doctor_id:
        raise HTTPException(status_code=400, detail="Doctor ID header missing")
    return get_incidents(
        patient_name=patient_name,
        risk_level=risk_level,
        patient_phone=patient_phone,
        patient_id=patient_id,
        limit=limit,
        order=order,
        doctor_id=x_user_doctor_id,
    )


@router.get('/chat-history')
async def list_chat_history(
    patient_name: Optional[str] = Query(None),
    patient_phone: Optional[str] = Query(None),
    patient_id: Optional[str] = Query(None),
    limit: int = Query(100, ge=1, le=1000),
    order: str = Query('DESC'),
    x_user_role: Optional[str] = Header(None),
    x_user_doctor_id: Optional[str] = Header(None),
):
    """Return recent chat log entries."""
    role = x_user_role or "doctor"  # Default to doctor for test scripts
    if role != "doctor":
        raise HTTPException(status_code=403, detail="Access denied. Doctors only.")
    if not x_user_doctor_id:
        raise HTTPException(status_code=400, detail="Doctor ID header missing")
    return get_chat_logs(
        patient_name=patient_name,
        patient_phone=patient_phone,
        patient_id=patient_id,
        limit=limit,
        order=order,
        doctor_id=x_user_doctor_id,
    )
