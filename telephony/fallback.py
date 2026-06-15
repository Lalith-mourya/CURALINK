"""
Fallback / retry logic for emergency calls.

Strategy:
  1. Try the doctor's primary phone number.
  2. On failure, wait `retry_delay` seconds and try the doctor again.
  3. If still failing and an emergency contact is provided, try that number.
  4. Return a structured report of every attempt.
"""

import time

from .call_handler import place_emergency_call


def place_call_with_fallback(
    patient_name: str,
    risk_level: str,
    callback_number: str,
    doctor_phone: str,
    emergency_contact: str | None = None,
    reason: str = "",
    max_retries: int = 2,
    retry_delay: int = 30,
) -> dict:
    """
    Attempt to reach the doctor with automatic retries and fallback.

    Args:
        patient_name: Patient's full name.
        risk_level: Risk classification level.
        callback_number: Number for the doctor to call back.
        doctor_phone: Doctor's primary phone number.
        emergency_contact: Optional fallback phone number.
        reason: Brief reason for the alert.
        max_retries: Maximum number of attempts on the primary number (default 2).
        retry_delay: Seconds to wait between retries (default 30).

    Returns:
        dict with:
            final_status  – 'completed' | 'failed'
            attempts      – list of per-attempt dicts
            total_attempts – int
    """

    attempts: list[dict] = []
    attempt_number = 0

    # ---- Primary number attempts --------------------------------------------
    for i in range(max_retries):
        attempt_number += 1
        print(
            f"[FALLBACK] Attempt {attempt_number}: "
            f"Calling doctor at {doctor_phone}..."
        )

        result = place_emergency_call(
            patient_name=patient_name,
            risk_level=risk_level,
            callback_number=callback_number,
            doctor_phone=doctor_phone,
            reason=reason,
        )

        attempt_record = {
            "attempt_number": attempt_number,
            "phone_called": doctor_phone,
            "call_sid": result.get("call_sid"),
            "status": result.get("status"),
        }
        attempts.append(attempt_record)

        # A non-failed status means Twilio accepted the call
        if result.get("status") != "failed":
            print(
                f"[FALLBACK] Call accepted on attempt {attempt_number}. "
                f"SID={result.get('call_sid')}"
            )
            return {
                "final_status": "completed",
                "attempts": attempts,
                "total_attempts": attempt_number,
            }

        # Not the last primary attempt → wait before retrying
        if i < max_retries - 1:
            print(
                f"[FALLBACK] Attempt {attempt_number} failed. "
                f"Retrying in {retry_delay}s..."
            )
            time.sleep(retry_delay)

    # ---- Emergency-contact fallback -----------------------------------------
    if emergency_contact and emergency_contact.strip():
        attempt_number += 1
        print(
            f"[FALLBACK] Primary number exhausted. "
            f"Attempt {attempt_number}: Calling emergency contact "
            f"at {emergency_contact}..."
        )

        result = place_emergency_call(
            patient_name=patient_name,
            risk_level=risk_level,
            callback_number=callback_number,
            doctor_phone=emergency_contact,
            reason=reason,
        )

        attempt_record = {
            "attempt_number": attempt_number,
            "phone_called": emergency_contact,
            "call_sid": result.get("call_sid"),
            "status": result.get("status"),
        }
        attempts.append(attempt_record)

        if result.get("status") != "failed":
            print(
                f"[FALLBACK] Emergency contact call accepted on attempt "
                f"{attempt_number}. SID={result.get('call_sid')}"
            )
            return {
                "final_status": "completed",
                "attempts": attempts,
                "total_attempts": attempt_number,
            }

    # ---- All attempts exhausted ---------------------------------------------
    print(
        f"[FALLBACK] All {attempt_number} attempt(s) failed. "
        f"Could not reach doctor or emergency contact."
    )

    return {
        "final_status": "failed",
        "attempts": attempts,
        "total_attempts": attempt_number,
    }
