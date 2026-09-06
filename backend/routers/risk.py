"""
CropPulse – Crop Risk Router
GET  /api/v1/risk          – Assess crop disease risk for a farm or plot
POST /api/v1/risk/evaluate – Ad-hoc multi-factor risk assessment
"""

from typing import Optional
from fastapi import APIRouter, Depends, Query, status
from slowapi import Limiter
from slowapi.util import get_remote_address

from backend.dependencies import get_current_user
from backend.services.risk_service import risk_service
from backend.models.risk import RiskEvaluationRequest, RiskEvaluationResponse

router = APIRouter()
limiter = Limiter(key_func=get_remote_address)


@router.get("", response_model=RiskEvaluationResponse)
async def get_crop_risk(
    farm_id: Optional[str] = Query(default=None, description="Optional Farm ID"),
    crop: Optional[str] = Query(default=None, description="Optional Crop type (e.g. Tomato)"),
    lat: Optional[float] = Query(default=None, description="Latitude"),
    lon: Optional[float] = Query(default=None, description="Longitude"),
    current_user: dict = Depends(get_current_user),
):
    """
    Synthesize disease predictions, current weather, forecast, and soil moisture
    into an explainable crop disease risk score (0–100).
    """
    uid = current_user.get("uid")
    return await risk_service.assess_farm_risk(
        farm_id=farm_id,
        crop_type=crop,
        latitude=lat,
        longitude=lon,
        user_id=uid,
    )


@router.post("/evaluate", response_model=RiskEvaluationResponse)
@router.post("/assess", response_model=RiskEvaluationResponse)
async def evaluate_risk_post(
    payload: RiskEvaluationRequest,
    current_user: dict = Depends(get_current_user),
):
    """
    Evaluate crop risk using payload parameters.
    """
    uid = current_user.get("uid")
    return await risk_service.assess_farm_risk(
        farm_id=payload.farm_id,
        crop_type=payload.crop_type,
        latitude=payload.latitude,
        longitude=payload.longitude,
        user_id=uid,
        temperature=payload.temperature,
        humidity=payload.humidity,
        rainfall_mm=payload.rainfall_mm,
        recent_disease_count=payload.recent_disease_count,
    )
