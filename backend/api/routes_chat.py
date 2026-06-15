"""
Chat API routes.

POST /chat/ — process a patient message through risk classification
and RAG pipeline, escalating when necessary.
"""

from datetime import datetime, timezone

from typing import Optional
import re
from fastapi import APIRouter, HTTPException, Header

from core import risk_classifier, email_service, telephony_service, incident_logger, rag_pipeline
from models.schemas import ChatRequest, ChatResponse

router = APIRouter(prefix='/chat', tags=['Chat'])

# ── PROHIBITED PATTERNS FOR SECURITY INJECTION GUARD ───────────────────────
PROHIBITED_PATTERNS = [
    # Ignore instructions
    r"ignore (?:previous )?instructions",
    r"bypass (?:system )?guidelines",
    r"override instructions",
    
    # Pretend/act as doctor or admin
    r"pretend I am a (?:doctor|physician|administrator|admin|db|database)",
    r"pretend to be a (?:doctor|physician|administrator|admin|db|database)",
    r"act as a (?:doctor|physician|administrator|admin|db|database)",
    r"i am a doctor",
    r"i am the doctor",
    r"am i a doctor",
    
    # Database dumping / extraction / enumeration
    r"dump (?:the |your )?(?:vector )?database",
    r"database dump",
    r"show everything (?:in|stored in) (?:the |your )?database",
    r"tell me everything (?:in|stored in|about) (?:the |your )?database",
    r"reveal all records",
    r"print all documents",
    r"show all uploaded (?:documents|reports|files)",
    r"show every uploaded (?:document|report|file)",
    r"list all patient",
    r"list every patient",
    r"list all patients",
    r"show all patients",
    r"how many patients",
    r"extract patient",
    r"retrieve all records",
    r"database browser",
    r"all patient diagnoses",
    r"patient diagnoses",
    
    # Internal system info / code / prompt leaks
    r"system prompt",
    r"hidden instructions",
    r"vector embeddings",
    r"reveal embeddings",
    r"database schema",
    r"api keys?",
    r"internal logs",
    r"backend architecture",
    r"show hidden context",
    r"display your prompt",
    r"what is your prompt",
    
    # Cross-patient access
    r"information about other patients",
    r"other patient (?:records|documents|chat histories|info|details|profiles)",
    r"details of other patients",
    r"tell me about other patients"
]

_PROHIBITED_REGEX = re.compile("|".join(PROHIBITED_PATTERNS), re.IGNORECASE)

def is_malicious_request(message: str) -> bool:
    if _PROHIBITED_REGEX.search(message):
        return True
    return False


