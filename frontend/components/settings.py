"""
Settings tab for overriding API credentials in the Healthcare Assistant.
"""

import streamlit as st


def render_settings_tab(api_client) -> None:
    """Render the API keys configuration and health checks UI."""
    st.write("### ⚙️ API Credentials Configuration")
    st.markdown(
        """
        Use this panel to customize API keys for LLM inference, email alerts, and voice calls.
        If left blank, the system falls back to default server-side settings from the backend `.env` file.
        All keys are stored temporarily in your session and passed securely via request headers.
        """
    )

    # Fetch backend configuration status
    health = api_client.health_check()
    backend_online = health is not None

    groq_backend = False
    resend_backend = False
    twilio_backend = False
    llm_connected = False

    if backend_online:
        groq_backend = health.get("groq_configured", False)
        resend_backend = health.get("resend_configured", False)
        twilio_backend = health.get("twilio_configured", False)
        llm_connected = health.get("ollama_status") == "connected"

    # UI overrides status
    groq_ui = bool(st.session_state.get("groq_api_key"))
    resend_ui = bool(st.session_state.get("resend_api_key"))
    twilio_ui = bool(
        st.session_state.get("twilio_account_sid")
        and st.session_state.get("twilio_auth_token")
        and st.session_state.get("twilio_phone_number")
    )

    st.markdown("#### 📊 Configuration Status Overview")

    col1, col2, col3 = st.columns(3)

    # Groq Badge Info
    with col1:
        st.markdown(
            f"""
            <div class="patient-card">
                <h3>🧠 Groq (LLM Engine)</h3>
                <div class="profile-field">
                    <span class="field-label">Backend Default</span>
                    <span class="field-value">{"✅ Available" if groq_backend else "❌ Missing"}</span>
                </div>
                <div class="profile-field">
                    <span class="field-label">UI Override</span>
                    <span class="field-value" style="color: {'#1e88e5' if groq_ui else '#94a3b8'}">
                        {"🔹 Active" if groq_ui else "None (Using Default)"}
                    </span>
                </div>
                <div class="profile-field">
                    <span class="field-label">Status</span>
                    <span class="field-value" style="color: {'#10b981' if llm_connected else '#ef4444'}">
                        {"🟢 Connected" if llm_connected else "🔴 Offline / Error"}
                    </span>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    # Resend Badge Info
    with col2:
        st.markdown(
            f"""
            <div class="patient-card">
                <h3>📧 Resend (Email Alerts)</h3>
                <div class="profile-field">
                    <span class="field-label">Backend Default</span>
                    <span class="field-value">{"✅ Available" if resend_backend else "❌ Missing"}</span>
                </div>
                <div class="profile-field">
                    <span class="field-label">UI Override</span>
                    <span class="field-value" style="color: {'#1e88e5' if resend_ui else '#94a3b8'}">
                        {"🔹 Active" if resend_ui else "None (Using Default)"}
                    </span>
                </div>
                <div class="profile-field">
                    <span class="field-label">Status</span>
                    <span class="field-value">
                        {"🟢 Configured" if (resend_backend or resend_ui) else "🔴 Unconfigured"}
                    </span>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    # Twilio Badge Info
    with col3:
        st.markdown(
            f"""
            <div class="patient-card">
                <h3>📞 Twilio (Voice Calls)</h3>
                <div class="profile-field">
                    <span class="field-label">Backend Default</span>
                    <span class="field-value">{"✅ Available" if twilio_backend else "❌ Missing"}</span>
                </div>
                <div class="profile-field">
                    <span class="field-label">UI Override</span>
                    <span class="field-value" style="color: {'#1e88e5' if twilio_ui else '#94a3b8'}">
                        {"🔹 Active" if twilio_ui else "None (Using Default)"}
                    </span>
                </div>
                <div class="profile-field">
                    <span class="field-label">Status</span>
                    <span class="field-value">
                        {"🟢 Configured" if (twilio_backend or twilio_ui) else "🔴 Unconfigured"}
                    </span>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.markdown("---")
    st.markdown("#### ✏️ Edit API Credentials")

    # Form/Inputs for entering values
    with st.container():
        # Groq section
        st.markdown("##### 🧠 Groq Credentials")
        st.text_input(
            "Groq API Key",
            type="password",
            key="groq_api_key",
            help="Your API Key from console.groq.com. Enables patient risk classification and RAG responses.",
        )

        st.markdown("##### 📧 Resend Credentials")
        st.text_input(
            "Resend API Key",
            type="password",
            key="resend_api_key",
            help="Your API Key from resend.com. Used to send urgent escalation emails to the doctor.",
        )

        st.markdown("##### 📞 Twilio Credentials")
        sub_col1, sub_col2, sub_col3 = st.columns(3)
        with sub_col1:
            st.text_input(
                "Twilio Account SID",
                key="twilio_account_sid",
                help="Your Twilio Account SID. Used to place emergency voice calls to the doctor.",
            )
        with sub_col2:
            st.text_input(
                "Twilio Auth Token",
                type="password",
                key="twilio_auth_token",
                help="Your Twilio Auth Token.",
            )
        with sub_col3:
            st.text_input(
                "Twilio Phone Number",
                key="twilio_phone_number",
                placeholder="+1234567890",
                help="Your Twilio phone number purchased or verified on your account.",
            )

    # Actions buttons
    st.markdown("<br>", unsafe_allow_html=True)
    act_col1, act_col2 = st.columns([0.2, 0.8])
    with act_col1:
        if st.button("🔄 Test Connection & Save", type="primary", use_container_width=True):
            st.toast("Testing backend connection with new keys...")
            st.rerun()

    with act_col2:
        if st.button("🗑️ Clear Overrides", use_container_width=True):
            st.session_state["groq_api_key"] = ""
            st.session_state["resend_api_key"] = ""
            st.session_state["twilio_account_sid"] = ""
            st.session_state["twilio_auth_token"] = ""
            st.session_state["twilio_phone_number"] = ""
            st.toast("Cleared all custom credential overrides. Resetting to backend defaults.")
            st.rerun()
