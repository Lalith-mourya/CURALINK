"""
Healthcare Assistant — Streamlit Frontend (dashboard/main_ui.py copy)
==========================================
Main entry point. Run with:
    streamlit run dashboard/main_ui.py
"""

import os
import sys
import streamlit as st

# ---------------------------------------------------------------------------
#  Ensure the `frontend/`, `dashboard/` and root directories are on sys.path
# ---------------------------------------------------------------------------
_DASHBOARD_DIR = os.path.dirname(os.path.abspath(__file__))
_ROOT_DIR = os.path.dirname(_DASHBOARD_DIR)
_FRONTEND_DIR = os.path.join(_ROOT_DIR, "frontend")

if _FRONTEND_DIR not in sys.path:
    sys.path.insert(0, _FRONTEND_DIR)

if _ROOT_DIR not in sys.path:
    sys.path.insert(0, _ROOT_DIR)

from utils.api_client import APIClient
from utils.session import init_session_state
from components.status_banner import (
    render_disclaimer,
    render_emergency_banner,
    render_system_status,
)
from components.chat import render_chat_tab
from components.documents import render_documents_tab
from components.patient_profile import render_profile_tab, render_sidebar_profile
from components.doctor_dashboard import render_doctor_dashboard
from dashboard.auth_ui import render_auth_page, render_api_gateway_screen


# ====================================================================== #
#  Page Config (must be the very first Streamlit call)
# ====================================================================== #
st.set_page_config(
    page_title="Healthcare Assistant",
    page_icon="🏥",
    layout="wide",
    initial_sidebar_state="expanded",
)


# ====================================================================== #
#  Load & Inject Custom CSS
# ====================================================================== #
def _load_css() -> None:
    css_path = os.path.join(_FRONTEND_DIR, "assets", "style.css")
    try:
        with open(css_path, "r", encoding="utf-8") as f:
            css = f.read()
        st.markdown(f"<style>{css}</style>", unsafe_allow_html=True)
    except FileNotFoundError:
        st.warning("⚠️ Custom stylesheet not found — using default Streamlit theme.")


_load_css()


# ====================================================================== #
#  Session State & API Client
# ====================================================================== #
init_session_state()
api_client = APIClient()


# ====================================================================== #
#  Gatekeeper / API Gateway check
# ====================================================================== #
api_gateway_keys = [
    "groq_api_key",
    "resend_api_key",
    "twilio_account_sid",
    "twilio_auth_token",
    "twilio_phone_number"
]
has_gateway_keys = all(st.session_state.get(k) for k in api_gateway_keys)

if not has_gateway_keys:
    render_api_gateway_screen()
    st.stop()


# ====================================================================== #
#  Gatekeeper / Auth check
# ====================================================================== #
if not st.session_state.get("logged_in"):
    render_auth_page()
    st.stop()

# If logged in, perform token validation
try:
    verification = api_client.verify_token()
    if not verification or not verification.get("valid"):
        st.session_state.clear()
        init_session_state()
        st.rerun()
except Exception:
    # backend is down or unreachable; fallback to offline mode
    pass


def logout_action() -> None:
    """Clear session token from backend, wipe local state, and redirect to login."""
    try:
        api_client.logout_user()
    except Exception:
        pass
    st.session_state.clear()
    init_session_state()
    st.rerun()


# ====================================================================== #
#  Role Selection
# ====================================================================== #
role = st.session_state.get("role")

