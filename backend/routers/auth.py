"""
Authentication router for FastAPI backend.
Handles registration, login, token verification, and logout using SQLite.
"""

import re
import uuid
import sqlite3
import bcrypt
from datetime import datetime, timezone, timedelta
from typing import List, Optional
from pydantic import BaseModel, Field

from fastapi import APIRouter, HTTPException, Header, status
from models.database import get_db_connection

router = APIRouter(prefix="/auth", tags=["Auth"])

# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------

class DoctorRegisterRequest(BaseModel):
    name: str
    email: str
    phone: str
    specialization: Optional[str] = ""
    clinic_name: Optional[str] = ""
    password: str

class PatientRegisterRequest(BaseModel):
    name: str
    age: int
    gender: Optional[str] = ""
    height: Optional[float] = 0.0
    weight: Optional[float] = 0.0
    phone: str
    email: str
    password: str
    doctor_id: str
    medical_issue: Optional[str] = ""
    emergency_contact: Optional[str] = ""
    medicines: Optional[List[str]] = []
    special_instructions: Optional[str] = ""
    blood_group: Optional[str] = ""
    address: Optional[str] = ""

class LoginRequest(BaseModel):
    email: str
    password: str

class DoctorSearchResponse(BaseModel):
    doctor_id: str
    name: str
    specialization: Optional[str] = ""
    clinic_name: Optional[str] = ""

# ---------------------------------------------------------------------------
# Helper Functions
# ---------------------------------------------------------------------------

def hash_password(password: str) -> str:
    pwd_bytes = password.encode('utf-8')
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(pwd_bytes, salt).decode('utf-8')

def verify_password(password: str, password_hash: str) -> bool:
    pwd_bytes = password.encode('utf-8')
    hash_bytes = password_hash.encode('utf-8')
    try:
        return bcrypt.checkpw(pwd_bytes, hash_bytes)
    except Exception:
        return False

def get_token_from_header(authorization: Optional[str]) -> str:
    if not authorization:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing Authorization header"
        )
    parts = authorization.split()
    if len(parts) != 2 or parts[0].lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid Authorization header format. Must be Bearer <token>"
        )
    return parts[1]

# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.post("/doctor/register")
async def register_doctor(req: DoctorRegisterRequest):
    if len(req.password) < 8:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password must be at least 8 characters long"
        )

    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        # Check uniqueness across doctors and patients
        cursor.execute("SELECT 1 FROM doctors WHERE email = ? OR phone = ?", (req.email, req.phone))
        if cursor.fetchone():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email or phone already registered"
            )

        cursor.execute("SELECT 1 FROM patients WHERE email = ? OR phone = ?", (req.email, req.phone))
        if cursor.fetchone():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email or phone already registered"
            )

        # Generate doctor_id: DOC001, DOC002, etc.
        cursor.execute("SELECT doctor_id FROM doctors ORDER BY doctor_id DESC LIMIT 1")
        row = cursor.fetchone()
        if row:
            last_id = row["doctor_id"]
            match = re.match(r"DOC(\d+)", last_id)
            if match:
                num = int(match.group(1))
                next_id = f"DOC{num + 1:03d}"
            else:
                next_id = "DOC001"
        else:
            next_id = "DOC001"

        pwd_hash = hash_password(req.password)

        cursor.execute(
            """
            INSERT INTO doctors (doctor_id, name, email, phone, specialization, clinic_name, password_hash)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (next_id, req.name, req.email, req.phone, req.specialization, req.clinic_name, pwd_hash)
        )
        conn.commit()
        return {
            "success": True,
            "doctor_id": next_id,
            "message": "Doctor registered successfully"
        }
    except HTTPException:
        raise
    except Exception as e:
        conn.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Registration failed: {str(e)}"
        )
    finally:
        conn.close()


@router.post("/patient/register")
async def register_patient(req: PatientRegisterRequest):
    if len(req.password) < 8:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password must be at least 8 characters long"
        )

    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        # Check if doctor exists
        cursor.execute("SELECT name, email, phone FROM doctors WHERE doctor_id = ?", (req.doctor_id,))
        doc_row = cursor.fetchone()
        if not doc_row:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid doctor_id. Selected doctor does not exist."
            )
        
        doc_name = doc_row["name"]
        doc_email = doc_row["email"]
        doc_phone = doc_row["phone"]

        # Check uniqueness across doctors and patients
        cursor.execute("SELECT 1 FROM doctors WHERE email = ? OR phone = ?", (req.email, req.phone))
        if cursor.fetchone():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email or phone already registered"
            )

        cursor.execute("SELECT 1 FROM patients WHERE email = ? OR phone = ?", (req.email, req.phone))
        if cursor.fetchone():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email or phone already registered"
            )

        # Generate patient_id: PAT001, PAT002, etc.
        cursor.execute("SELECT patient_id FROM patients ORDER BY patient_id DESC LIMIT 1")
        row = cursor.fetchone()
        if row:
            last_id = row["patient_id"]
            match = re.match(r"PAT(\d+)", last_id)
            if match:
                num = int(match.group(1))
                next_id = f"PAT{num + 1:03d}"
            else:
                next_id = "PAT001"
        else:
            next_id = "PAT001"

        pwd_hash = hash_password(req.password)
        import json
        medicines_json = json.dumps(req.medicines)

        cursor.execute(
            """
            INSERT INTO patients (
                patient_id, name, age, gender, height, weight, phone, email, password_hash, doctor_id,
                medical_issue, doctor_name, doctor_email, doctor_phone, emergency_contact, medicines,
                special_instructions, blood_group, address
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                next_id, req.name, req.age, req.gender, req.height, req.weight, req.phone, req.email, pwd_hash, req.doctor_id,
                req.medical_issue, doc_name, doc_email, doc_phone, req.emergency_contact, medicines_json,
                req.special_instructions, req.blood_group, req.address
            )
        )
        conn.commit()
        return {
            "success": True,
            "patient_id": next_id,
            "message": "Patient registered successfully"
        }
    except HTTPException:
        raise
    except Exception as e:
        conn.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Registration failed: {str(e)}"
        )
    finally:
        conn.close()


