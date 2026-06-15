"""
Patient Profile DB Service.
Handles all SQLite operations for registering, updating, and listing patient profiles.
"""

import json
import sqlite3
from models.database import get_db_connection
from models.schemas import PatientProfile


def _generate_patient_id(conn: sqlite3.Connection) -> str:
    """Generate a sequential Patient ID like PAT001, PAT002, etc."""
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM patients")
    count = cursor.fetchone()[0]
    return f"PAT{count + 1:03d}"


def save_patient(profile: PatientProfile) -> dict:
    """
    Save or update a patient profile in the SQLite database.
    If the phone number exists, update the profile; otherwise, create a new profile with a generated PATxxx ID.
    Returns the complete saved profile as a dictionary.
    """
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        # Check if patient exists by phone
        cursor.execute("SELECT patient_id, created_at, blood_group, address, profile_status FROM patients WHERE phone = ?", (profile.phone,))
        existing = cursor.fetchone()

        medicines_json = json.dumps(profile.medicines)

        if existing:
            # Update existing patient profile
            patient_id = existing["patient_id"]
            created_at = existing["created_at"]
            
            # Use profile overrides, fallback to DB if not set
            blood_group = profile.blood_group or existing["blood_group"] or ""
            address = profile.address or existing["address"] or ""
            profile_status = profile.profile_status or existing["profile_status"] or "Active"

            cursor.execute(
                """
                UPDATE patients
                SET name = ?, age = ?, gender = ?, height = ?, weight = ?, email = ?, 
                    medical_issue = ?, doctor_name = ?, doctor_email = ?, doctor_phone = ?, 
                    emergency_contact = ?, medicines = ?, special_instructions = ?, 
                    blood_group = ?, address = ?, profile_status = ?, last_login = CURRENT_TIMESTAMP
                WHERE phone = ?
                """,
                (
                    profile.name,
                    profile.age,
                    profile.gender,
                    profile.height,
                    profile.weight,
                    profile.email,
                    profile.medical_issue,
                    profile.doctor_name,
                    profile.doctor_email,
                    profile.doctor_phone,
                    profile.emergency_contact,
                    medicines_json,
                    profile.special_instructions,
                    blood_group,
                    address,
                    profile_status,
                    profile.phone,
                ),
            )
            print(f"[PatientService] Updated patient {profile.name} (ID: {patient_id})")
        else:
            # Create new patient profile
            patient_id = _generate_patient_id(conn)
            created_at = None  # Will be set by database default
            
            blood_group = profile.blood_group or ""
            address = profile.address or ""
            profile_status = profile.profile_status or "Active"

            cursor.execute(
                """
                INSERT INTO patients (
                    patient_id, name, age, gender, height, weight, phone, email, 
                    medical_issue, doctor_name, doctor_email, doctor_phone, 
                    emergency_contact, medicines, special_instructions, 
                    blood_group, address, profile_status
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    patient_id,
                    profile.name,
                    profile.age,
                    profile.gender,
                    profile.height,
                    profile.weight,
                    profile.phone,
                    profile.email,
                    profile.medical_issue,
                    profile.doctor_name,
                    profile.doctor_email,
                    profile.doctor_phone,
                    profile.emergency_contact,
                    medicines_json,
                    profile.special_instructions,
                    blood_group,
                    address,
                    profile_status,
                ),
            )
            print(f"[PatientService] Registered new patient {profile.name} (ID: {patient_id})")

        conn.commit()

        # Re-fetch complete saved data to capture DB auto-timestamps
        cursor.execute("SELECT * FROM patients WHERE patient_id = ?", (patient_id,))
        row = cursor.fetchone()
        
        saved_dict = dict(row)
        # Parse medicines list back
        try:
            saved_dict["medicines"] = json.loads(saved_dict["medicines"])
        except Exception:
            saved_dict["medicines"] = []

        return saved_dict

    except Exception as e:
        conn.rollback()
        print(f"[PatientService] Error saving patient: {e}")
        raise e
    finally:
        conn.close()


def get_all_patients(doctor_id: str = None) -> list:
    """Retrieve patient profiles from the database, optionally filtered by doctor_id, ordered by registration date."""
    conn = get_db_connection()
    cursor = conn.cursor()
    patients_list = []
    try:
        if doctor_id:
            cursor.execute("SELECT * FROM patients WHERE doctor_id = ? ORDER BY created_at DESC", (doctor_id,))
        else:
            cursor.execute("SELECT * FROM patients ORDER BY created_at DESC")
        rows = cursor.fetchall()
        for row in rows:
            p_dict = dict(row)
            try:
                p_dict["medicines"] = json.loads(p_dict["medicines"])
            except Exception:
                p_dict["medicines"] = []
            patients_list.append(p_dict)
    except Exception as e:
        print(f"[PatientService] Error fetching patients: {e}")
    finally:
        conn.close()
    return patients_list


def get_patient_by_phone(phone: str) -> dict | None:
    """Retrieve a patient profile by phone number."""
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT * FROM patients WHERE phone = ?", (phone,))
        row = cursor.fetchone()
        if row:
            p_dict = dict(row)
            try:
                p_dict["medicines"] = json.loads(p_dict["medicines"])
            except Exception:
                p_dict["medicines"] = []
            return p_dict
    except Exception as e:
        print(f"[PatientService] Error fetching patient by phone {phone}: {e}")
    finally:
        conn.close()
    return None


def get_patient_by_id(patient_id: str) -> dict | None:
    """Retrieve a patient profile by patient_id."""
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT * FROM patients WHERE patient_id = ?", (patient_id,))
        row = cursor.fetchone()
        if row:
            p_dict = dict(row)
            try:
                p_dict["medicines"] = json.loads(p_dict["medicines"])
            except Exception:
                p_dict["medicines"] = []
            return p_dict
    except Exception as e:
        print(f"[PatientService] Error fetching patient by ID {patient_id}: {e}")
    finally:
        conn.close()
    return None
