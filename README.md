# 🏥 Healthcare Patient-Support Chatbot (CURALINK)
**LIVE LINK: https://clinical-bot-frontend.onrender.com **

A premium, two-service clinical assistant and patient-monitoring portal. It provides real-time patient support via a Retrieval-Augmented Generation (RAG) chatbot, clinical safety classification, and automated alert escalation to doctors when risk is detected.

---

## 🌟 Key Features

*   **RAG-Powered Chatbot**: Uses document indexation (`PyPDF2`, `docx`) and ChromaDB vector store embeddings to answer patient questions based on their uploaded care plans.
*   **Clinical Safety & Risk Classifier**: Classifies incoming messages into `safe`, `unclear`, or `risky`.
*   **Emergency Alert Escalation**: If risk is detected, the system immediately:
    *   Sends an HTML alert email to the assigned doctor via the **Resend API**.
    *   Places an automated text-to-speech phone call to the doctor via the **Twilio API**.
*   **Role-Based Portal Access**: SQLite authentication ensures doctors can only access files, chats, and safety logs for patients assigned to them.
*   **Dynamic API Key Injection**: API keys are captured at runtime in the Streamlit sidebar and forwarded to the backend via secure custom request headers (`x-groq-key`, `x-resend-key`, etc.), ensuring zero server-side storage of third-party credentials.

---

## 🛠️ Tech Stack

*   **Backend**: FastAPI, SQLite, ChromaDB, SentenceTransformers, Groq API, Uvicorn
*   **Frontend**: Streamlit, Requests, Pandas
*   **Integrations**: Resend (Emails), Twilio (Emergency Telephony)


