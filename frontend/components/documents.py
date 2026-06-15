"""
Documents tab — upload and manage patient documents.
"""

import streamlit as st
from utils.session import get_patient_profile


def render_documents_tab(api_client) -> None:
    """Render the 📄 Documents tab."""

    st.subheader("📄 Document Management")
    st.caption("Upload medical documents such as prescriptions, lab reports, and discharge summaries.")

    profile = get_patient_profile()
    patient_name = profile.get("patient_name", "").strip()
    patient_phone = profile.get("phone_number", "").strip()

    # ── Upload Section ─────────────────────────────────────────────
    st.markdown("---")
    st.markdown("#### ⬆️ Upload Documents")

    if not patient_name:
        st.warning("⚠️ Please set your **Patient Name** in the Profile tab before uploading documents.")
        return

    uploaded_files = st.file_uploader(
        "Choose files to upload",
        type=["pdf", "txt", "docx"],
        accept_multiple_files=True,
        key="doc_uploader",
        help="Accepted formats: PDF, TXT, DOCX",
    )

    if uploaded_files:
        if st.button("📤 Upload Selected Files", key="btn_upload_docs", use_container_width=True):
            progress = st.progress(0, text="Uploading…")
            results: list[dict] = []

            for idx, file in enumerate(uploaded_files):
                progress.progress(
                    (idx + 1) / len(uploaded_files),
                    text=f"Uploading {file.name}…",
                )
                result = api_client.upload_document(file, patient_name, patient_phone)
                results.append({"name": file.name, "result": result})

            progress.empty()

            success_count = 0
            for r in results:
                if r["result"]:
                    st.success(f"✅ **{r['name']}** uploaded successfully.")
                    success_count += 1
                    # Track in session
                    if r["name"] not in st.session_state.get("uploaded_documents", []):
                        st.session_state.setdefault("uploaded_documents", []).append(r["name"])
                else:
                    st.error(f"❌ **{r['name']}** failed to upload.")

            if success_count:
                st.balloons()

    # ── Existing Documents ─────────────────────────────────────────
    st.markdown("---")
    st.markdown("#### 📂 Existing Documents")

    col_refresh, _ = st.columns([0.3, 0.7])
    with col_refresh:
        refresh = st.button("🔄 Refresh List", key="btn_refresh_docs")

    documents = api_client.list_documents(patient_phone, patient_name)

    if documents:
        for doc in documents:
            if isinstance(doc, dict):
                name = doc.get("filename") or doc.get("name", "Unknown")
                uploaded_at = doc.get("uploaded_at", "")
                size = doc.get("size", "")
                meta_parts = []
                if uploaded_at:
                    meta_parts.append(f"Uploaded: {uploaded_at}")
                if size:
                    meta_parts.append(f"Size: {size}")
                meta_text = " · ".join(meta_parts) if meta_parts else "Medical document"
            else:
                name = str(doc)
                meta_text = "Medical document"

            # Determine icon by extension
            ext = name.rsplit(".", 1)[-1].lower() if "." in name else ""
            icon_map = {"pdf": "📕", "txt": "📄", "docx": "📘", "doc": "📘"}
            icon = icon_map.get(ext, "📎")

            st.markdown(
                f"""
                <div class="document-card">
                    <div class="doc-icon">{icon}</div>
                    <div class="doc-info">
                        <div class="doc-name">{name}</div>
                        <div class="doc-meta">{meta_text}</div>
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )
    else:
        st.markdown(
            """
            <div class="empty-state">
                <div class="empty-icon">📂</div>
                <p>No documents found.<br>Upload your first document above to get started.</p>
            </div>
            """,
            unsafe_allow_html=True,
        )

    # ── Session-tracked uploads ────────────────────────────────────
    session_docs = st.session_state.get("uploaded_documents", [])
    if session_docs:
        with st.expander("📋 Uploads this session"):
            for name in session_docs:
                st.write(f"• {name}")
