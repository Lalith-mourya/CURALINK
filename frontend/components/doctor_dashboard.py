"""
Doctor Dashboard Component.
Displays a responsive grid of registered patients, instant search, filters, and detailed patient profile modals.
"""

from datetime import datetime
import streamlit as st
from components.status_banner import render_risk_badge


@st.dialog("📄 View / Edit Document", width="large")
def _show_edit_document_dialog(api_client, phone, filename, name):
    st.markdown(f"**Patient:** {name} | **File:** `{filename}`")
    
    # Fetch content and cache it
    if "doc_content_cache" not in st.session_state or st.session_state.get("doc_content_file") != filename:
        with st.spinner("Reading file content..."):
            res = api_client.get_document_content(phone, filename, name)
            st.session_state["doc_content_cache"] = res.get("content", "") if res else ""
            st.session_state["doc_content_file"] = filename

    content = st.session_state.get("doc_content_cache", "")
    
    edited_text = st.text_area("Document Content (Plain Text)", value=content, height=350)
    
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    if ext in ("pdf", "docx"):
        st.info("⚠️ Saving changes will save this as a `.txt` file and delete the original binary file.")

    col1, col2 = st.columns(2)
    with col1:
        if st.button("💾 Save Changes", type="primary", use_container_width=True):
            with st.spinner("Updating document..."):
                res = api_client.update_document_content(phone, filename, edited_text, name)
                if res and res.get("status") == "success":
                    st.success("Document updated!")
                    st.session_state["editing_doc"] = None
                    if "doc_content_cache" in st.session_state:
                        del st.session_state["doc_content_cache"]
                        del st.session_state["doc_content_file"]
                    st.rerun()
                else:
                    st.error("Failed to save changes.")
    with col2:
        if st.button("❌ Cancel", use_container_width=True):
            st.session_state["editing_doc"] = None
            if "doc_content_cache" in st.session_state:
                del st.session_state["doc_content_cache"]
                del st.session_state["doc_content_file"]
            st.rerun()


