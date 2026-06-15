"""
Telephony Integration Module for Healthcare Patient-Support Chatbot.

Provides emergency call placement via Twilio with fallback retry logic.
When the backend detects a risky patient message, this module handles
placing a real phone call to the doctor.
"""

from .call_handler import place_emergency_call
from .fallback import place_call_with_fallback

__all__ = ["place_emergency_call", "place_call_with_fallback"]
