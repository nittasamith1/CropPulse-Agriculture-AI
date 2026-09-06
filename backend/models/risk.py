"""
CropPulse – Crop Risk Schemas
Pydantic schemas for multi-factor disease risk assessments.
"""

from typing import List, Optional, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field


class RiskEvaluationRequest(BaseModel):
    farm_id: Optional[str] = None
    crop_type: Optional[str] = "Tomato"
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    temperature: Optional[float] = None
    humidity: Optional[float] = None
    rainfall_mm: Optional[float] = None
    recent_disease_count: Optional[int] = None
    season: Optional[str] = None


class RiskEvaluationResponse(BaseModel):
    assessment_id: str
    farm_id: Optional[str] = None
    farm_name: Optional[str] = "Field Plot"
    crop: str
    latitude: float
    longitude: float
    risk_score: int = Field(..., ge=0, le=100, description="Composite disease risk score (0-100)")
    risk_level: str = Field(..., description="'LOW' | 'MODERATE' | 'HIGH' | 'CRITICAL'")
    factors: List[str] = Field(default=[], description="Contributing agricultural and weather factors")
    breakdown: Dict[str, float]
    weather_summary: Optional[Dict[str, Any]] = None
    disclaimer: str
    created_at: datetime
