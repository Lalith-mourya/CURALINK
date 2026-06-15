"""
Telephony service — thin bridge to the project-level telephony package.

Attempts to import from telephony.call_handler. If the package is not
installed / configured, gracefully degrades.
"""

from typing import Dict, Optional


def trigger_emergency_call(
    patient_name: str,
    risk_level: str,
    callback_number: str,
    doctor_phone: str,
    reason: str,
    account_sid: str,
    auth_token: str,
    from_number: str,
) -> Dict:
    """
    Initiate an automated emergency call to the doctor.

    Returns dict with keys: call_sid, status.
    """
    if not account_sid:
        raise ValueError("account_sid")
    if not auth_token:
        raise ValueError("auth_token")
    if not from_number:
        raise ValueError("from_number")

    try:
        import sys
        import os
        # Add project root to sys.path
        backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        project_root = os.path.dirname(backend_dir)
        if project_root not in sys.path:
            sys.path.insert(0, project_root)

        from core.config import get_settings
        from telephony.call_handler import place_emergency_call

        settings = get_settings()

        result = place_emergency_call(
            patient_name=patient_name,
            risk_level=risk_level,
            callback_number=callback_number,
            doctor_phone=doctor_phone,
            reason=reason,
            account_sid=account_sid,
            auth_token=auth_token,
            from_number=from_number,
        )
        return {
            'call_sid': result.get('call_sid'),
            'status': result.get('status', 'initiated'),
        }

    except ImportError:
        print("[Telephony] telephony package not found — call not initiated.")
        return {
            'call_sid': None,
            'status': 'telephony_not_configured',
        }
    except Exception as exc:
        print(f"[Telephony] Emergency call failed: {exc}")
        return {
            'call_sid': None,
            'status': f'error: {exc}',
        }
