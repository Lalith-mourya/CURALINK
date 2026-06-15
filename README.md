# 🏥 Healthcare Patient-Support Chatbot (CURALINK)

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

---

## 💻 Local Development Setup

### 1. Prerequisites
Ensure you have Python 3.10+ installed.

### 2. Install Dependencies
Create a virtual environment and install the required dependencies:
```bash
# Create a virtual environment
python -m venv .venv

# Activate the virtual environment
# On Windows:
.venv\Scripts\activate
# On macOS/Linux:
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 3. Run the Backend Service
Run the FastAPI backend on port 8000:
```bash
uvicorn backend.main:app --host 127.0.0.1 --port 8000 --reload
```

### 4. Run the Frontend Service
In a separate terminal (with the virtual environment active), launch the Streamlit frontend on port 8501:
```bash
streamlit run frontend/app.py --server.port 8501
```

### 5. Access and Configure
1. Open your browser and navigate to `http://localhost:8501`.
2. Enter your credentials in the **API Configuration** sidebar to activate features:
    *   **Groq API Key**: `gsk_...`
    *   **Resend API Key**: `re_...`
    *   **Twilio Account SID & Auth Token**
    *   **Twilio Phone Number**
    *   **Doctor Email**
3. Proceed to Register/Login.

---

## 🚀 Deployment Guide (Render)

This application is configured for seamless deployment on **Render** using the Blueprint specification (`render.yaml`).

### 📂 Render Blueprint Configuration
The project includes a `render.yaml` file that defines:
1.  **FastAPI Backend Service (`clinical-bot-backend`)**:
    *   Connected to a **Persistent Disk** mounted at `/data` to store the database, patient documents, and vector store indices across restarts.
    *   Environment variables mapping database paths to the persistent disk (`DB_PATH=/data/incidents.db`, etc.).
2.  **Streamlit Frontend Service (`clinical-bot-frontend`)**:
    *   Configured to build and run Streamlit on port `10000`.
    *   Requires a `BACKEND_URL` environment variable pointing to the backend service.

### 📋 Deployment Steps

1.  **Push Code to GitHub**:
    Ensure all changes are committed and pushed to your repository:
    ```bash
    git add .
    git commit -m "Configure paths and dependencies for Render deployment"
    git push origin main
    ```
    *Repository URL: `https://github.com/Lalith-mourya/CURALINK.git`*

2.  **Create Blueprints Service on Render**:
    *   Log in to your [Render Dashboard](https://dashboard.render.com).
    *   Click **New +** and select **Blueprint**.
    *   Connect your GitHub repository `CURALINK`.
    *   Render will read `render.yaml` and configure the backend service, persistent disk, and frontend service automatically.

3.  **Configure Environment Variables on Render**:
    During setup or after deployment in the Render dashboard:
    *   Under the **clinical-bot-frontend** settings, set the `BACKEND_URL` environment variable to the live URL of your deployed backend service (e.g. `https://clinical-bot-backend.onrender.com`).

4.  **Launch the App**:
    Once both services show a status of **Live**, visit the URL of your Streamlit frontend service (e.g. `https://clinical-bot-frontend.onrender.com`), configure your sidebar API keys, and start using the app!