def render_doctor_dashboard(api_client) -> None:
    """Render the Doctor Dashboard for patient profile management."""
    # Ensure view state is initialized
    if "viewing_patient" not in st.session_state:
        st.session_state["viewing_patient"] = None

    viewing_phone = st.session_state["viewing_patient"]

    # ------------------------------------------------------------------ #
    #  Detailed Profile Modal / View
    # ------------------------------------------------------------------ #
    if viewing_phone:
        _render_detailed_patient_profile(api_client, viewing_phone)
        return

    # ------------------------------------------------------------------ #
    #  Main Dashboard List View
    # ------------------------------------------------------------------ #
    st.subheader("👥 Patient Profiles Dashboard")
    st.caption("Access and manage registered patient records in the database.")

    # Fetch patients dynamically
    with st.spinner("Fetching patient profiles..."):
        patients = api_client.get_patients()

    if not patients:
        st.markdown(
            """
            <div class="empty-state">
                <div class="empty-icon">👥</div>
                <h3>No Patient Profiles Found</h3>
                <p>Patients will appear here after registration.</p>
            </div>
            """,
            unsafe_allow_html=True,
        )
        return

    # ── Search & Filter Controls ───────────────────────────────────
    st.markdown("#### 🔍 Search & Filters")
    
    # Search Bar
    search_query = st.text_input(
        "Search by Name, Patient ID, or Email",
        placeholder="Type to search patients...",
        key="search_pat_dashboard",
    ).strip().lower()

    # Filter columns
    f_col1, f_col2, f_col3 = st.columns(3)
    with f_col1:
        gender_filter = st.selectbox(
            "⚧ Gender",
            options=["All", "Male", "Female", "Other"],
            key="fil_gender",
        )
    with f_col2:
        age_filter = st.selectbox(
            "🎂 Age Group",
            options=["All", "Under 18", "18-35", "36-60", "60+"],
            key="fil_age",
        )
    with f_col3:
        status_filter = st.selectbox(
            "🟢 Profile Status",
            options=["All", "Active", "Inactive"],
            key="fil_status",
        )

    # ── Apply Filtering ────────────────────────────────────────────
    filtered = []
    for pat in patients:
        name = pat.get("name", "").lower()
        pid = pat.get("patient_id", "").lower()
        email = pat.get("email", "").lower()
        gender = pat.get("gender", "")
        age = pat.get("age", 0)
        status = pat.get("profile_status", "Active")

        # Search Query Match
        if search_query:
            if search_query not in name and search_query not in pid and search_query not in email:
                continue

        # Gender Match
        if gender_filter != "All" and gender != gender_filter:
            continue

        # Status Match
        if status_filter != "All" and status != status_filter:
            continue

        # Age Group Match
        if age_filter != "All":
            if age_filter == "Under 18" and age >= 18:
                continue
            elif age_filter == "18-35" and not (18 <= age <= 35):
                continue
            elif age_filter == "36-60" and not (36 <= age <= 60):
                continue
            elif age_filter == "60+" and age <= 60:
                continue

        filtered.append(pat)

    st.markdown(f"**Found {len(filtered)} matching patient profiles**")
    st.markdown("<br>", unsafe_allow_html=True)

    # ── Cards Grid Layout ──────────────────────────────────────────
    if not filtered:
        st.info("No patient profiles matched your search or filters.")
        return

    # Responsive Grid (3 Columns)
    cols = st.columns(3)
    for idx, pat in enumerate(filtered):
        col = cols[idx % 3]
        with col:
            name = pat.get("name", "Unknown Patient")
            pid = pat.get("patient_id", "—")
            email = pat.get("email", "—") or "—"
            phone = pat.get("phone", "—")
            age = pat.get("age", "—")
            gender = pat.get("gender", "—") or "—"
            
            created_raw = pat.get("created_at", "")
            try:
                # Format: 2026-06-15 11:24:00 -> Jun 15, 2026
                dt = datetime.fromisoformat(created_raw.replace("Z", "+00:00"))
                reg_date = dt.strftime("%b %d, %Y")
            except Exception:
                reg_date = created_raw or "—"

            st.markdown(
                f"""
                <div class="patient-card">
                    <h3 style="margin-top:0; color: #42a5f5;">👤 {name}</h3>
                    <div class="profile-field">
                        <span class="field-label">Patient ID</span>
                        <span class="field-value" style="font-family: monospace; font-weight: bold; color: #fafafa;">{pid}</span>
                    </div>
                    <div class="profile-field">
                        <span class="field-label">Gender / Age</span>
                        <span class="field-value">{gender} / {age} yrs</span>
                    </div>
                    <div class="profile-field">
                        <span class="field-label">Phone</span>
                        <span class="field-value">{phone}</span>
                    </div>
                    <div class="profile-field">
                        <span class="field-label">Email</span>
                        <span class="field-value">{email}</span>
                    </div>
                    <div class="profile-field" style="border-bottom: none;">
                        <span class="field-label">Registered</span>
                        <span class="field-value">{reg_date}</span>
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )
            # Action button
            if st.button("👁️ View Profile", key=f"vp_btn_{phone}", use_container_width=True):
                st.session_state["viewing_patient"] = phone
                st.rerun()


def _render_detailed_patient_profile(api_client, phone: str) -> None:
    """Render the detailed profile modal view for a patient."""
    st.markdown("### 🩺 Detailed Patient File")
    
    with st.spinner("Fetching profile details..."):
        pat = api_client.get_patient_details(phone)

    if not pat:
        st.error("Error retrieving detailed patient profile.")
        if st.button("⬅️ Back to Patient List"):
            st.session_state["viewing_patient"] = None
            st.rerun()
        return

    # Back button at the top
    if st.button("⬅️ Back to Patient List", key="btn_back_top"):
        st.session_state["viewing_patient"] = None
        st.rerun()

    # Formatted layouts
    name = pat.get("name", "—")
    pid = pat.get("patient_id", "—")
    email = pat.get("email", "—") or "—"
    age = pat.get("age", "—")
    gender = pat.get("gender", "—") or "—"
    height = pat.get("height", 0.0)
    weight = pat.get("weight", 0.0)
    blood_group = pat.get("blood_group", "—") or "—"
    address = pat.get("address", "—") or "—"
    
    medical_issue = pat.get("medical_issue", "—") or "—"
    status = pat.get("profile_status", "Active")
    
    created_raw = pat.get("created_at", "")
    last_raw = pat.get("last_login", "")

    # Medications and special instructions
    meds_list = pat.get("medicines", [])
    if isinstance(meds_list, str):
        try:
            import json
            meds_list = json.loads(meds_list)
        except Exception:
            meds_list = [meds_list]
    meds_str = ", ".join(meds_list) if meds_list else "No active care meds"
    special_instr = pat.get("special_instructions", "—") or "—"

    # Date formatting
    try:
        reg_date = datetime.fromisoformat(created_raw.replace("Z", "+00:00")).strftime("%B %d, %Y, %I:%M %p")
    except Exception:
        reg_date = created_raw or "—"

    try:
        last_login = datetime.fromisoformat(last_raw.replace("Z", "+00:00")).strftime("%B %d, %Y, %I:%M %p")
    except Exception:
        last_login = last_raw or "—"

    tab1, tab2, tab3 = st.tabs(["👤 Patient Details", "📄 Document Details", "📋 Logs"])

    with tab1:
        col_a, col_b = st.columns(2)

        with col_a:
            st.markdown(
                f"""
                <div class="patient-card" style="border-left: 4px solid #42a5f5;">
                    <h3 style="color: #42a5f5; margin-bottom: 20px;">👤 Patient Information</h3>
                    <div class="profile-field"><span class="field-label">Full Name</span><span class="field-value">{name}</span></div>
                    <div class="profile-field"><span class="field-label">Patient ID</span><span class="field-value" style="font-family: monospace; font-weight:bold;">{pid}</span></div>
                    <div class="profile-field"><span class="field-label">Email Address</span><span class="field-value">{email}</span></div>
                    <div class="profile-field"><span class="field-label">Phone Number</span><span class="field-value">{phone}</span></div>
                    <div class="profile-field"><span class="field-label">Age</span><span class="field-value">{age} years</span></div>
                    <div class="profile-field"><span class="field-label">Gender</span><span class="field-value">{gender}</span></div>
                    <div class="profile-field"><span class="field-label">Height</span><span class="field-value">{height} cm</span></div>
                    <div class="profile-field"><span class="field-label">Weight</span><span class="field-value">{weight} kg</span></div>
                    <div class="profile-field"><span class="field-label">Blood Group</span><span class="field-value">{blood_group}</span></div>
                    <div class="profile-field" style="border-bottom:none;"><span class="field-label">Address</span><span class="field-value">{address}</span></div>
                </div>
                """,
                unsafe_allow_html=True,
            )

        with col_b:
            st.markdown(
                f"""
                <div class="patient-card" style="border-left: 4px solid #ef4444;">
                    <h3 style="color: #ef4444; margin-bottom: 20px;">📋 Medical Information</h3>
                    <div class="profile-field" style="flex-direction: column; align-items: flex-start; height: auto;">
                        <span class="field-label" style="margin-bottom: 6px;">Chief Medical History & Issues</span>
                        <span class="field-value" style="text-align: left; max-width: 100%; font-size: 0.9rem; line-height: 1.5; color: #fafafa;">{medical_issue}</span>
                    </div>
                    <div class="profile-field" style="flex-direction: column; align-items: flex-start; height: auto;">
                        <span class="field-label" style="margin-bottom: 6px;">Current Medications</span>
                        <span class="field-value" style="text-align: left; max-width: 100%; font-size: 0.9rem; line-height: 1.5; color: #fafafa;">{meds_str}</span>
                    </div>
                    <div class="profile-field" style="border-bottom:none; flex-direction: column; align-items: flex-start; height: auto;">
                        <span class="field-label" style="margin-bottom: 6px;">Special Instructions</span>
                        <span class="field-value" style="text-align: left; max-width: 100%; font-size: 0.9rem; line-height: 1.5; color: #fafafa;">{special_instr}</span>
                    </div>
                </div>
                
                <div class="patient-card" style="border-left: 4px solid #10b981;">
                    <h3 style="color: #10b981; margin-bottom: 20px;">🔐 Account Information</h3>
                    <div class="profile-field"><span class="field-label">Profile Status</span><span class="field-value" style="color: #10b981; font-weight: bold;">{status}</span></div>
                    <div class="profile-field"><span class="field-label">Registration Date</span><span class="field-value">{reg_date}</span></div>
                    <div class="profile-field" style="border-bottom:none;"><span class="field-label">Last Login Session</span><span class="field-value">{last_login}</span></div>
                </div>
                """,
                unsafe_allow_html=True,
            )

    with tab2:
        st.markdown("### 📄 Patient Documents & Files")
        st.caption("Upload, view, or remove care plans, lab results, and patient record files.")

        doc_col1, doc_col2 = st.columns([1.1, 0.9])

        with doc_col1:
            st.markdown("#### 📂 Existing Documents")
            
            # Load documents
            documents = api_client.list_documents(phone, name)
            
            if documents:
                for doc in documents:
                    doc_name = doc.get("filename") or doc.get("name") if isinstance(doc, dict) else str(doc)
                    ext = doc_name.rsplit(".", 1)[-1].lower() if "." in doc_name else ""
                    icon_map = {"pdf": "📕", "txt": "📄", "docx": "📘", "doc": "📘"}
                    icon = icon_map.get(ext, "📎")
                    
                    # Render a row with columns: Document card, View, Delete
                    card_col, view_col, del_col = st.columns([0.6, 0.2, 0.2])
                    with card_col:
                        st.markdown(
                            f"""
                            <div class="document-card" style="margin: 4px 0; padding: 12px 16px;">
                                <div class="doc-icon" style="font-size: 1.4rem;">{icon}</div>
                                <div class="doc-info">
                                    <div class="doc-name" style="font-size: 0.85rem; font-weight: 600;">{doc_name}</div>
                                    <div class="doc-meta" style="font-size: 0.72rem;">Stored on server</div>
                                </div>
                            </div>
                            """,
                            unsafe_allow_html=True,
                        )
                    with view_col:
                        st.write("") # spacer
                        if st.button("👁️ View", key=f"view_doc_{doc_name}_{phone}", use_container_width=True):
                            st.session_state["editing_doc"] = (doc_name, phone, name)
                            st.rerun()
                    with del_col:
                        st.write("") # spacer
                        if st.button("🗑️ Delete", key=f"del_doc_{doc_name}_{phone}", use_container_width=True):
                            with st.spinner("Deleting..."):
                                res = api_client.delete_document(phone, doc_name, name)
                                if res and res.get("status") == "success":
                                    st.success("Deleted!")
                                    st.rerun()
                                else:
                                    st.error("Failed to delete.")
            else:
                st.markdown(
                    """
                    <div class="empty-state" style="padding: 20px;">
                        <div class="empty-icon" style="font-size: 2rem;">📂</div>
                        <p>No documents found for this patient.</p>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

        with doc_col2:
            st.markdown("#### 📤 Upload Document")
            uploaded_files = st.file_uploader(
                "Choose files to upload",
                type=["pdf", "txt", "docx"],
                accept_multiple_files=True,
                key=f"doc_uploader_{phone}",
                help="Accepted formats: PDF, TXT, DOCX",
            )
            if uploaded_files:
                if st.button("📤 Upload to Patient File", key=f"btn_upload_doc_{phone}", use_container_width=True):
                    progress = st.progress(0, text="Uploading…")
                    success_count = 0
                    for idx, file in enumerate(uploaded_files):
                        progress.progress(
                            (idx + 1) / len(uploaded_files),
                            text=f"Uploading {file.name}…",
                        )
                        res = api_client.upload_document(file, name, phone)
                        if res:
                            success_count += 1
                    progress.empty()
                    if success_count > 0:
                        st.success(f"Successfully uploaded {success_count} files.")
                        st.rerun()
                    else:
                        st.error("Failed to upload files.")

    with tab3:
        patient_id = pat.get("patient_id") or phone
        with st.spinner("Loading patient logs..."):
            logs_data = api_client.get_patient_logs(patient_id)
            
        chat_history = logs_data.get("chat_history", []) if logs_data else []
        incidents = logs_data.get("incidents", []) if logs_data else []

        col_log1, col_log2 = st.columns([1, 1])

        with col_log1:
            st.markdown("### 💬 Patient Chat History")
            st.caption(f"Chronological conversation history belonging ONLY to patient **{name}** ({patient_id}).")
            
            if chat_history:
                with st.container(height=350):
                    for chat in chat_history:
                        role = chat.get("role", "user")
                        message = chat.get("message", "")
                        created_at = chat.get("created_at", "")
                        
                        try:
                            dt = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
                            time_str = dt.strftime("%b %d, %Y, %I:%M %p")
                        except Exception:
                            time_str = created_at
                            
                        badge = ""
                        if role == "user":
                            speaker = f"👤 **Patient** <span style='font-size:0.75rem; color:#94a3b8; font-style:italic;'>({time_str})</span>"
                            risk = chat.get("risk_level", "safe")
                            if risk != "safe":
                                badge = render_risk_badge(risk)
                        else:
                            speaker = f"🤖 **Assistant** <span style='font-size:0.75rem; color:#94a3b8; font-style:italic;'>({time_str})</span>"
                            
                        st.markdown(f"{speaker} {badge}", unsafe_allow_html=True)
                        st.markdown(f"<p style='margin-top:4px; margin-bottom:12px; font-size:0.92rem; line-height:1.5; color:#fafafa;'>{message}</p>", unsafe_allow_html=True)
            else:
                st.markdown(
                    """
                    <div class="empty-state" style="padding: 40px 10px;">
                        <div class="empty-icon">💬</div>
                        <p>No chat history found for this patient.</p>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

        with col_log2:
            st.markdown("### 🚨 Patient-Specific Safety Logs")
            st.caption(f"Safety logs and incident alerts logged ONLY for patient **{name}** ({patient_id}).")
            
            if incidents:
                with st.container(height=350):
                    for inc in incidents:
                        created_at = inc.get("created_at", "")
                        risk = inc.get("risk_level", "risky")
                        risky_text = inc.get("risky_text", "")
                        call_status = inc.get("call_status", "not_initiated")
                        email_sent = inc.get("email_sent", 0)
                        
                        try:
                            dt = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
                            time_str = dt.strftime("%b %d, %Y, %I:%M %p")
                        except Exception:
                            time_str = created_at
                            
                        risk_badge_html = render_risk_badge(risk)
                        
                        st.markdown(
                            f"""
                            <div style="background-color: #1e2538; border-left: 4px solid #ef4444; border-radius: 8px; padding: 12px; margin-bottom: 12px; border: 1px solid #2d3748;">
                                <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:8px;">
                                    <span style="font-size:0.8rem; color:#94a3b8; font-weight:bold;">{time_str}</span>
                                    {risk_badge_html}
                                </div>
                                <div style="margin-bottom:8px; font-size:0.9rem; font-style:italic; color:#fafafa;">
                                    "{risky_text}"
                                </div>
                                <div style="font-size:0.75rem; color:#94a3b8; display:flex; gap:12px;">
                                    <span>📧 Email: {"✅ Sent" if email_sent else "❌ Failed/Not Sent"}</span>
                                    <span>📞 Call: {"✅ Configured" if call_status != "telephony_not_configured" else "❌ Off"} ({call_status})</span>
                                </div>
                            </div>
                            """,
                            unsafe_allow_html=True,
                        )
            else:
                st.markdown(
                    """
                    <div class="empty-state" style="padding: 40px 10px;">
                        <div class="empty-icon">🚨</div>
                        <p>No safety incidents logged for this patient.</p>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

    # Check if we need to show document editor popup
    editing_doc = st.session_state.get("editing_doc")
    if editing_doc:
        filename, doc_phone, doc_pat_name = editing_doc
        _show_edit_document_dialog(api_client, doc_phone, filename, doc_pat_name)

    st.markdown("<br><br>", unsafe_allow_html=True)
    if st.button("⬅️ Back to Patient List", key="btn_back_bottom"):
        st.session_state["viewing_patient"] = None
        st.rerun()
