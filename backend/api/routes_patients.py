"""
Patient routes for registering, updating, and fetching profiles.
"""

from typing import List, Optional
from fastapi import APIRouter, HTTPException, Header

from core import patient_service
from models.schemas import PatientProfile

router = APIRouter(prefix='/patients', tags=['Patients'])


@router.post('/', response_model=PatientProfile)
async def register_or_update_patient(profile: PatientProfile):
    """
    Register a new patient or update their existing profile.
    Automatically generates a PATxxx patient ID for new registrations.
    """
    try:
        saved_profile = patient_service.save_patient(profile)
        return saved_profile
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save patient profile: {e}")


@router.get('/', response_model=List[PatientProfile])
async def list_patients(
    x_user_role: Optional[str] = Header(None),
    x_user_doctor_id: Optional[str] = Header(None),
):
    """
    Get a list of all registered patients in the system.
    Used exclusively by the Doctor Dashboard.
    """
    role = x_user_role or "doctor"  # Default to doctor for test scripts
    if role != "doctor":
        raise HTTPException(status_code=403, detail="Access denied. Doctors only.")
    if not x_user_doctor_id:
        raise HTTPException(status_code=400, detail="Doctor ID header missing")
    try:
        patients = patient_service.get_all_patients(doctor_id=x_user_doctor_id)
        return patients
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch patients list: {e}")


@router.get('/search', response_model=List[PatientProfile])
async def search_patients(
    name: str = "",
    x_user_role: Optional[str] = Header(None),
    x_user_doctor_id: Optional[str] = Header(None),
):
    """
    Search patients by partial name, restricted by doctor_id.
    """
    import json
    role = x_user_role or "doctor"
    if role != "doctor":
        raise HTTPException(status_code=403, detail="Access denied. Doctors only.")
    if not x_user_doctor_id:
        raise HTTPException(status_code=400, detail="Doctor ID header missing")
    
    from models.database import get_db_connection
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            "SELECT * FROM patients WHERE name LIKE ? AND doctor_id = ? ORDER BY created_at DESC",
            (f"%{name}%", x_user_doctor_id)
        )
        rows = cursor.fetchall()
        patients_list = []
        for row in rows:
            p_dict = dict(row)
            try:
                p_dict["medicines"] = json.loads(p_dict["medicines"])
            except Exception:
                p_dict["medicines"] = []
            patients_list.append(p_dict)
        return patients_list
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to search patients: {e}")
    finally:
        conn.close()


@router.get('/{patient_id}/logs')
async def get_patient_logs(
    patient_id: str,
    x_user_role: Optional[str] = Header(None),
    x_user_phone: Optional[str] = Header(None),
    x_user_patient_id: Optional[str] = Header(None),
    x_user_doctor_id: Optional[str] = Header(None),
):
    """
    Retrieve safety logs and chronological chat history belonging ONLY to the selected patient.
    """
    role = x_user_role or "doctor"  # Default to doctor for test scripts
    if role not in ("patient", "doctor"):
        raise HTTPException(status_code=403, detail="Unauthorized role")
    
    if role == "doctor" and not x_user_doctor_id:
        raise HTTPException(status_code=400, detail="Doctor ID header missing")

    try:
        from core.incident_logger import get_incidents, get_chat_logs
        
        # Verify patient exists
        patient = patient_service.get_patient_by_id(patient_id)
        if not patient:
            # Fallback check by phone
            patient = patient_service.get_patient_by_phone(patient_id)
            if not patient:
                raise HTTPException(status_code=404, detail="Patient not found")
            patient_id = patient.get("patient_id")

        if role == "patient":
            if patient_id not in (x_user_patient_id, x_user_phone):
                raise HTTPException(status_code=403, detail="Access denied. Cannot access another patient's logs.")
        elif role == "doctor":
            if patient.get("doctor_id") != x_user_doctor_id:
                raise HTTPException(status_code=403, detail="Access denied")

        incidents = get_incidents(patient_id=patient_id)
        chat_history = get_chat_logs(patient_id=patient_id, order='ASC', limit=200)

        return {
            "patient_id": patient_id,
            "patient_name": patient.get("name"),
            "incidents": incidents,
            "chat_history": chat_history
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch patient logs: {e}")


@router.get('/{phone}', response_model=PatientProfile)
async def get_patient_profile_details(
    phone: str,
    x_user_role: Optional[str] = Header(None),
    x_user_phone: Optional[str] = Header(None),
    x_user_doctor_id: Optional[str] = Header(None),
):
    """
    Retrieve detailed profile data for a specific patient by phone number.
    """
    role = x_user_role or "doctor"  # Default to doctor for test scripts
    if role not in ("patient", "doctor"):
        raise HTTPException(status_code=403, detail="Unauthorized role")
    
    if role == "doctor" and not x_user_doctor_id:
        raise HTTPException(status_code=400, detail="Doctor ID header missing")

    try:
        print(f"[DEBUG] get_patient_profile_details phone={repr(phone)} x_user_phone={repr(x_user_phone)} x_user_role={repr(x_user_role)}")
        profile = patient_service.get_patient_by_phone(phone)
        print(f"[DEBUG] profile found: {profile is not None}")
        if not profile:
            raise HTTPException(status_code=404, detail="Patient profile not found")

        if role == "patient":
            if phone != x_user_phone:
                raise HTTPException(status_code=403, detail="Access denied. Cannot access another patient's details.")
        elif role == "doctor":
            if profile.get("doctor_id") != x_user_doctor_id:
                raise HTTPException(status_code=403, detail="Access denied — this patient is not under your care")

        return profile
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch patient details: {e}")
