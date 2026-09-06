"""
CropPulse – Precision Irrigation Schemas
Pydantic schemas for precision irrigation recommendations.
"""

from typing import Optional, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field


class IrrigationRecommendationRequest(BaseModel):
    farm_id: Optional[str] = None
    crop_type: Optional[str] = "Tomato"
    growth_stage: str = Field(default="mid", description="'initial' | 'mid' | 'late'")
    soil_type: Optional[str] = "loamy"
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    soil_moisture: Optional[float] = None
    temperature: Optional[float] = None
    humidity: Optional[float] = None
    rain_probability_24h: Optional[float] = None
    forecast_precipitation_24h: Optional[float] = None


class IrrigationRecommendationResponse(BaseModel):
    recommendation_id: str
    farm_id: Optional[str] = None
    farm_name: Optional[str] = "Farm Plot"
    crop: str
    growth_stage: str
    soil_type: str
    action: str = Field(..., description="'IRRIGATE' | 'WAIT' | 'REDUCE IRRIGATION' | 'MONITOR'")
    confidence: float = Field(..., ge=0.0, le=1.0)
    reason: str
    priority: str = Field(..., description="'low' | 'medium' | 'high' | 'urgent'")
    water_amount_mm: float
    litres_per_hectare: int
    recommended_method: str = Field(default="drip", description="'drip' | 'micro-sprinkler'")
    decision_confidence: Optional[str] = None
    water_balance: Optional[Dict[str, Any]] = None
    soil_moisture_level: float
    field_capacity_reference: float
    weather_forecast_summary: Optional[Dict[str, Any]] = None
    disclaimer: str
    created_at: datetime
