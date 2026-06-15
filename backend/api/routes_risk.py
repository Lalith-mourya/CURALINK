"""
Risk testing route (non-escalating).

POST /risk/test — classify a message without triggering any escalation.
"""

from typing import Optional
from fastapi import APIRouter, Header

from core.risk_classifier import classify_risk
from models.schemas import RiskTestRequest, RiskTestResponse

router = APIRouter(prefix='/risk', tags=['Risk'])


@router.post('/test', response_model=RiskTestResponse)
async def test_risk(
    request: RiskTestRequest,
    x_groq_key: Optional[str] = Header(None, alias="x-groq-key"),
):
    """
    Classify a message for risk level.

    This endpoint does NOT trigger any escalation — it is for testing only.
    """
    if not x_groq_key:
        from fastapi import HTTPException
        raise HTTPException(status_code=400, detail="API keys not configured")
    result = classify_risk(request.message, groq_key=x_groq_key)
    return RiskTestResponse(
        risk_level=result['risk_level'],
        keywords_found=result['keywords_found'],
        explanation=result['explanation'],
    )
