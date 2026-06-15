"""
Configuration module using pydantic-settings.
Loads settings from environment variables and .env file.
"""

import os
from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(env_file='.env', extra='ignore')

    # Ollama LLM settings
    OLLAMA_BASE_URL: str = 'http://localhost:11434'
    OLLAMA_MODEL: str = 'llama3.1:8b'

    # Groq LLM settings
    GROQ_API_KEY: str = ''
    GROQ_MODEL: str = 'llama-3.3-70b-versatile'

    # Embedding model
    EMBEDDING_MODEL: str = 'all-MiniLM-L6-v2'

    # SMTP / Email settings
    SMTP_HOST: str = 'smtp.gmail.com'
    SMTP_PORT: int = 465
    SMTP_USER: str = ''
    SMTP_PASSWORD: str = ''
    RESEND_API_KEY: str = ''

    # Twilio settings
    TWILIO_ACCOUNT_SID: str = ''
    TWILIO_AUTH_TOKEN: str = ''
    TWILIO_PHONE_NUMBER: str = ''

    # API settings
    API_HOST: str = '0.0.0.0'
    API_PORT: int = 8000

    # Database and storage
    DATABASE_PATH: str = os.getenv("DB_PATH", "./data/incidents.db")
    CHROMA_PERSIST_DIR: str = os.getenv("CHROMA_PATH", "./data/chroma_store")
    PATIENTS_DIR: str = os.getenv("PATIENTS_DIR", "./data/patients")


@lru_cache()
def get_settings() -> Settings:
    """Return a cached singleton Settings instance."""
    return Settings()
