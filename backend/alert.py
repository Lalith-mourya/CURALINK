"""
Alert escalation module.
Fetches live doctor contact info from doctors table using patient's doctor_id,
then triggers email & telephony alerts.
"""

import sqlite3
from models.database import get_db_connection
from core.config import get_settings
from core import email_service, telephony_service, incident_logger

def send_emergency_alerts(
    patient_id: str,
    patient_name: str,
    patient_phone: str,
    message: str,
    history: list,
    risk_level: str,
    resend_key: str,
    twilio_sid: str,
    twilio_token: str,
    twilio_phone: str,
    doctor_email: str = None,
    fallback_doc_name: str = "",
    fallback_doc_phone: str = "",
) -> tuple:
    """
    Escalates an emergency alert by sending an email/call notification.
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    doctor_name = fallback_doc_name
    doctor_phone = fallback_doc_phone
    email_to_use = doctor_email
    
    try:
        # Fetch patient's doctor_id and doctor_email from database
        cursor.execute("SELECT doctor_id, doctor_email FROM patients WHERE patient_id = ? OR phone = ?", (patient_id, patient_phone))
        pat_row = cursor.fetchone()
        if pat_row:
            if not email_to_use:
                email_to_use = pat_row["doctor_email"]
            doctor_id = pat_row["doctor_id"]
            if doctor_id:
                # Fetch doctor's live details
                cursor.execute("SELECT name, phone, email FROM doctors WHERE doctor_id = ?", (doctor_id,))
                doc_row = cursor.fetchone()
                if doc_row:
                    doctor_name = doc_row["name"]
                    doctor_phone = doc_row["phone"]
                    if doc_row["email"]:
                        email_to_use = doc_row["email"]
                    print(f"[Alert] Using live doctor details from DB: name={doctor_name}, phone={doctor_phone}, email={email_to_use}")
    except Exception as e:
        print(f"[Alert] Error fetching doctor details from DB: {e}")
    finally:
        conn.close()

    # Verify completeness of required parameters
    for key_name, val in [
        ("resend_key", resend_key),
        ("twilio_sid", twilio_sid),
        ("twilio_token", twilio_token),
        ("twilio_phone", twilio_phone),
        ("doctor_email", email_to_use)
    ]:
        if not val:
            print(f"[Alert] Error: Missing alert key {key_name}")
            raise ValueError(key_name)

    # Fallbacks if none found in DB
    if not doctor_phone:
        doctor_phone = patient_phone  # fallback to calling the patient's phone for testing
    if not doctor_name:
        doctor_name = "Doctor-on-Duty"

    # 1. Send escalation email
    email_sent = email_service.send_escalation_email(
        patient_name=patient_name,
        patient_phone=patient_phone,
        doctor_name=doctor_name,
        doctor_email=email_to_use,
        risk_level=risk_level,
        risky_text=message,
        message_history=history,
        doctor_phone=doctor_phone,
        resend_key=resend_key,
    )

    # 2. Trigger emergency call
    call_result = telephony_service.trigger_emergency_call(
        patient_name=patient_name,
        risk_level=risk_level,
        callback_number=patient_phone,
        doctor_phone=doctor_phone,
        reason=message,
        account_sid=twilio_sid,
        auth_token=twilio_token,
        from_number=twilio_phone,
    )

    # 3. Log incident
    incident_id = incident_logger.log_incident(
        patient_name=patient_name,
        patient_phone=patient_phone,
        doctor_name=doctor_name,
        doctor_email=email_to_use,
        doctor_phone=doctor_phone,
        risk_level=risk_level,
        risky_text=message,
        message_history=history,
        email_sent=email_sent,
        call_status=call_result.get('status', 'unknown'),
        call_sid=call_result.get('call_sid'),
        patient_id=patient_id,
    )

    return email_sent, call_result, incident_id
