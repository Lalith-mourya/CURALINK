"""
Chat tab component for the Healthcare Assistant.
Uses st.chat_message / st.chat_input for a modern conversational UI.
"""

import streamlit as st
from utils.session import add_message, get_messages, clear_messages, get_patient_profile, set_risk_status
from components.status_banner import render_risk_badge, render_escalation_status


def _render_welcome() -> None:
    """Render a friendly welcome message when the chat is empty."""
    st.markdown(
        """
        <div class="welcome-container">
            <div class="welcome-icon">🏥</div>
            <h2>Welcome to Healthcare Assistant</h2>
            <p>
                I'm here to help answer your health-related questions.
                Type a message below to get started.
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_chat_tab(api_client) -> None:
    """Main chat interface rendered inside the 💬 Chat tab."""



    # ── Message history ────────────────────────────────────────────
    messages = get_messages()

    if not messages:
        _render_welcome()
    else:
        for msg in messages:
            role = msg.get("role", "user")
            avatar = "🧑" if role == "user" else "🤖"
            with st.chat_message(role, avatar=avatar):
                st.markdown(msg["content"])

                # Timestamp + risk badge row
                extra_parts: list[str] = []
                ts = msg.get("timestamp")
                if ts:
                    extra_parts.append(f'<span class="chat-timestamp">{ts}</span>')
                risk = msg.get("risk_level", "safe")
                if risk and risk != "safe" and role == "assistant":
                    extra_parts.append(render_risk_badge(risk))
                if extra_parts:
                    st.markdown("  ".join(extra_parts), unsafe_allow_html=True)

    # ── Escalation card (below messages, above input) ──────────
    esc = st.session_state.get("last_escalation_status", {})
    if esc:
        render_escalation_status(esc)

    # ── Chat input ─────────────────────────────────────────────────
    profile = get_patient_profile()
    profile_set = bool(profile.get("patient_name"))

    if not profile_set:
        st.info("👤 Please set up your **Patient Profile** in the sidebar or Profile tab before chatting.")

    user_input = st.chat_input("Type your message…", disabled=not profile_set)

    if user_input:
        # 1. Persist & display user message
        add_message("user", user_input)
        with st.chat_message("user", avatar="🧑"):
            st.markdown(user_input)

        # 2. Call backend
        with st.chat_message("assistant", avatar="🤖"):
            with st.spinner("Thinking…"):
                # Build a lightweight history for context
                history = [
                    {"role": m["role"], "content": m["content"]}
                    for m in get_messages()[-20:]  # last 20 turns
                ]
                response = api_client.send_chat(
                    message=user_input,
                    patient_profile=profile,
                    message_history=history,
                )

            if response:
                reply = response.get("reply") or response.get("response") or response.get("message", "I'm sorry, I couldn't generate a response.")
                risk_level = response.get("risk_level", "safe")
                escalation = response.get("escalation_status", {})

                st.markdown(reply)

                # Badge
                if risk_level and risk_level != "safe":
                    st.markdown(render_risk_badge(risk_level), unsafe_allow_html=True)

                add_message("assistant", reply, risk_level=risk_level)
                set_risk_status(risk_level, escalation or {})

                if risk_level == "risky":
                    st.session_state["show_emergency_banner"] = True
                    st.rerun()
            else:
                fallback = "⚠️ I'm unable to reach the server right now. Please try again in a moment."
                st.error(fallback)
                add_message("assistant", fallback, risk_level="safe")