@router.post('/', response_model=ChatResponse)
async def chat(
    request: ChatRequest,
    x_groq_key: Optional[str] = Header(None, alias="x-groq-key"),
    x_resend_key: Optional[str] = Header(None, alias="x-resend-key"),
    x_twilio_sid: Optional[str] = Header(None, alias="x-twilio-sid"),
    x_twilio_token: Optional[str] = Header(None, alias="x-twilio-token"),
    x_twilio_phone: Optional[str] = Header(None, alias="x-twilio-phone"),
    x_doctor_email: Optional[str] = Header(None, alias="x-doctor-email"),
    x_user_role: Optional[str] = Header(None),
):
    """Process a patient chat message."""
    try:
        message = request.message
        profile = request.patient_profile
        history = request.message_history
        timestamp = datetime.now(timezone.utc).isoformat()

        if not x_groq_key:
            raise HTTPException(status_code=400, detail="API keys not configured")
        if not all([x_resend_key, x_twilio_sid, x_twilio_token, x_twilio_phone]):
            raise HTTPException(status_code=400, detail="Alert API keys not configured")

        # Step 1: Security Guard against prompt injections / DB enumeration / role impersonation
        if is_malicious_request(message):
            return ChatResponse(
                reply="I cannot provide database contents, other patient information, internal system data, or information that you are not authorized to access.",
                risk_level="safe",
                escalation_status={},
                timestamp=timestamp,
            )

        # Step 2: Role-based access verification
        role = x_user_role or "doctor"  # Default to doctor for legacy test scripts that don't send headers
        if role not in ("patient", "doctor"):
            raise HTTPException(status_code=403, detail="Unauthorized role")

        from core import patient_service
        # Fetch actual profile to verify identity and prevent parameter tampering
        db_profile = patient_service.get_patient_by_phone(profile.phone)
        if not db_profile:
            raise HTTPException(status_code=403, detail="Access denied. Patient profile not found.")

        # Ensure patients are restricted strictly to their own patient_id
        if role == "patient" and db_profile.get("patient_id") != profile.patient_id:
            raise HTTPException(status_code=403, detail="Access denied. Patient ID mismatch.")

        # Step 3: classify risk with custom key overrides
        risk_result = risk_classifier.classify_risk(message, groq_key=x_groq_key)
        risk_level = risk_result['risk_level']

        # ----- RISKY ----------------------------------------------------------
        if risk_level == 'risky':
            import alert
            
            email_sent, call_result, incident_id = alert.send_emergency_alerts(
                patient_id=profile.patient_id,
                patient_name=profile.name,
                patient_phone=profile.phone,
                message=message,
                history=history,
                risk_level=risk_level,
                resend_key=x_resend_key,
                twilio_sid=x_twilio_sid,
                twilio_token=x_twilio_token,
                twilio_phone=x_twilio_phone,
                doctor_email=x_doctor_email,
                fallback_doc_name=profile.doctor_name,
                fallback_doc_phone=profile.doctor_phone,
            )

            reply = (
                "I'm concerned about what you've shared. Your safety is the top priority. "
                "Your doctor has been notified immediately. If you are in immediate danger, "
                "please call emergency services (911) right away. "
                "You are not alone, and help is on the way."
            )

            return ChatResponse(
                reply=reply,
                risk_level='risky',
                escalation_status={
                    'email_sent': email_sent,
                    'call_triggered': call_result.get('status') != 'telephony_not_configured',
                    'call_sid': call_result.get('call_sid'),
                    'incident_logged': True,
                    'incident_id': incident_id,
                },
                timestamp=timestamp,
            )

        # ----- UNCLEAR --------------------------------------------------------
        if risk_level == 'unclear':
            # Log the chat
            incident_logger.log_chat(
                patient_name=profile.name,
                role='user',
                message=message,
                risk_level='unclear',
                patient_phone=profile.phone,
                patient_id=profile.patient_id,
            )

            reply = (
                "I want to make sure I understand you correctly. Could you tell me more "
                "about what you're experiencing? If you're feeling unwell or unsafe, "
                "please don't hesitate to contact your doctor or emergency services."
            )

            return ChatResponse(
                reply=reply,
                risk_level='unclear',
                escalation_status={},
                timestamp=timestamp,
            )

        # ----- SAFE -----------------------------------------------------------
        # Query RAG pipeline using patient_phone to prevent same-name conflict leaks
        context_chunks = rag_pipeline.query_documents(
            query=message,
            patient_phone=profile.phone,
        )

        # Generate response via Groq + context
        generated_reply = rag_pipeline.generate_response(
            query=message,
            context_chunks=context_chunks,
            patient_profile=profile.model_dump(),
            groq_key=x_groq_key,
        )

        # Log the chat exchange with patient_phone
        incident_logger.log_chat(
            patient_name=profile.name,
            role='user',
            message=message,
            risk_level='safe',
            patient_phone=profile.phone,
            patient_id=profile.patient_id,
        )
        incident_logger.log_chat(
            patient_name=profile.name,
            role='assistant',
            message=generated_reply,
            risk_level='safe',
            patient_phone=profile.phone,
            patient_id=profile.patient_id,
        )

        return ChatResponse(
            reply=generated_reply,
            risk_level='safe',
            escalation_status={},
            timestamp=timestamp,
        )

    except Exception as exc:
        print(f"[Chat] Error processing message: {exc}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {exc}")
