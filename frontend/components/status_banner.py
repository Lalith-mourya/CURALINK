"""
Status banners and badges for the Healthcare Assistant.
Renders disclaimers, risk badges, emergency banners, escalation checklists,
and backend health indicators.
"""

import streamlit as st


# ------------------------------------------------------------------ #
#  Disclaimer
# ------------------------------------------------------------------ #
def render_disclaimer() -> None:
    """Show the medical-information disclaimer at the top of the page."""
    st.markdown(
        """
        <div class="disclaimer-banner">
            <strong>⚕️ Medical Disclaimer:</strong>
            This assistant provides informational support only.
            It is <strong>not</strong> a replacement for professional medical advice,
            diagnosis, or treatment. Always consult a qualified healthcare provider
            for medical concerns.
        </div>
        """,
        unsafe_allow_html=True,
    )


# ------------------------------------------------------------------ #
#  Risk Badge
# ------------------------------------------------------------------ #
def render_risk_badge(risk_level: str) -> str:
    """Return an HTML snippet for a colored risk badge.

    Returns raw HTML — caller must use ``unsafe_allow_html=True``.
    """
    badges = {
        "safe": '<span class="risk-badge risk-safe">🟢 Safe</span>',
        "unclear": '<span class="risk-badge risk-unclear">🟡 Unclear</span>',
        "risky": '<span class="risk-badge risk-risky">🔴 Risky</span>',
    }
    return badges.get(risk_level, "")


# ------------------------------------------------------------------ #
#  Emergency Banner
# ------------------------------------------------------------------ #
def render_emergency_banner() -> None:
    """Full-width animated red banner when a risk event is active."""
    if not st.session_state.get("show_emergency_banner", False):
        return

    col1, col2 = st.columns([0.95, 0.05])
    with col1:
        st.markdown(
            """
            <div class="emergency-banner">
                <span class="emergency-icon">🚨</span>
                EMERGENCY ALERT: Risk Detected — Doctor has been notified.
                <span class="emergency-icon">🚨</span>
                <div class="emergency-sub">
                    If you are in immediate danger, please call <strong>911</strong> now.
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with col2:
        if st.button("✖", key="dismiss_emergency", help="Dismiss alert"):
            st.session_state["show_emergency_banner"] = False
            st.rerun()


# ------------------------------------------------------------------ #
#  Escalation Status
# ------------------------------------------------------------------ #
def render_escalation_status(status_dict: dict) -> None:
    """Render a checklist card showing which escalation actions fired."""
    if not status_dict:
        return

    import textwrap

    email_sent = status_dict.get("email_sent", False)
    call_triggered = status_dict.get("call_triggered", False)
    call_sid = status_dict.get("call_sid", "")

    email_icon = "✅" if email_sent else "❌"
    call_icon = "✅" if call_triggered else "❌"

    call_meta = f'<span class="status-meta">SID: {call_sid}</span>' if call_sid else ""

    html = f"""
    <div class="escalation-status">
        <h4>📋 Escalation Actions</h4>
        <div class="status-item">
            <span class="status-icon">{email_icon}</span>
            <span class="status-text">Email notification sent to doctor</span>
        </div>
        <div class="status-item">
            <span class="status-icon">{call_icon}</span>
            <span class="status-text">Emergency call triggered</span> {call_meta}
        </div>
    </div>
    """
    st.markdown(textwrap.dedent(html).strip(), unsafe_allow_html=True)


# ------------------------------------------------------------------ #
#  System Status (Sidebar)
# ------------------------------------------------------------------ #
def render_system_status(api_client) -> None:
    """Sidebar widget showing backend health indicators."""
    st.markdown("##### 🖥️ System Status")

    health = api_client.health_check()

    if health:
        api_status = health.get("api_status", "unknown")
        ollama = health.get("ollama_status", "unknown")
        db = health.get("db_status", "unknown")

        # API
        api_online = api_status in ("ok", "healthy", "running", "connected")
        dot_class_api = "online" if api_online else "offline"
        st.markdown(
            f"""
            <div class="health-indicator">
                <div class="health-dot {dot_class_api}"></div>
                <span>API Server: <strong>{'Online' if api_online else 'Offline'}</strong></span>
            </div>
            """,
            unsafe_allow_html=True,
        )

        # Ollama / LLM
        ollama_ok = str(ollama).lower() in ("ok", "connected", "healthy", "running", "true")
        dot_class_ollama = "online" if ollama_ok else "offline"
        st.markdown(
            f"""
            <div class="health-indicator">
                <div class="health-dot {dot_class_ollama}"></div>
                <span>LLM Engine: <strong>{'Connected' if ollama_ok else 'Disconnected'}</strong></span>
            </div>
            """,
            unsafe_allow_html=True,
        )

        # Database
        db_ok = str(db).lower() in ("ok", "connected", "healthy", "running", "true")
        dot_class_db = "online" if db_ok else "offline"
        st.markdown(
            f"""
            <div class="health-indicator">
                <div class="health-dot {dot_class_db}"></div>
                <span>Database: <strong>{'Connected' if db_ok else 'Disconnected'}</strong></span>
            </div>
            """,
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            """
            <div class="health-indicator">
                <div class="health-dot offline"></div>
                <span>Backend: <strong>Unreachable</strong></span>
            </div>
            """,
            unsafe_allow_html=True,
        )
        st.caption("⚠️ Cannot connect to the backend server.")
