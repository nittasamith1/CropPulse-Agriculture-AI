"""
CropPulse – Precision Irrigation Router
GET  /api/v1/irrigation/recommendation – Compute precision irrigation advice
POST /api/v1/irrigation/calculate      – Ad-hoc precision irrigation calculation
"""

from typing import Optional
from fastapi import APIRouter, Depends, Query, status
from slowapi import Limiter
from slowapi.util import get_remote_address

from backend.dependencies import get_current_user
from backend.services.irrigation_service import irrigation_service
from backend.models.irrigation import IrrigationRecommendationRequest, IrrigationRecommendationResponse

router = APIRouter()
limiter = Limiter(key_func=get_remote_address)


@router.get("", response_model=IrrigationRecommendationResponse)
@router.get("/recommendation", response_model=IrrigationRecommendationResponse)
async def get_irrigation_recommendation(
    farm_id: Optional[str] = Query(default=None, description="Farm ID"),
    crop: Optional[str] = Query(default=None, description="Crop name"),
    growth_stage: str = Query(default="mid", description="Crop growth stage: initial|mid|late"),
    soil_type: Optional[str] = Query(default="loamy", description="Soil type"),
    lat: Optional[float] = Query(default=None, description="Latitude"),
    lon: Optional[float] = Query(default=None, description="Longitude"),
    current_user: dict = Depends(get_current_user),
):
    """
    Generate agronomic irrigation recommendations: IRRIGATE, WAIT, REDUCE IRRIGATION, or MONITOR.
    Evaluates weather forecast, current soil moisture, and crop coefficient.
    """
    uid = current_user.get("uid")
    return await irrigation_service.get_farm_irrigation_recommendation(
        farm_id=farm_id,
        crop_type=crop,
        soil_type=soil_type,
        latitude=lat,
        longitude=lon,
        user_id=uid,
        growth_stage=growth_stage,
    )


@router.post("/calculate", response_model=IrrigationRecommendationResponse)
@router.post("/recommend", response_model=IrrigationRecommendationResponse)
async def calculate_irrigation(
    payload: IrrigationRecommendationRequest,
    current_user: dict = Depends(get_current_user),
):
    """Calculate irrigation recommendation via request body."""
    uid = current_user.get("uid")
    return await irrigation_service.get_farm_irrigation_recommendation(
        farm_id=payload.farm_id,
        crop_type=payload.crop_type,
        soil_type=payload.soil_type,
        latitude=payload.latitude,
        longitude=payload.longitude,
        user_id=uid,
        growth_stage=payload.growth_stage,
        soil_moisture=payload.soil_moisture,
        temperature=payload.temperature,
        humidity=payload.humidity,
        rain_probability_24h=payload.rain_probability_24h,
        forecast_precipitation_24h=payload.forecast_precipitation_24h,
    )
