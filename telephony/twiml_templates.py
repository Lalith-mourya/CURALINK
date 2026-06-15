"""
TwiML XML template generators for emergency and voicemail calls.

These templates produce Twilio Markup Language (TwiML) strings that instruct
Twilio on what to say when a call connects or reaches voicemail.
"""


def generate_emergency_twiml(
    patient_name: str,
    risk_level: str,
    callback_number: str,
    reason: str,
) -> str:
    """
    Generate TwiML XML for an emergency call to the doctor.

    The message is spoken twice (with a pause in between) to ensure
    the doctor catches all details. Uses first name only for patient
    privacy (HIPAA consideration).

    Args:
        patient_name: Full name of the patient (only first name is used).
        risk_level: Risk classification level (e.g., "high", "critical").
        callback_number: Phone number the doctor should call back.
        reason: Brief description of why the alert was triggered.

    Returns:
        A TwiML XML string ready to be passed to Twilio's calls.create().
    """
    # Extract first name only for privacy
    first_name = patient_name.strip().split()[0] if patient_name and patient_name.strip() else "Unknown"

    # Sanitize inputs to prevent XML injection
    first_name = _xml_escape(first_name)
    risk_level = _xml_escape(risk_level)
    callback_number = _xml_escape(callback_number)
    reason = _xml_escape(reason)

    message = (
        f"Urgent alert from the patient healthcare support system. "
        f"Patient {first_name} has been flagged at {risk_level} risk level. "
        f"Reason: {reason}. "
        f"Please call back at {callback_number} immediately. "
        f"An email with full details has already been sent to you. "
        f"This is an automated emergency message."
    )

    twiml = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        "<Response>"
        f'<Say voice="Polly.Joanna" language="en-US">{message}</Say>'
        '<Pause length="1"/>'
        f'<Say voice="Polly.Joanna" language="en-US">I repeat, {message}</Say>'
        "</Response>"
    )

    return twiml


def generate_voicemail_twiml(
    patient_name: str,
    risk_level: str,
    callback_number: str,
) -> str:
    """
    Generate a shorter TwiML XML message suitable for voicemail.

    Args:
        patient_name: Full name of the patient (only first name is used).
        risk_level: Risk classification level.
        callback_number: Phone number the doctor should call back.

    Returns:
        A TwiML XML string for voicemail.
    """
    first_name = patient_name.strip().split()[0] if patient_name and patient_name.strip() else "Unknown"

    first_name = _xml_escape(first_name)
    risk_level = _xml_escape(risk_level)
    callback_number = _xml_escape(callback_number)

    message = (
        f"Urgent patient alert. "
        f"Patient {first_name} flagged {risk_level}. "
        f"Call {callback_number}. "
        f"Check email for details."
    )

    twiml = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        "<Response>"
        f'<Say voice="Polly.Joanna" language="en-US">{message}</Say>'
        "</Response>"
    )

    return twiml


def _xml_escape(text: str) -> str:
    """Escape special XML characters to prevent injection."""
    if not text:
        return ""
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
        .replace("'", "&apos;")
    )
