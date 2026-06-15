"""
Patient Profile tab and sidebar widget.
"""

import streamlit as st
from utils.session import get_patient_profile, set_patient_profile


# ------------------------------------------------------------------ #
#  Full Profile Tab
# ------------------------------------------------------------------ #
def render_profile_tab(api_client) -> None:
    """Render the 👤 Patient Profile tab with form and current-profile card."""

    st.subheader("👤 Patient Profile")
    st.caption("Provide your details so the assistant can offer personalised guidance.")

    profile = get_patient_profile()

    # ── Current profile card ───────────────────────────────────────
    if profile.get("patient_name"):
        st.markdown(
            f"""
            <div class="patient-card">
                <h3>🩺 Current Profile</h3>
                <div class="profile-field">
                    <span class="field-label">Patient Name</span>
                    <span class="field-value">{profile.get('patient_name', '—')}</span>
                </div>
                <div class="profile-field">
                    <span class="field-label">Age</span>
                    <span class="field-value">{profile.get('age', '—')}</span>
                </div>
                <div class="profile-field">
                    <span class="field-label">Gender</span>
                    <span class="field-value">{profile.get('gender', '—') or '—'}</span>
                </div>
                <div class="profile-field">
                    <span class="field-label">Height</span>
                    <span class="field-value">{profile.get('height', '—')} cm</span>
                </div>
                <div class="profile-field">
                    <span class="field-label">Weight</span>
                    <span class="field-value">{profile.get('weight', '—')} kg</span>
                </div>
                <div class="profile-field">
                    <span class="field-label">Email</span>
                    <span class="field-value">{profile.get('email', '—') or '—'}</span>
                </div>
                <div class="profile-field">
                    <span class="field-label">Phone</span>
                    <span class="field-value">{profile.get('phone_number', '—')}</span>
                </div>
                <div class="profile-field">
                    <span class="field-label">Medical Issue / Concern</span>
                    <span class="field-value">{profile.get('medical_issue', '—') or '—'}</span>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        st.markdown("")

    # ── Edit form ──────────────────────────────────────────────────
    st.markdown("#### ✏️ Edit Profile")

    with st.form("patient_profile_form", clear_on_submit=False):
        col1, col2 = st.columns(2)

        with col1:
            st.markdown("##### **Personal Details**")
            patient_name = st.text_input(
                "Patient Name *",
                value=profile.get("patient_name", ""),
                placeholder="John Doe",
            )
            age = st.number_input(
                "Age",
                min_value=0,
                max_value=150,
                value=int(profile.get("age", 0)),
            )
            gender = st.selectbox(
                "Gender",
                options=["", "Male", "Female", "Other"],
                index=["", "Male", "Female", "Other"].index(profile.get("gender", "") if profile.get("gender", "") in ["Male", "Female", "Other"] else ""),
            )

        with col2:
            st.markdown("##### **Physical Metrics**")
            height = st.number_input(
                "Height (cm)",
                min_value=0.0,
                max_value=300.0,
                value=float(profile.get("height", 0.0)),
                step=0.1,
            )
            weight = st.number_input(
                "Weight (kg)",
                min_value=0.0,
                max_value=500.0,
                value=float(profile.get("weight", 0.0)),
                step=0.1,
            )

        st.markdown("##### **Contact Details & Medical Concern**")
        c1, c2 = st.columns(2)
        with c1:
            phone_number = st.text_input(
                "Phone Number *",
                value=profile.get("phone_number", ""),
                placeholder="+1 555-123-4567",
                help="Your contact number. For testing Twilio calls, this is used as the callback number.",
            )
        with c2:
            email = st.text_input(
                "Email Address",
                value=profile.get("email", ""),
                placeholder="john.doe@example.com",
            )

        medical_issue = st.text_area(
            "Explain your issue or medical concern (Optional)",
            value=profile.get("medical_issue", ""),
            height=100,
            placeholder="Briefly describe what issue or symptoms you are experiencing...",
        )

        submitted = st.form_submit_button(
            "💾 Save Profile",
            use_container_width=True,
            type="primary",
        )

        if submitted:
            # Validation
            errors: list[str] = []
            if not patient_name.strip():
                errors.append("Patient Name is required.")
            if not phone_number.strip():
                errors.append("Phone Number is required.")

            if errors:
                for err in errors:
                    st.error(f"❌ {err}")
            else:
                new_profile = {
                    "patient_name": patient_name.strip(),
                    "age": age,
                    "gender": gender,
                    "height": height,
                    "weight": weight,
                    "phone_number": phone_number.strip(),
                    "email": email.strip(),
                    "medical_issue": medical_issue.strip(),
                    # Compatibility placeholders for legacy doctor schema fields
                    "doctor_name": "",
                    "doctor_email": "",
                    "doctor_phone": "",
                    "emergency_contact": "",
                    "current_medicines": [],
                    "special_instructions": "",
                }
                # Check for existing patient same-name conflict
                # Query backend for any existing incidents or chat logs with the same name
                existing_by_name = api_client.get_incidents(patient_name=patient_name.strip())
                conflict_found = False
                phone_matched = False
                
                if existing_by_name:
                    # Let's inspect the phone numbers in existing records
                    for inc in existing_by_name:
                        existing_phone = inc.get("patient_phone")
                        if existing_phone:
                            if existing_phone.strip() == phone_number.strip():
                                phone_matched = True
                                break
                            else:
                                conflict_found = True
                else:
                    # Check chat history too just in case
                    existing_chats = api_client.get_chat_history(patient_name=patient_name.strip())
                    if existing_chats:
                        for ch in existing_chats:
                            existing_phone = ch.get("patient_phone")
                            if existing_phone:
                                if existing_phone.strip() == phone_number.strip():
                                    phone_matched = True
                                    break
                                else:
                                    conflict_found = True

                with st.spinner("Saving profile to database..."):
                    saved_db_profile = api_client.register_patient(new_profile)
                if saved_db_profile:
                    new_profile["patient_id"] = saved_db_profile.get("patient_id", "")
                    new_profile["created_at"] = saved_db_profile.get("created_at", "")
                    new_profile["last_login"] = saved_db_profile.get("last_login", "")
                    new_profile["profile_status"] = saved_db_profile.get("profile_status", "Active")

                set_patient_profile(new_profile)
                st.success("✅ Profile saved successfully!")
                
                if conflict_found and not phone_matched:
                    st.info(
                        f"ℹ️ **New Patient Profile**: A new record has been created. Since the phone number "
                        f"({phone_number.strip()}) is different, your documents, chat logs, and medical "
                        f"files will be kept completely separate from the existing patient named *{patient_name.strip()}*."
                    )
                elif phone_matched or (existing_by_name or existing_chats):
                    st.info(
                        f"ℹ️ **Existing Profile Loaded**: Resuming session for patient *{patient_name.strip()}* "
                        f"with phone {phone_number.strip()}. You can continue adding care documents "
                        f"or chat with the assistant under the active care plan."
                    )
                st.balloons()
                st.rerun()


# ------------------------------------------------------------------ #
#  Compact Sidebar Widget
# ------------------------------------------------------------------ #
def render_sidebar_profile(api_client=None) -> None:
    """Compact patient summary for the sidebar and editing options."""
    profile = get_patient_profile()
    name = profile.get("patient_name", "")

    if name:
        st.markdown(
            f"""
            <div class="metric-card">
                <div class="metric-label">Patient</div>
                <div class="metric-value">👤 {name}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        age = profile.get("age", 0)
        gender = profile.get("gender", "")
        if age or gender:
            gender_val = f" / {gender}" if gender else ""
            st.markdown(
                f"""
                <div class="metric-card">
                    <div class="metric-label">Age / Gender</div>
                    <div class="metric-value">{age or '—'}y{gender_val}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )

        # Risk level
        risk = st.session_state.get("last_risk_level", "none")
        if risk and risk != "none":
            risk_colors = {"safe": "#10b981", "unclear": "#f59e0b", "risky": "#ef4444"}
            risk_labels = {"safe": "Safe", "unclear": "Unclear", "risky": "Risky"}
            color = risk_colors.get(risk, "#94a3b8")
            label = risk_labels.get(risk, risk.title())
            st.markdown(
                f"""
                <div class="metric-card" style="border-left: 3px solid {color};">
                    <div class="metric-label">Last Risk Level</div>
                    <div class="metric-value" style="color: {color};">{label}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )

        st.markdown("<br>", unsafe_allow_html=True)
        # Edit Profile Expander in sidebar
        with st.expander("✏️ Edit Profile Details"):
            with st.form("patient_sidebar_profile_form", clear_on_submit=False):
                patient_name = st.text_input(
                    "Patient Name *",
                    value=profile.get("patient_name", ""),
                    placeholder="John Doe",
                    key="sb_name"
                )
                age = st.number_input(
                    "Age",
                    min_value=0,
                    max_value=150,
                    value=int(profile.get("age", 0)),
                    key="sb_age"
                )
                gender = st.selectbox(
                    "Gender",
                    options=["", "Male", "Female", "Other"],
                    index=["", "Male", "Female", "Other"].index(profile.get("gender", "") if profile.get("gender", "") in ["Male", "Female", "Other"] else ""),
                    key="sb_gender"
                )
                height = st.number_input(
                    "Height (cm)",
                    min_value=0.0,
                    max_value=300.0,
                    value=float(profile.get("height", 0.0)),
                    step=0.1,
                    key="sb_height"
                )
                weight = st.number_input(
                    "Weight (kg)",
                    min_value=0.0,
                    max_value=500.0,
                    value=float(profile.get("weight", 0.0)),
                    step=0.1,
                    key="sb_weight"
                )
                phone_number = st.text_input(
                    "Phone Number *",
                    value=profile.get("phone_number", ""),
                    placeholder="+1 555-123-4567",
                    key="sb_phone"
                )
                email = st.text_input(
                    "Email Address",
                    value=profile.get("email", ""),
                    placeholder="john.doe@example.com",
                    key="sb_email"
                )
                medical_issue = st.text_area(
                    "Explain issue (Optional)",
                    value=profile.get("medical_issue", ""),
                    placeholder="Describe your symptoms...",
                    key="sb_issue"
                )

                submitted = st.form_submit_button(
                    "💾 Save Changes",
                    use_container_width=True,
                    type="primary",
                )

                if submitted:
                    errors = []
                    if not patient_name.strip():
                        errors.append("Name is required.")
                    if not phone_number.strip():
                        errors.append("Phone is required.")

                    if errors:
                        for err in errors:
                            st.error(err)
                    else:
                        new_profile = {
                            "patient_name": patient_name.strip(),
                            "age": age,
                            "gender": gender,
                            "height": height,
                            "weight": weight,
                            "phone_number": phone_number.strip(),
                            "email": email.strip(),
                            "medical_issue": medical_issue.strip(),
                            # Compatibility placeholders
                            "doctor_name": "",
                            "doctor_email": "",
                            "doctor_phone": "",
                            "emergency_contact": "",
                            "current_medicines": [],
                            "special_instructions": "",
                        }
                        if api_client:
                            with st.spinner("Saving changes to database..."):
                                saved_db_profile = api_client.register_patient(new_profile)
                            if saved_db_profile:
                                new_profile["patient_id"] = saved_db_profile.get("patient_id", "")
                                new_profile["created_at"] = saved_db_profile.get("created_at", "")
                                new_profile["last_login"] = saved_db_profile.get("last_login", "")
                                new_profile["profile_status"] = saved_db_profile.get("profile_status", "Active")
                        set_patient_profile(new_profile)
                        st.success("✅ Changes saved!")
                        st.rerun()
    else:
        st.warning("⚠️ Patient profile not set.")
