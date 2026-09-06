"""
CropPulse – User Models and Pydantic Schemas
Defines request/response models for JWT authentication, profile, and farm management.
"""

from typing import Optional, List
from pydantic import BaseModel, EmailStr, Field, ConfigDict
from datetime import datetime


# ── Request Models ────────────────────────────────────────────────────────────

class UserRegisterRequest(BaseModel):
    """User registration payload."""
    email: EmailStr
    password: str = Field(..., min_length=8, description="Password must be at least 8 characters")
    name: str = Field(..., min_length=2, max_length=100)
    role: str = Field(default="farmer", description="Role: farmer or admin")
    phone: Optional[str] = None
    state: Optional[str] = None
    district: Optional[str] = None

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "email": "farmer@example.com",
                "password": "SecurePass123",
                "name": "John Farmer",
                "role": "farmer",
                "phone": "+91 9876543210",
                "state": "Karnataka",
                "district": "Bangalore",
            }
        }
    )


class LoginRequest(BaseModel):
    """JWT User Login payload."""
    email: EmailStr
    password: str = Field(..., min_length=8)


class TokenResponse(BaseModel):
    """JWT tokens response payload."""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    role: str
    name: str


class RefreshTokenRequest(BaseModel):
    """Refresh token verification payload."""
    refresh_token: str


class ForgotPasswordRequest(BaseModel):
    """Request forgot password reset link."""
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    """Password reset payload using reset token."""
    token: str
    new_password: str = Field(..., min_length=8, description="Password must be at least 8 characters")


class ChangePasswordRequest(BaseModel):
    """Request to change password inside settings."""
    current_password: str = Field(..., min_length=8)
    new_password: str = Field(..., min_length=8, description="Password must be at least 8 characters")


class UserUpdateRequest(BaseModel):
    """Update user profile."""
    name: Optional[str] = None
    phone: Optional[str] = None
    state: Optional[str] = None
    district: Optional[str] = None
    profile_picture_url: Optional[str] = None


class LocationModel(BaseModel):
    """Geographic location coordinates."""
    latitude: float = Field(..., ge=-90, le=90)
    longitude: float = Field(..., ge=-180, le=180)


# ── Response Models ───────────────────────────────────────────────────────────

class UserProfileResponse(BaseModel):
    """User profile response."""
    uid: str
    email: str
    name: str
    role: str
    phone: Optional[str] = None
    state: Optional[str] = None
    district: Optional[str] = None
    profile_picture_url: Optional[str] = None
    farm_ids: List[str] = []
    is_email_verified: bool = False
    is_active: bool = True
    total_predictions: int = 0
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "uid": "user123",
                "email": "farmer@example.com",
                "name": "John Farmer",
                "role": "farmer",
                "phone": "+91 9876543210",
                "state": "Karnataka",
                "district": "Bangalore",
                "profile_picture_url": None,
                "farm_ids": ["farm001", "farm002"],
                "is_email_verified": True,
                "is_active": True,
                "total_predictions": 42,
                "created_at": "2025-06-26T10:30:00Z",
                "updated_at": "2025-06-26T15:45:00Z",
            }
        }
    )


class MessageResponse(BaseModel):
    """Generic message response."""
    message: str

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "message": "Operation completed successfully."
            }
        }
    )


class DiseaseResultResponse(BaseModel):
    """Disease prediction result."""
    success: bool
    prediction_id: str
    disease_name: str
    confidence: float
    confidence_percent: str
    severity: str
    affected_area_percent: float
    is_healthy: bool
    crop_type: Optional[str] = None
    image_url: str
    treatments: List[str]
    prevention_tips: List[str]
    recommended_pesticides: List[str]
    organic_alternatives: List[str]
    top_predictions: List[dict]
    image_quality: dict
    stub_mode: bool
    model_version: str
    created_at: str


class SoilResultResponse(BaseModel):
    """Soil moisture prediction result."""
    success: bool
    prediction_id: str
    predicted_moisture: float
    moisture_percent: str
    irrigation_recommendation: str
    next_watering_days: int
    confidence: float
    created_at: str
