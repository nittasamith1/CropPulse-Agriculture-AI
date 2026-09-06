"""
CropPulse – Pydantic Models: Farm
Farm geographic and agronomic information schemas.
"""

from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field


class FarmLocation(BaseModel):
    """GeoPoint representation."""
    latitude: float = Field(..., ge=-90, le=90)
    longitude: float = Field(..., ge=-180, le=180)


class FarmCreateRequest(BaseModel):
    """Create a new farm."""
    name: str = Field(..., min_length=2, max_length=100)
    location: FarmLocation
    area_acres: Optional[float] = Field(default=None, ge=0, le=100000)
    crop_types: List[str] = Field(default_factory=list)
    soil_type: Optional[str] = Field(
        default=None,
        description="sandy | loamy | clay | silt | peaty"
    )
    district: Optional[str] = None
    state: Optional[str] = None
    irrigation_type: Optional[str] = None
    notes: Optional[str] = Field(default=None, max_length=500)


class FarmUpdateRequest(BaseModel):
    """Update an existing farm."""
    name: Optional[str] = Field(default=None, min_length=2, max_length=100)
    location: Optional[FarmLocation] = None
    area_acres: Optional[float] = Field(default=None, ge=0)
    crop_types: Optional[List[str]] = None
    soil_type: Optional[str] = None
    district: Optional[str] = None
    state: Optional[str] = None
    irrigation_type: Optional[str] = None
    notes: Optional[str] = Field(default=None, max_length=500)


class FarmResponse(BaseModel):
    """Farm document returned by API."""
    farm_id: str
    user_id: str
    name: str
    latitude: float
    longitude: float
    area_acres: Optional[float] = None
    crop_types: List[str] = []
    soil_type: Optional[str] = None
    district: Optional[str] = None
    state: Optional[str] = None
    irrigation_type: Optional[str] = None
    notes: Optional[str] = None
    total_predictions: int = 0
    last_prediction_at: Optional[datetime] = None
    created_at: datetime
    updated_at: Optional[datetime] = None


class FarmMapMarker(BaseModel):
    """Compact farm representation for GIS map rendering."""
    farm_id: str
    name: str
    latitude: float
    longitude: float
    district: Optional[str] = None
    state: Optional[str] = None
    crop_types: List[str] = []
    last_disease: Optional[str] = None
    last_severity: Optional[str] = None  # healthy | mild | moderate | severe
    last_moisture: Optional[float] = None
    marker_color: str = "green"  # green | yellow | orange | red
