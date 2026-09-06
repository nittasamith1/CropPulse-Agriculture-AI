"""
CropPulse – Pydantic Models: Prediction & Intelligence
Defines schemas for disease detection, soil moisture prediction,
history records, and report requests.
"""

from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field


# ── Disease Detection ─────────────────────────────────────────────────────────

class TopClassPrediction(BaseModel):
    class_key: str
    display_name: str
    confidence: float


class DiseaseDetectionResponse(BaseModel):
    """Result returned after processing a leaf image."""
    prediction_id: str
    user_id: str
    farm_id: Optional[str] = None
    image_url: str
    disease_name: str
    disease_class_key: Optional[str] = None
    confidence: float = Field(..., ge=0.0, le=1.0)
    severity: str  # "healthy" | "mild" | "moderate" | "severe"
    is_healthy: bool = False
    affected_area_percent: Optional[float] = 0.0
    crop_type: Optional[str] = None
    treatments: List[str] = []
    prevention_tips: List[str] = []
    recommended_pesticides: List[str] = []
    organic_remedies: List[str] = []
    top_3: List[TopClassPrediction] = []
    explanation_available: bool = False
    explanation_data_uri: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    district: Optional[str] = None
    state: Optional[str] = None
    created_at: datetime
    model_version: str = "EfficientNet-B0"


class DiseasePredictionHistory(BaseModel):
    """Compact record for history list view."""
    prediction_id: str
    disease_name: str
    confidence: float
    severity: str
    crop_type: Optional[str] = None
    image_url: str
    created_at: datetime
    farm_id: Optional[str] = None


# ── Soil Moisture Prediction ──────────────────────────────────────────────────

class SoilPredictionRequest(BaseModel):
    """Input features for soil moisture prediction model."""
    temperature: float = Field(..., ge=-10, le=60, description="Temperature in °C")
    humidity: float = Field(..., ge=0, le=100, description="Relative humidity %")
    rainfall: float = Field(..., ge=0, le=500, description="Rainfall in mm")
    wind_speed: float = Field(default=10.0, ge=0, le=150, description="Wind speed in km/h")
    soil_type: str = Field(default="loamy", description="sandy|loamy|clay|silt|peaty")
    previous_moisture: float = Field(default=50.0, ge=0, le=100, description="Previous moisture %")
    farm_id: Optional[str] = None
    crop_type: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None


class SoilPredictionResponse(BaseModel):
    """Result returned after soil moisture prediction."""
    prediction_id: str
    user_id: str
    farm_id: Optional[str] = None
    predicted_moisture: float
    water_requirement_mm: float
    irrigation_recommended: bool
    irrigation_action: Optional[str] = "MONITOR"
    irrigation_reason: Optional[str] = None
    irrigation_type: str = "drip"
    litres_per_hectare: Optional[int] = 0
    priority: Optional[str] = "low"
    recommendation_text: str
    input_features: Dict[str, Any]
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    disclaimer: Optional[str] = None
    created_at: datetime
    model_version: str = "XGBoost-v1"


class SoilPredictionHistory(BaseModel):
    """Compact record for history list view."""
    prediction_id: str
    predicted_moisture: float
    irrigation_recommended: bool
    irrigation_type: str
    created_at: datetime
    farm_id: Optional[str] = None


# ── Combined Paginated History ────────────────────────────────────────────────

class PredictionHistoryResponse(BaseModel):
    """Paginated combined prediction history."""
    total: int
    page: int
    page_size: int
    total_pages: int
    disease_predictions: List[DiseasePredictionHistory] = []
    soil_predictions: List[SoilPredictionHistory] = []


# ── Notification ──────────────────────────────────────────────────────────────

class NotificationModel(BaseModel):
    """Notification document."""
    notification_id: str
    user_id: str
    title: str
    message: str
    type: str
    read: bool = False
    data: Optional[Dict[str, Any]] = None
    created_at: datetime


# ── Report ────────────────────────────────────────────────────────────────────

class ReportRequest(BaseModel):
    """Request to generate a PDF report."""
    report_type: str = Field(..., pattern="^(disease|soil|combined|farm_health)$")
    farm_id: Optional[str] = None
    prediction_ids: Optional[List[str]] = None


class ReportResponse(BaseModel):
    """Report generation result."""
    report_id: str
    user_id: str
    report_type: str
    title: str
    pdf_url: str
    prediction_count: int
    created_at: datetime