if role is None:
    st.markdown("<h1 style='text-align: center; color: #1e88e5; margin-top: 50px;'>🏥 Healthcare Assistant</h1>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center; color: #94a3b8; font-size: 1.1rem;'>Welcome! Please select your portal to proceed.</p>", unsafe_allow_html=True)
    st.markdown("<br><br>", unsafe_allow_html=True)
    
    col1, col2, col3, col4, col5 = st.columns([0.1, 0.35, 0.1, 0.35, 0.1])
    with col2:
        st.markdown(
            """
            <div style="background-color: #1e2538; padding: 30px; border-radius: 12px; border: 1px solid #2d3748; text-align: center; height: 260px;">
                <div style="font-size: 3rem; margin-bottom: 15px;">👤</div>
                <h3 style="color: #42a5f5; margin-bottom: 10px;">Patient Portal</h3>
                <p style="color: #94a3b8; font-size: 0.9rem;">Chat with your AI care assistant, upload care plans, and review your profile details.</p>
            </div>
            """,
            unsafe_allow_html=True
        )
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("Enter Patient Portal", type="primary", use_container_width=True):
            st.session_state["role"] = "patient"
            st.rerun()
            
    with col4:
        st.markdown(
            """
            <div style="background-color: #1e2538; padding: 30px; border-radius: 12px; border: 1px solid #2d3748; text-align: center; height: 260px;">
                <div style="font-size: 3rem; margin-bottom: 15px;">🩺</div>
                <h3 style="color: #10b981; margin-bottom: 10px;">Doctor Portal</h3>
                <p style="color: #94a3b8; font-size: 0.9rem;">Monitor patient escalation logs, track safety incident alerts, and check real-time system diagnostics.</p>
            </div>
            """,
            unsafe_allow_html=True
        )
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("Enter Doctor Portal", type="primary", use_container_width=True):
            st.session_state["role"] = "doctor"
            st.rerun()

elif role == "patient":
    profile = st.session_state.get("patient_profile", {})
    patient_filled = bool(profile.get("patient_name") and profile.get("phone_number"))

    if not patient_filled:
        # First force profile setup in patient portal
        st.markdown("<h1 style='text-align: center; color: #1e88e5; margin-top: 20px;'>🏥 Patient Portal Setup</h1>", unsafe_allow_html=True)
        st.markdown("<p style='text-align: center; color: #94a3b8; font-size: 1.05rem;'>Please configure your patient profile and medical details below to unlock your dashboard.</p>", unsafe_allow_html=True)
        st.markdown("<br>", unsafe_allow_html=True)
        
        render_profile_tab(api_client)
        
        st.markdown("<hr style='border: 1px solid #2d3748;'>", unsafe_allow_html=True)
        if st.button("🚪 Logout", use_container_width=True):
            logout_action()
    else:
        # Render Patient Application Layout
        with st.sidebar:
            st.markdown("# 🏥 Patient Portal")
            st.caption("AI-powered medical support companion")
            st.markdown("---")

            # -- Patient summary ---------------------------------------------------
            render_sidebar_profile()

            st.markdown("---")

            # -- System health -----------------------------------------------------
            render_system_status(api_client)

            st.markdown("---")

            # Logout button in sidebar
            if st.button("🚪 Logout", use_container_width=True):
                logout_action()

            st.markdown("---")
            st.markdown(
                """
                <div class="app-footer">
                    <strong>Healthcare Assistant</strong> v1.0.0<br>
                    © 2026 — All rights reserved.
                </div>
                """,
                unsafe_allow_html=True,
            )

        # Main Area for Patient
        render_disclaimer()
        render_emergency_banner()
        render_chat_tab(api_client)

elif role == "doctor":
    # Render Doctor Application Layout
    with st.sidebar:
        st.markdown("# 🩺 Doctor Portal")
        st.caption("Safety logs & system monitoring")
        st.markdown("---")

        st.markdown("##### 👩‍⚕️ Doctor Dashboard Active")
        st.markdown("---")

        # -- System health -----------------------------------------------------
        render_system_status(api_client)

        st.markdown("---")

        # Logout button in sidebar
        if st.button("🚪 Logout", use_container_width=True):
            logout_action()

        st.markdown("---")
        st.markdown(
            """
            <div class="app-footer">
                <strong>Healthcare Assistant</strong> v1.0.0<br>
                © 2026 — All rights reserved.
            </div>
            """,
            unsafe_allow_html=True,
        )

    # Main Area for Doctor
    render_disclaimer()
    
    render_doctor_dashboard(api_client)
