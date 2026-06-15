"""
Incident and chat-log persistence layer.

Stores escalation incidents and per-message chat logs in SQLite.
"""

import json
from typing import Dict, List, Optional

from models.database import get_db_connection


def log_incident(
    patient_name: str,
    patient_phone: str,
    doctor_name: str,
    doctor_email: str,
    doctor_phone: str,
    risk_level: str,
    risky_text: str,
    message_history: list,
    email_sent: bool,
    call_status: str,
    call_sid: Optional[str],
    patient_id: Optional[str] = None,
) -> int:
    """
    Insert a new incident record.

    Returns the auto-generated incident id.
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO incidents
            (patient_id, patient_name, patient_phone, doctor_name, doctor_email, doctor_phone,
             risk_level, risky_text, message_history, email_sent, call_status, call_sid)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            patient_id,
            patient_name,
            patient_phone,
            doctor_name,
            doctor_email,
            doctor_phone,
            risk_level,
            risky_text,
            json.dumps(message_history),
            1 if email_sent else 0,
            call_status,
            call_sid,
        ),
    )
    conn.commit()
    incident_id = cursor.lastrowid
    conn.close()
    print(f"[Incident] Logged incident #{incident_id} (ID: {patient_id}) for patient '{patient_name}'.")
    return incident_id


def log_chat(
    patient_name: str,
    role: str,
    message: str,
    risk_level: str,
    patient_phone: Optional[str] = None,
    patient_id: Optional[str] = None,
) -> None:
    """Insert a single chat log entry."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO chat_logs (patient_id, patient_name, role, message, risk_level, patient_phone)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (patient_id, patient_name, role, message, risk_level, patient_phone),
    )
    conn.commit()
    conn.close()


def get_incidents(
    patient_name: Optional[str] = None,
    risk_level: Optional[str] = None,
    patient_phone: Optional[str] = None,
    patient_id: Optional[str] = None,
    limit: int = 50,
    order: str = 'DESC',
    doctor_id: Optional[str] = None,
) -> List[Dict]:
    """Retrieve incident records with optional filters."""
    conn = get_db_connection()
    cursor = conn.cursor()

    if doctor_id:
        query = "SELECT i.* FROM incidents i JOIN patients p ON i.patient_id = p.patient_id WHERE p.doctor_id = ?"
        params: list = [doctor_id]
    else:
        query = "SELECT * FROM incidents WHERE 1=1"
        params = []

    if patient_id:
        prefix = "i." if doctor_id else ""
        query += f" AND {prefix}patient_id = ?"
        params.append(patient_id)
    elif patient_phone:
        prefix = "i." if doctor_id else ""
        query += f" AND {prefix}patient_phone = ?"
        params.append(patient_phone)
    elif patient_name:
        prefix = "i." if doctor_id else ""
        query += f" AND {prefix}patient_name = ?"
        params.append(patient_name)

    if risk_level:
        prefix = "i." if doctor_id else ""
        query += f" AND {prefix}risk_level = ?"
        params.append(risk_level)

    # Validate order input to prevent SQL injection
    order_direction = 'ASC' if order.upper() == 'ASC' else 'DESC'
    order_col = "i.created_at" if doctor_id else "created_at"
    query += f" ORDER BY {order_col} {order_direction} LIMIT ?"
    params.append(limit)

    cursor.execute(query, params)
    rows = cursor.fetchall()
    conn.close()

    return [dict(row) for row in rows]


def get_chat_logs(
    patient_name: Optional[str] = None,
    patient_phone: Optional[str] = None,
    patient_id: Optional[str] = None,
    limit: int = 100,
    order: str = 'DESC',
    doctor_id: Optional[str] = None,
) -> List[Dict]:
    """Retrieve chat log entries with optional patient filter."""
    conn = get_db_connection()
    cursor = conn.cursor()

    if doctor_id:
        query = "SELECT c.* FROM chat_logs c JOIN patients p ON c.patient_id = p.patient_id WHERE p.doctor_id = ?"
        params: list = [doctor_id]
    else:
        query = "SELECT * FROM chat_logs WHERE 1=1"
        params = []

    if patient_id:
        prefix = "c." if doctor_id else ""
        query += f" AND {prefix}patient_id = ?"
        params.append(patient_id)
    elif patient_phone:
        prefix = "c." if doctor_id else ""
        query += f" AND {prefix}patient_phone = ?"
        params.append(patient_phone)
    elif patient_name:
        prefix = "c." if doctor_id else ""
        query += f" AND {prefix}patient_name = ?"
        params.append(patient_name)

    # Validate order input to prevent SQL injection
    order_direction = 'ASC' if order.upper() == 'ASC' else 'DESC'
    order_col = "c.created_at" if doctor_id else "created_at"
    query += f" ORDER BY {order_col} {order_direction} LIMIT ?"
    params.append(limit)

    cursor.execute(query, params)
    rows = cursor.fetchall()
    conn.close()

    return [dict(row) for row in rows]


def update_incident_call_status(
    incident_id: int,
    call_status: str,
    call_sid: Optional[str],
) -> None:
    """Update the call status and SID of an existing incident."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        UPDATE incidents
        SET call_status = ?, call_sid = ?
        WHERE id = ?
        """,
        (call_status, call_sid, incident_id),
    )
    conn.commit()
    conn.close()
    print(f"[Incident] Updated call status for incident #{incident_id}: {call_status}")
