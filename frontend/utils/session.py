"""
Session-state helpers for the Healthcare Assistant Streamlit app.
Provides typed accessors so every component uses a single source of truth.
"""

from datetime import datetime
import streamlit as st


# ------------------------------------------------------------------ #
#  Defaults
# ------------------------------------------------------------------ #
_DEFAULT_PROFILE: dict = {
    "patient_name": "",
    "age": 0,
    "gender": "",
    "height": 0.0,
    "weight": 0.0,
    "phone_number": "",
    "email": "",
    "medical_issue": "",
    "doctor_name": "",
    "doctor_email": "",
    "doctor_phone": "",
    "emergency_contact": "",
    "current_medicines": [],
    "special_instructions": "",
}

_SESSION_DEFAULTS: dict = {
    "messages": [],
    "patient_profile": dict(_DEFAULT_PROFILE),
    "last_risk_level": "none",
    "last_escalation_status": {},
    "show_emergency_banner": False,
    "uploaded_documents": [],
    "groq_api_key": "",
    "resend_api_key": "",
    "twilio_account_sid": "",
    "twilio_auth_token": "",
    "twilio_phone_number": "",
    "role": None,  # role selection: None, 'patient', or 'doctor'
    "session_token": None,
    "phone": None,
    "user_id": None,
    "doctor_id": "",
    "name": None,
    "logged_in": False,
}


# ------------------------------------------------------------------ #
#  Initialization
# ------------------------------------------------------------------ #
def init_session_state() -> None:
    """Ensure every expected key exists in ``st.session_state``."""
    for key, default in _SESSION_DEFAULTS.items():
        if key not in st.session_state:
            # Use a fresh copy for mutable defaults
            if isinstance(default, (list, dict)):
                st.session_state[key] = type(default)(default)
            else:
                st.session_state[key] = default


# ------------------------------------------------------------------ #
#  Patient Profile
# ------------------------------------------------------------------ #
def get_patient_profile() -> dict:
    """Return the current patient profile dict."""
    return st.session_state.get("patient_profile", dict(_DEFAULT_PROFILE))


def set_patient_profile(profile_dict: dict) -> None:
    """Persist an updated patient profile."""
    st.session_state["patient_profile"] = profile_dict


# ------------------------------------------------------------------ #
#  Messages
# ------------------------------------------------------------------ #
def add_message(
    role: str,
    content: str,
    risk_level: str = "safe",
    timestamp: str | None = None,
) -> None:
    """Append a message to the conversation history."""
    if "messages" not in st.session_state:
        st.session_state["messages"] = []
    st.session_state["messages"].append(
        {
            "role": role,
            "content": content,
            "risk_level": risk_level,
            "timestamp": timestamp or datetime.now().strftime("%I:%M %p"),
        }
    )


def get_messages() -> list:
    """Return the full message list."""
    return st.session_state.get("messages", [])


def clear_messages() -> None:
    """Wipe conversation history and reset emergency banner."""
    st.session_state["messages"] = []
    st.session_state["show_emergency_banner"] = False
    st.session_state["last_risk_level"] = "none"
    st.session_state["last_escalation_status"] = {}


# ------------------------------------------------------------------ #
#  Risk Status
# ------------------------------------------------------------------ #
def set_risk_status(risk_level: str, escalation_status: dict) -> None:
    """Update risk-related session state."""
    st.session_state["last_risk_level"] = risk_level
    st.session_state["last_escalation_status"] = escalation_status
    if risk_level == "risky":
        st.session_state["show_emergency_banner"] = True
