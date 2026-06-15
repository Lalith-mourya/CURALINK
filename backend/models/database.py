"""
SQLite database setup and connection helpers.
Creates tables for incidents and chat_logs.
"""

import os
import sqlite3
from dotenv import load_dotenv

# Load environment variables from .env
for env_path in [".env", "../.env", "../../.env"]:
    if os.path.exists(env_path):
        load_dotenv(env_path)
        break

from core.config import get_settings

DB_PATH = os.getenv("DB_PATH", "./incidents.db")
CHROMA_PATH = os.getenv("CHROMA_PATH", "./chroma_store")
PATIENTS_DIR = os.getenv("PATIENTS_DIR", "./data/patients")

def get_db_connection() -> sqlite3.Connection:
    """Get a new SQLite database connection with row_factory enabled."""
    abs_path = os.path.abspath(DB_PATH)
    print(f"[DB_CONNECTION] Connecting to: {abs_path}")
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL;")
    return conn


def init_db() -> None:
    """Initialize the database: create tables and indexes if they don't exist."""
    conn = get_db_connection()
    cursor = conn.cursor()

    # Create doctors table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS doctors (
            doctor_id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            phone TEXT UNIQUE NOT NULL,
            specialization TEXT,
            clinic_name TEXT,
            password_hash TEXT NOT NULL,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Check patients table and migrate if needed
    cursor.execute("PRAGMA table_info(patients)")
    pat_columns = [row['name'] for row in cursor.fetchall()]

    if not pat_columns:
        # Create patients table from scratch
        cursor.execute("""
            CREATE TABLE patients (
                patient_id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                age INTEGER NOT NULL,
                gender TEXT,
                height REAL,
                weight REAL,
                phone TEXT UNIQUE NOT NULL,
                email TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL DEFAULT '',
                doctor_id TEXT,
                medical_issue TEXT,
                doctor_name TEXT,
                doctor_email TEXT,
                doctor_phone TEXT,
                emergency_contact TEXT,
                medicines TEXT,
                special_instructions TEXT,
                blood_group TEXT,
                address TEXT,
                profile_status TEXT DEFAULT 'Active',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_login TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (doctor_id) REFERENCES doctors(doctor_id)
            )
        """)
    elif 'password_hash' not in pat_columns or 'doctor_id' not in pat_columns:
        print("[DB] Migrating patients table to add password_hash, doctor_id and set email UNIQUE NOT NULL...")
        # Rename old table
        cursor.execute("ALTER TABLE patients RENAME TO patients_old")
        
        # Create new table
        cursor.execute("""
            CREATE TABLE patients (
                patient_id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                age INTEGER NOT NULL,
                gender TEXT,
                height REAL,
                weight REAL,
                phone TEXT UNIQUE NOT NULL,
                email TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL DEFAULT '',
                doctor_id TEXT,
                medical_issue TEXT,
                doctor_name TEXT,
                doctor_email TEXT,
                doctor_phone TEXT,
                emergency_contact TEXT,
                medicines TEXT,
                special_instructions TEXT,
                blood_group TEXT,
                address TEXT,
                profile_status TEXT DEFAULT 'Active',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_login TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (doctor_id) REFERENCES doctors(doctor_id)
            )
        """)
        
        # Copy data
        cursor.execute("""
            INSERT INTO patients (
                patient_id, name, age, gender, height, weight, phone, email,
                password_hash, doctor_id, medical_issue, doctor_name, doctor_email,
                doctor_phone, emergency_contact, medicines, special_instructions,
                blood_group, address, profile_status, created_at, last_login
            )
            SELECT
                patient_id, name, age, gender, height, weight, phone,
                COALESCE(NULLIF(email, ''), patient_id || '@example.com'),
                '', NULL, medical_issue, doctor_name, doctor_email,
                doctor_phone, emergency_contact, medicines, special_instructions,
                blood_group, address, profile_status, created_at, last_login
            FROM patients_old
        """)
        
        # Drop old table
        cursor.execute("DROP TABLE patients_old")
        print("[DB] patients table migration completed successfully.")

    # Create auth_sessions table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS auth_sessions (
            session_token TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            role TEXT NOT NULL,
            phone TEXT,
            expires_at DATETIME NOT NULL,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Create incidents table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS incidents (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            patient_id TEXT,
            patient_name TEXT,
            patient_phone TEXT,
            doctor_name TEXT,
            doctor_email TEXT,
            doctor_phone TEXT,
            risk_level TEXT,
            risky_text TEXT,
            message_history TEXT,
            email_sent INTEGER DEFAULT 0,
            call_status TEXT DEFAULT 'not_initiated',
            call_sid TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Create chat_logs table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS chat_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            patient_id TEXT,
            patient_name TEXT,
            role TEXT,
            message TEXT,
            risk_level TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            patient_phone TEXT
        )
    """)

    # Ensure patient_phone column exists in chat_logs (Migration)
    cursor.execute("PRAGMA table_info(chat_logs)")
    columns = [row['name'] for row in cursor.fetchall()]
    if 'patient_phone' not in columns:
        cursor.execute("ALTER TABLE chat_logs ADD COLUMN patient_phone TEXT")

    # Ensure patient_id column exists in chat_logs (Migration)
    if 'patient_id' not in columns:
        cursor.execute("ALTER TABLE chat_logs ADD COLUMN patient_id TEXT")

    # Ensure patient_id column exists in incidents (Migration)
    cursor.execute("PRAGMA table_info(incidents)")
    inc_columns = [row['name'] for row in cursor.fetchall()]
    if 'patient_id' not in inc_columns:
        cursor.execute("ALTER TABLE incidents ADD COLUMN patient_id TEXT")

    # Create indexes for faster queries
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_incidents_created_at
        ON incidents (created_at)
    """)
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_incidents_risk_level
        ON incidents (risk_level)
    """)
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_incidents_patient_id
        ON incidents (patient_id)
    """)
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_chat_logs_created_at
        ON chat_logs (created_at)
    """)
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_chat_logs_risk_level
        ON chat_logs (risk_level)
    """)
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_chat_logs_patient_phone
        ON chat_logs (patient_phone)
    """)
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_chat_logs_patient_id
        ON chat_logs (patient_id)
    """)

    conn.commit()
    conn.close()
    print("[DB] Database initialized successfully.")