@router.get("/doctors/search", response_model=List[DoctorSearchResponse])
async def search_doctors(name: str = ""):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            """
            SELECT doctor_id, name, specialization, clinic_name
            FROM doctors
            WHERE name LIKE ?
            ORDER BY name ASC
            """,
            (f"%{name}%",)
        )
        rows = cursor.fetchall()
        return [dict(row) for row in rows]
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Doctor search failed: {str(e)}"
        )
    finally:
        conn.close()


@router.post("/login")
async def login(req: LoginRequest):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        # 1. Search doctors table
        cursor.execute("SELECT doctor_id, name, phone, password_hash FROM doctors WHERE email = ?", (req.email,))
        doc_row = cursor.fetchone()
        
        user_id = None
        name = None
        phone = None
        pwd_hash = None
        role = None

        if doc_row:
            user_id = doc_row["doctor_id"]
            name = doc_row["name"]
            phone = doc_row["phone"]
            pwd_hash = doc_row["password_hash"]
            role = "doctor"
        else:
            # 2. Search patients table
            cursor.execute("SELECT patient_id, name, phone, password_hash FROM patients WHERE email = ?", (req.email,))
            pat_row = cursor.fetchone()
            if pat_row:
                user_id = pat_row["patient_id"]
                name = pat_row["name"]
                phone = pat_row["phone"]
                pwd_hash = pat_row["password_hash"]
                role = "patient"

        # Account not found
        if not user_id or not pwd_hash:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Account not found"
            )

        # Verify password
        if not verify_password(req.password, pwd_hash):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Incorrect password"
            )

        # Create session token (UUID4)
        session_token = str(uuid.uuid4())
        expiry_hours = 8 if role == "doctor" else 2
        expires_at = (datetime.now(timezone.utc) + timedelta(hours=expiry_hours)).isoformat()

        cursor.execute(
            """
            INSERT INTO auth_sessions (session_token, user_id, role, phone, expires_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (session_token, user_id, role, phone, expires_at)
        )
        conn.commit()

        return {
            "session_token": session_token,
            "role": role,
            "phone": phone,
            "user_id": user_id,
            "doctor_id": user_id if role == "doctor" else None,
            "name": name
        }
    except HTTPException:
        raise
    except Exception as e:
        conn.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Login failed: {str(e)}"
        )
    finally:
        conn.close()


@router.get("/verify")
async def verify_token(authorization: Optional[str] = Header(None)):
    token = get_token_from_header(authorization)
    
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        # Check token
        cursor.execute("SELECT user_id, role, phone, expires_at FROM auth_sessions WHERE session_token = ?", (token,))
        sess_row = cursor.fetchone()
        
        if not sess_row:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid session token"
            )

        expires_dt = datetime.fromisoformat(sess_row["expires_at"])
        # Handle offset-naive comparison
        if expires_dt.tzinfo is None:
            now_dt = datetime.now()
        else:
            now_dt = datetime.now(timezone.utc)

        if expires_dt < now_dt:
            # Delete expired session
            cursor.execute("DELETE FROM auth_sessions WHERE session_token = ?", (token,))
            conn.commit()
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Session token expired"
            )

        user_id = sess_row["user_id"]
        role = sess_row["role"]
        phone = sess_row["phone"]
        name = ""

        # Fetch display name
        if role == "doctor":
            cursor.execute("SELECT name FROM doctors WHERE doctor_id = ?", (user_id,))
            doc_row = cursor.fetchone()
            if doc_row:
                name = doc_row["name"]
        else:
            cursor.execute("SELECT name FROM patients WHERE patient_id = ?", (user_id,))
            pat_row = cursor.fetchone()
            if pat_row:
                name = pat_row["name"]

        return {
            "valid": True,
            "user_id": user_id,
            "role": role,
            "phone": phone,
            "name": name
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Verification failed: {str(e)}"
        )
    finally:
        conn.close()


@router.post("/logout")
async def logout(authorization: Optional[str] = Header(None)):
    token = get_token_from_header(authorization)
    
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("DELETE FROM auth_sessions WHERE session_token = ?", (token,))
        conn.commit()
        return {"success": True}
    except Exception as e:
        conn.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Logout failed: {str(e)}"
        )
    finally:
        conn.close()
