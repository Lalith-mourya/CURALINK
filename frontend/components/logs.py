"""
Logs tab — view incidents and chat history.
"""

import streamlit as st
import pandas as pd
from components.status_banner import render_risk_badge


def render_logs_tab(api_client) -> None:
    """Render the 📋 Logs tab with incident list and chat history."""

    st.subheader("📋 Incident Logs & Chat History")
    st.caption("Review flagged incidents and past conversations.")

    # ── Filters ────────────────────────────────────────────────────
    col_risk, col_name, col_phone, col_refresh = st.columns([1, 1, 1, 0.6])

    with col_risk:
        risk_filter = st.selectbox(
            "Risk Level",
            options=["All", "safe", "unclear", "risky"],
            index=0,
            key="log_risk_filter",
        )
    with col_name:
        name_filter = st.text_input(
            "Patient Name",
            key="log_name_filter",
            placeholder="Filter by name…",
        )
    with col_phone:
        phone_filter = st.text_input(
            "Patient Phone",
            key="log_phone_filter",
            placeholder="Filter by phone…",
        )
    with col_refresh:
        st.write("")  # spacer
        st.write("")
        refresh = st.button("🔄 Refresh", key="btn_refresh_logs", use_container_width=True)

    st.divider()

    # ── Incidents ──────────────────────────────────────────────────
    st.markdown("#### 🚨 Incidents")

    risk_arg = risk_filter if risk_filter != "All" else None
    name_arg = name_filter.strip() or None
    phone_arg = phone_filter.strip() or None

    incidents = api_client.get_incidents(patient_name=name_arg, risk_level=risk_arg, patient_phone=phone_arg)

    if incidents:
        # Build a DataFrame for the table view
        rows = []
        for inc in incidents:
            if isinstance(inc, dict):
                rows.append({
                    "Timestamp": inc.get("timestamp", inc.get("created_at", "—")),
                    "Patient": inc.get("patient_name", "—"),
                    "Phone": inc.get("patient_phone", "—"),
                    "Risk Level": inc.get("risk_level", "—"),
                    "Message": inc.get("message", inc.get("trigger_message", "—"))[:120],
                    "Status": inc.get("status", "—"),
                })
            else:
                rows.append({"Info": str(inc)})

        df = pd.DataFrame(rows)

        # Color-code risk column
        def _highlight_risk(val):
            colors = {
                "safe": "background-color: rgba(16,185,129,0.15); color: #10b981;",
                "unclear": "background-color: rgba(245,158,11,0.15); color: #f59e0b;",
                "risky": "background-color: rgba(239,68,68,0.15); color: #ef4444;",
            }
            return colors.get(str(val).lower(), "")

        if "Risk Level" in df.columns:
            if hasattr(df.style, "map"):
                styled = df.style.map(_highlight_risk, subset=["Risk Level"])
            else:
                styled = df.style.applymap(_highlight_risk, subset=["Risk Level"])
            st.dataframe(styled, use_container_width=True, hide_index=True)
        else:
            st.dataframe(df, use_container_width=True, hide_index=True)

        # Expandable details
        st.markdown("##### 🔍 Incident Details")
        for i, inc in enumerate(incidents):
            if isinstance(inc, dict):
                label = f"{inc.get('timestamp', inc.get('created_at', ''))}: {inc.get('patient_name', 'Unknown')} — {inc.get('risk_level', '').upper()}"
                with st.expander(label, expanded=False):
                    st.json(inc)
    else:
        st.markdown(
            """
            <div class="empty-state">
                <div class="empty-icon">📋</div>
                <p>No incidents found matching your filters.<br>Incidents are logged when risk is detected in patient messages.</p>
            </div>
            """,
            unsafe_allow_html=True,
        )

    # ── Chat History ───────────────────────────────────────────────
    st.divider()
    st.markdown("#### 💬 Recent Chat History")

    history = api_client.get_chat_history(patient_name=name_arg, patient_phone=phone_arg)

    if history:
        for entry in history[-30:]:  # show last 30
            if isinstance(entry, dict):
                role = entry.get("role", "unknown")
                content = entry.get("content") or entry.get("message", "")
                ts = entry.get("timestamp", "")
                risk = entry.get("risk_level", "safe")

                icon = "🧑" if role == "user" else "🤖"
                with st.chat_message(role, avatar=icon):
                    st.markdown(content)
                    extras = []
                    if ts:
                        extras.append(f'<span class="chat-timestamp">{ts}</span>')
                    if risk and risk != "safe":
                        extras.append(render_risk_badge(risk))
                    if extras:
                        st.markdown("  ".join(extras), unsafe_allow_html=True)
            else:
                st.text(str(entry))
    else:
        st.markdown(
            """
            <div class="empty-state">
                <div class="empty-icon">💬</div>
                <p>No chat history available yet.</p>
            </div>
            """,
            unsafe_allow_html=True,
        )
