"""
Core call handler for placing emergency calls via the Twilio API.

Loads credentials from function parameters or environment variables,
generates TwiML, and places the call. All attempts are logged.
"""

import os
from datetime import datetime, timezone

from twilio.rest import Client
from twilio.base.exceptions import TwilioRestException

from .twiml_templates import generate_emergency_twiml


def place_emergency_call(
    patient_name: str,
    risk_level: str,
    callback_number: str,
    doctor_phone: str,
    reason: str,
    account_sid: str | None = None,
    auth_token: str | None = None,
    from_number: str | None = None,
) -> dict:
    """
    Place an emergency phone call to a doctor via Twilio.

    Credentials are resolved in order: explicit parameters → environment
    variables.  On success the Twilio call SID and status are returned;
    on any failure the error is captured and returned instead.

    Args:
        patient_name: Full patient name (first name used in voice message).
        risk_level: Risk classification (e.g. "high", "critical").
        callback_number: Number the doctor should call back.
        doctor_phone: Doctor's phone number to dial.
        reason: Brief reason the alert was triggered.
        account_sid: Twilio Account SID (falls back to TWILIO_ACCOUNT_SID env var).
        auth_token: Twilio Auth Token (falls back to TWILIO_AUTH_TOKEN env var).
        from_number: Twilio phone number to call from (falls back to TWILIO_PHONE_NUMBER env var).

    Returns:
        dict with keys:
            call_sid   – Twilio call SID or None on failure
            status     – Twilio call status string or 'failed'
            to         – the phone number that was called
            initiated_at – ISO-8601 UTC timestamp
            error      – error message (only present on failure)
    """

    initiated_at = datetime.now(timezone.utc).isoformat()

    # ---- Resolve credentials ------------------------------------------------
    sid = account_sid or os.environ.get("TWILIO_ACCOUNT_SID")
    token = auth_token or os.environ.get("TWILIO_AUTH_TOKEN")
    caller_id = from_number or os.environ.get("TWILIO_PHONE_NUMBER")

    if not sid or not token:
        error_msg = (
            "Twilio credentials missing. Provide account_sid/auth_token "
            "as arguments or set TWILIO_ACCOUNT_SID and TWILIO_AUTH_TOKEN "
            "environment variables."
        )
        print(f"[TELEPHONY ERROR] {error_msg}")
        return {
            "call_sid": None,
            "status": "failed",
            "error": error_msg,
            "to": doctor_phone,
            "initiated_at": initiated_at,
        }

    if not caller_id:
        error_msg = (
            "Twilio from-number missing. Provide from_number as an argument "
            "or set the TWILIO_PHONE_NUMBER environment variable."
        )
        print(f"[TELEPHONY ERROR] {error_msg}")
        return {
            "call_sid": None,
            "status": "failed",
            "error": error_msg,
            "to": doctor_phone,
            "initiated_at": initiated_at,
        }

    if not doctor_phone or not doctor_phone.strip():
        error_msg = "doctor_phone is required and cannot be empty."
        print(f"[TELEPHONY ERROR] {error_msg}")
        return {
            "call_sid": None,
            "status": "failed",
            "error": error_msg,
            "to": doctor_phone,
            "initiated_at": initiated_at,
        }

    # ---- Generate TwiML & place call ----------------------------------------
    try:
        twiml_xml = generate_emergency_twiml(
            patient_name=patient_name,
            risk_level=risk_level,
            callback_number=callback_number,
            reason=reason,
        )

        print(
            f"[TELEPHONY] Placing emergency call to {doctor_phone} "
            f"for patient '{patient_name}' (risk={risk_level})"
        )

        client = Client(sid, token)
        call = client.calls.create(
            twiml=twiml_xml,
            to=doctor_phone,
            from_=caller_id,
        )

        print(
            f"[TELEPHONY] Call placed successfully. "
            f"SID={call.sid}, status={call.status}"
        )

        return {
            "call_sid": call.sid,
            "status": call.status,
            "to": doctor_phone,
            "initiated_at": initiated_at,
        }

    except TwilioRestException as e:
        error_msg = f"Twilio API error: {e}"
        print(f"[TELEPHONY ERROR] {error_msg}")
        return {
            "call_sid": None,
            "status": "failed",
            "error": error_msg,
            "to": doctor_phone,
            "initiated_at": initiated_at,
        }

    except Exception as e:
        error_msg = f"Unexpected error placing call: {e}"
        print(f"[TELEPHONY ERROR] {error_msg}")
        return {
            "call_sid": None,
            "status": "failed",
            "error": error_msg,
            "to": doctor_phone,
            "initiated_at": initiated_at,
        }
