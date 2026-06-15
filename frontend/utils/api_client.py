"""
API Client for Healthcare Assistant Backend.
Handles all HTTP communication with the FastAPI backend.
"""

import os
import requests


# Field mapping: frontend session keys -> backend schema keys
_PROFILE_KEY_MAP = {
    "patient_name": "name",
    "phone_number": "phone",
    "current_medicines": "medicines",
}


def _map_profile(profile: dict) -> dict:
    """Convert frontend profile keys to the backend PatientProfile schema."""
    mapped = {}
    for k, v in profile.items():
        mapped[_PROFILE_KEY_MAP.get(k, k)] = v
    return mapped


class APIClient:
    """HTTP client for the Healthcare Assistant backend API."""

    def __init__(self, base_url: str = None):
        backend_url = os.getenv("BACKEND_URL", "http://localhost:8000")
        self.base_url = base_url or backend_url
        self.base_url = self.base_url.rstrip("/")

    def _handle_response(self, response: requests.Response) -> requests.Response:
        import streamlit as st
        if response.status_code == 401:
            st.session_state["logged_in"] = False
            st.session_state["session_token"] = None
            st.session_state["role"] = None
            st.session_state["user_id"] = None
            st.session_state["phone"] = None
            st.rerun()
        response.raise_for_status()
        return response

    def _get_headers(self) -> dict:
        """Construct headers incorporating session state auth tokens and variables."""
        import streamlit as st
        headers = {}
        
        # Verify API keys exist and are complete
        if "api_keys" not in st.session_state or not st.session_state.api_keys:
            raise ValueError("API keys not configured")
            
        api_keys = st.session_state.api_keys
        required_keys = ["groq_key", "resend_key", "twilio_sid", "twilio_token", "twilio_phone", "doctor_email"]
        if not all(api_keys.get(k) for k in required_keys):
            raise ValueError("API keys not configured")
            
        try:
            # Map dynamic API Keys
            headers["x-groq-key"] = api_keys.get("groq_key", "")
            headers["x-resend-key"] = api_keys.get("resend_key", "")
            headers["x-twilio-sid"] = api_keys.get("twilio_sid", "")
            headers["x-twilio-token"] = api_keys.get("twilio_token", "")
            headers["x-twilio-phone"] = api_keys.get("twilio_phone", "")
            headers["x-doctor-email"] = api_keys.get("doctor_email", "")
            
            # Custom Session Headers
            if "role" in st.session_state and st.session_state["role"]:
                headers["x-user-role"] = st.session_state["role"]
            if "phone" in st.session_state and st.session_state["phone"]:
                headers["x-user-phone"] = st.session_state["phone"]
            if "user_id" in st.session_state and st.session_state["user_id"]:
                headers["x-user-patient-id"] = st.session_state["user_id"]
            
            # Add doctor identity header specifically
            if "role" in st.session_state and st.session_state["role"] == "doctor":
                headers["x-user-doctor-id"] = st.session_state.get("doctor_id", "")
            else:
                headers["x-user-doctor-id"] = ""
                
            if "session_token" in st.session_state and st.session_state["session_token"]:
                headers["Authorization"] = f"Bearer {st.session_state['session_token']}"
        except Exception as exc:
            print(f"[APIClient] Error reading session state: {exc}")
        return headers

    # ------------------------------------------------------------------ #
    #  Auth Endpoints
    # ------------------------------------------------------------------ #
    def login(self, email: str, password: str) -> dict | None:
        """Log in a user (doctor or patient) with email and password."""
        try:
            response = requests.post(
                f"{self.base_url}/auth/login",
                json={"email": email, "password": password},
                timeout=10,
            )
            if response.status_code == 400:
                return {"error": response.json().get("detail", "Login failed")}
            self._handle_response(response)
            return response.json()
        except requests.exceptions.RequestException as exc:
            print(f"[APIClient] login error: {exc}")
            return None

    def logout_user(self) -> bool:
        """Log out the current user by deleting the session token on the backend."""
        try:
            response = requests.post(
                f"{self.base_url}/auth/logout",
                headers=self._get_headers(),
                timeout=10,
            )
            self._handle_response(response)
            return True
        except requests.exceptions.RequestException as exc:
            print(f"[APIClient] logout error: {exc}")
            return False

    def verify_token(self) -> dict | None:
        """Verify the current session token."""
        try:
            response = requests.get(
                f"{self.base_url}/auth/verify",
                headers=self._get_headers(),
                timeout=10,
            )
            self._handle_response(response)
            return response.json()
        except requests.exceptions.RequestException as exc:
            print(f"[APIClient] verify_token error: {exc}")
            return None

    def search_doctors(self, name: str) -> list:
        """Search for doctors by partial name match."""
        try:
            response = requests.get(
                f"{self.base_url}/auth/doctors/search",
                params={"name": name},
                timeout=10,
            )
            self._handle_response(response)
            return response.json()
        except requests.exceptions.RequestException as exc:
            print(f"[APIClient] search_doctors error: {exc}")
            return []

    def register_doctor_auth(self, doc_data: dict) -> dict | None:
        """Register a new doctor."""
        try:
            response = requests.post(
                f"{self.base_url}/auth/doctor/register",
                json=doc_data,
                timeout=10,
            )
            if response.status_code == 400:
                return {"error": response.json().get("detail", "Registration failed")}
            self._handle_response(response)
            return response.json()
        except requests.exceptions.RequestException as exc:
            print(f"[APIClient] register_doctor error: {exc}")
            return None

    def register_patient_auth(self, patient_data: dict) -> dict | None:
        """Register a new patient."""
        try:
            response = requests.post(
                f"{self.base_url}/auth/patient/register",
                json=patient_data,
                timeout=15,
            )
            if response.status_code == 400:
                return {"error": response.json().get("detail", "Registration failed")}
            self._handle_response(response)
            return response.json()
        except requests.exceptions.RequestException as exc:
            print(f"[APIClient] register_patient_auth error: {exc}")
            return None

    # ------------------------------------------------------------------ #
    #  Chat
    # ------------------------------------------------------------------ #
    def send_chat(self, message: str, patient_profile: dict, message_history: list) -> dict | None:
        """Send a chat message and return the assistant response.

        POST /chat/
        Timeout: 30 s
        """
        try:
            payload = {
                "message": message,
                "patient_profile": _map_profile(patient_profile),
                "message_history": message_history,
            }
            response = requests.post(
                f"{self.base_url}/chat/",
                json=payload,
                headers=self._get_headers(),
                timeout=30,
            )
            self._handle_response(response)
            return response.json()
        except requests.exceptions.RequestException as exc:
            print(f"[APIClient] send_chat error: {exc}")
            return None

    # ------------------------------------------------------------------ #
    #  Documents
    # ------------------------------------------------------------------ #
    def upload_document(self, file, patient_name: str, patient_phone: str) -> dict | None:
        """Upload a document for a patient.

        POST /documents/upload  (multipart/form-data)
        Timeout: 60 s
        """
        try:
            files = {"file": (file.name, file.getvalue(), file.type or "application/octet-stream")}
            data = {"patient_name": patient_name, "patient_phone": patient_phone}
            response = requests.post(
                f"{self.base_url}/documents/upload",
                files=files,
                data=data,
                headers=self._get_headers(),
                timeout=60,
            )
            self._handle_response(response)
            return response.json()
        except requests.exceptions.RequestException as exc:
            print(f"[APIClient] upload_document error: {exc}")
            return None

    def list_documents(self, patient_phone: str, patient_name: str = "") -> list:
        """Retrieve the list of documents for a patient by phone and optional name.

        GET /documents/list/{patient_phone}
        Timeout: 10 s
        """
        try:
            response = requests.get(
                f"{self.base_url}/documents/list/{patient_phone}",
                params={"patient_name": patient_name},
                headers=self._get_headers(),
                timeout=10,
            )
            self._handle_response(response)
            data = response.json()
            return data if isinstance(data, list) else data.get("documents", [])
        except requests.exceptions.RequestException as exc:
            print(f"[APIClient] list_documents error: {exc}")
            return []

    def delete_document(self, patient_phone: str, filename: str, patient_name: str = "") -> dict | None:
        """Delete a document for a patient.

        DELETE /documents/{patient_phone}
        Timeout: 15 s
        """
        try:
            response = requests.delete(
                f"{self.base_url}/documents/{patient_phone}",
                params={"filename": filename, "patient_name": patient_name},
                headers=self._get_headers(),
                timeout=15,
            )
            self._handle_response(response)
            return response.json()
        except requests.exceptions.RequestException as exc:
            print(f"[APIClient] delete_document error: {exc}")
            return None

    def get_document_content(self, patient_phone: str, filename: str, patient_name: str = "") -> dict | None:
        """Retrieve the text content of a patient document.

        GET /documents/content/{patient_phone}
        Timeout: 15 s
        """
        try:
            response = requests.get(
                f"{self.base_url}/documents/content/{patient_phone}",
                params={"filename": filename, "patient_name": patient_name},
                headers=self._get_headers(),
                timeout=15,
            )
            self._handle_response(response)
            return response.json()
        except requests.exceptions.RequestException as exc:
            print(f"[APIClient] get_document_content error: {exc}")
            return None

    def update_document_content(self, patient_phone: str, filename: str, content: str, patient_name: str = "") -> dict | None:
        """Update the text content of a patient document.

        POST /documents/update/{patient_phone}
        Timeout: 15 s
        """
        try:
            response = requests.post(
                f"{self.base_url}/documents/update/{patient_phone}",
                params={"filename": filename, "patient_name": patient_name},
                json={"content": content},
                headers=self._get_headers(),
                timeout=15,
            )
            self._handle_response(response)
            return response.json()
        except requests.exceptions.RequestException as exc:
            print(f"[APIClient] update_document_content error: {exc}")
            return None

    # ------------------------------------------------------------------ #
    #  Logs / Incidents
    # ------------------------------------------------------------------ #
    def get_incidents(self, patient_name: str = None, risk_level: str = None, patient_phone: str = None) -> list:
        """Fetch incident logs, optionally filtered.

        GET /logs/incidents
        Timeout: 10 s
        """
        try:
            params = {}
            if patient_name:
                params["patient_name"] = patient_name
            if risk_level:
                params["risk_level"] = risk_level
            if patient_phone:
                params["patient_phone"] = patient_phone
            response = requests.get(
                f"{self.base_url}/logs/incidents",
                params=params,
                headers=self._get_headers(),
                timeout=10,
            )
            self._handle_response(response)
            data = response.json()
            return data if isinstance(data, list) else data.get("incidents", [])
        except requests.exceptions.RequestException as exc:
            print(f"[APIClient] get_incidents error: {exc}")
            return []

    def get_chat_history(self, patient_name: str = None, patient_phone: str = None) -> list:
        """Fetch chat history logs.

        GET /logs/chat-history
        Timeout: 10 s
        """
        try:
            params = {}
            if patient_name:
                params["patient_name"] = patient_name
            if patient_phone:
                params["patient_phone"] = patient_phone
            response = requests.get(
                f"{self.base_url}/logs/chat-history",
                params=params,
                headers=self._get_headers(),
                timeout=10,
            )
            self._handle_response(response)
            data = response.json()
            return data if isinstance(data, list) else data.get("history", [])
        except requests.exceptions.RequestException as exc:
            print(f"[APIClient] get_chat_history error: {exc}")
            return []

    # ------------------------------------------------------------------ #
    #  Risk Testing
    # ------------------------------------------------------------------ #
    def test_risk(self, message: str) -> dict | None:
        """Test the risk classifier on an arbitrary message.

        POST /risk/test
        Timeout: 10 s
        """
        try:
            response = requests.post(
                f"{self.base_url}/risk/test",
                json={"message": message},
                headers=self._get_headers(),
                timeout=10,
            )
            self._handle_response(response)
            return response.json()
        except requests.exceptions.RequestException as exc:
            print(f"[APIClient] test_risk error: {exc}")
            return None

    # ------------------------------------------------------------------ #
    #  Health
    # ------------------------------------------------------------------ #
    def health_check(self) -> dict | None:
        """Check backend health.

        GET /health
        Timeout: 10 s
        """
        try:
            response = requests.get(
                f"{self.base_url}/health",
                headers=self._get_headers(),
                timeout=10,
            )
            self._handle_response(response)
            return response.json()
        except requests.exceptions.RequestException as exc:
            print(f"[APIClient] health_check error: {exc}")
            return None

    # ------------------------------------------------------------------ #
    #  Patients
    # ------------------------------------------------------------------ #
    def register_patient(self, profile: dict) -> dict | None:
        """Register or update a patient profile.

        POST /patients/
        Timeout: 15 s
        """
        try:
            mapped_profile = _map_profile(profile)
            mapped_profile.setdefault("doctor_name", "")
            mapped_profile.setdefault("doctor_email", "")
            mapped_profile.setdefault("doctor_phone", "")
            mapped_profile.setdefault("emergency_contact", "")
            mapped_profile.setdefault("medicines", [])
            mapped_profile.setdefault("special_instructions", "")
            mapped_profile.setdefault("medical_issue", profile.get("medical_issue", ""))
            mapped_profile.setdefault("patient_id", profile.get("patient_id", ""))
            mapped_profile.setdefault("blood_group", profile.get("blood_group", ""))
            mapped_profile.setdefault("address", profile.get("address", ""))
            mapped_profile.setdefault("profile_status", profile.get("profile_status", "Active"))
            
            response = requests.post(
                f"{self.base_url}/patients/",
                json=mapped_profile,
                headers=self._get_headers(),
                timeout=15,
            )
            self._handle_response(response)
            return response.json()
        except requests.exceptions.RequestException as exc:
            print(f"[APIClient] register_patient error: {exc}")
            return None

    def get_patients(self) -> list:
        """Fetch all registered patient profiles.

        GET /patients/
        Timeout: 10 s
        """
        try:
            response = requests.get(
                f"{self.base_url}/patients/",
                headers=self._get_headers(),
                timeout=10,
            )
            self._handle_response(response)
            return response.json()
        except requests.exceptions.RequestException as exc:
            print(f"[APIClient] get_patients error: {exc}")
            return []

    def get_patient_details(self, phone: str) -> dict | None:
        """Get detailed profile data for a specific patient by phone number.

        GET /patients/{phone}
        Timeout: 10 s
        """
        try:
            response = requests.get(
                f"{self.base_url}/patients/{phone}",
                headers=self._get_headers(),
                timeout=10,
            )
            self._handle_response(response)
            return response.json()
        except requests.exceptions.RequestException as exc:
            print(f"[APIClient] get_patient_details error: {exc}")
            return None

    def get_patient_logs(self, patient_id: str) -> dict | None:
        """Get logs (chat history and incidents) for a specific patient.

        GET /patients/{patient_id}/logs
        Timeout: 10 s
        """
        try:
            response = requests.get(
                f"{self.base_url}/patients/{patient_id}/logs",
                headers=self._get_headers(),
                timeout=10,
            )
            self._handle_response(response)
            return response.json()
        except requests.exceptions.RequestException as exc:
            print(f"[APIClient] get_patient_logs error: {exc}")
            return None
