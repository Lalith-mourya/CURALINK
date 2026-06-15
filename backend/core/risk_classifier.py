"""
Two-layer risk classifier.

Layer 1 — Keyword/regex detection (hard safety policy).
Layer 2 — Ollama LLM classification for messages that pass keyword check.

HARD SAFETY POLICY: keyword match → ALWAYS risky. LLM cannot downgrade.
"""

import re
from typing import Dict, List
from groq import Groq
from core.config import get_settings

# ---------------------------------------------------------------------------
# Layer 1: keyword lists (case-insensitive regex patterns)
# ---------------------------------------------------------------------------
RISKY_KEYWORDS: List[str] = [
    r'kill myself',
    r'end my life',
    r'want to die',
    r'suicide',
    r'suicidal',
    r'cut myself',
    r'hurt myself',
    r'self-harm',
    r'self harm',
    r'took too many pills',
    r'overdose',
    r'took all my medication',
    r"can't breathe",
    r'cannot breathe',
    r'chest pain',
    r'heart attack',
    r'stroke',
    r'unconscious',
    r'seizure',
    r'severe bleeding',
    r'choking',
    r'anaphylaxis',
    r'not worth living',
]

# Pre-compile a combined pattern for speed
_RISKY_PATTERN = re.compile(
    '|'.join(f'(?:{kw})' for kw in RISKY_KEYWORDS),
    re.IGNORECASE,
)


def _keyword_check(message: str) -> List[str]:
    """Return list of risky keywords found in *message*."""
    return [m.group() for m in _RISKY_PATTERN.finditer(message)]


# ---------------------------------------------------------------------------
# Layer 2: LLM-based classification via Ollama
# ---------------------------------------------------------------------------
_LLM_SYSTEM_PROMPT = """You are a medical-risk classifier. Given a patient message, classify it into exactly one of three categories:

- **safe** — The message is a normal health question or casual conversation with no signs of danger.
- **unclear** — The message is ambiguous and might indicate distress but is not clearly dangerous.
- **risky** — The message indicates self-harm, suicidal ideation, a medical emergency, or any immediate danger.

Respond with ONLY a JSON object in this exact format (no markdown, no extra text):
{"risk_level": "<safe|unclear|risky>", "explanation": "<one-sentence reason>"}
"""


def _llm_classify(message: str, groq_key: str, model: str | None = None) -> Dict:
    """Use Groq Cloud LLM to classify the message risk level."""
    settings = get_settings()
    try:
        if not groq_key:
            raise ValueError("Groq API key not provided")
        client = Groq(api_key=groq_key)
        response = client.chat.completions.create(
            model=model or settings.GROQ_MODEL,
            messages=[
                {'role': 'system', 'content': _LLM_SYSTEM_PROMPT},
                {'role': 'user', 'content': message},
            ],
            response_format={"type": "json_object"},  # Force JSON output mode if supported by Groq
            temperature=0.0,  # Strict classification output
        )
        content = response.choices[0].message.content.strip()

        # Attempt to parse the JSON response
        import json
        result = json.loads(content)
        return {
            'risk_level': result.get('risk_level', 'unclear'),
            'explanation': result.get('explanation', 'LLM classification.'),
        }
    except Exception as exc:
        print(f"[RiskClassifier] Groq classification failed: {exc}")
        # Default to unclear when LLM is unavailable
        return {
            'risk_level': 'unclear',
            'explanation': f'LLM classification unavailable: {exc}',
        }


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------
def classify_risk(message: str, groq_key: str, model: str | None = None) -> Dict:
    """
    Classify a patient message into safe / unclear / risky.

    Returns dict with keys: risk_level, keywords_found, explanation.
    """
    # Layer 1: keyword detection
    keywords_found = _keyword_check(message)

    if keywords_found:
        # HARD SAFETY POLICY — keyword match is always risky
        return {
            'risk_level': 'risky',
            'keywords_found': keywords_found,
            'explanation': f"Keyword match detected: {', '.join(keywords_found)}. Automatically classified as risky.",
        }

    # Layer 2: LLM classification (only if no keyword match)
    llm_result = _llm_classify(message, groq_key=groq_key, model=model)

    return {
        'risk_level': llm_result['risk_level'],
        'keywords_found': [],
        'explanation': llm_result['explanation'],
    }
