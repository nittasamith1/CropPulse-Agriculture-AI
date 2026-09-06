"""
CropPulse – Soil Prediction Router
POST /api/v1/soil/predict  – Predict soil moisture and generate precision irrigation guidance
GET  /api/v1/soil/history  – Paginated soil moisture history
GET  /api/v1/soil/{id}     – Get single soil prediction by ID
"""

from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Request, status
from slowapi import Limiter
from slowapi.util import get_remote_address

from backend.dependencies import get_current_user
from backend.services.soil_service import soil_service
from backend.repositories.prediction_repository import prediction_repository
from backend.models.prediction import SoilPredictionRequest, SoilPredictionResponse
from backend.ai.soil.predictor import SoilModelNotAvailableError

router = APIRouter()
limiter = Limiter(key_func=get_remote_address)


@router.post("/predict", response_model=SoilPredictionResponse, status_code=status.HTTP_201_CREATED)
@limiter.limit("30/minute")
async def predict_soil(
    request: Request,
    payload: SoilPredictionRequest,
    current_user: dict = Depends(get_current_user),
):
    """
    Predict soil moisture percentage and generate precision irrigation guidance.
    """
    uid = current_user["uid"]
    valid_soils = {"sandy", "loamy", "clay", "silt", "peaty"}
    if payload.soil_type.lower().strip() not in valid_soils:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid soil_type '{payload.soil_type}'. Allowed: {', '.join(valid_soils)}",
        )

    try:
        result = await soil_service.predict_soil_moisture(
            temperature=payload.temperature,
            humidity=payload.humidity,
            rainfall=payload.rainfall,
            wind_speed=payload.wind_speed,
            soil_type=payload.soil_type,
            previous_moisture=payload.previous_moisture,
            user_id=uid,
            farm_id=payload.farm_id,
            crop_type=payload.crop_type,
            latitude=payload.latitude,
            longitude=payload.longitude,
        )
        return result
    except SoilModelNotAvailableError as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "code": "MODEL_NOT_AVAILABLE",
                "message": str(e),
                "instructions": "Run `python -m ai_models.soil_model.train_soil_model` to generate soil_model.pkl.",
            },
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Soil moisture prediction failed: {str(e)}",
        )


@router.get("/history")
async def get_soil_history(
    page: int = 1,
    page_size: int = 20,
    farm_id: Optional[str] = None,
    current_user: dict = Depends(get_current_user),
):
    """Return paginated soil prediction history for current user."""
    uid = current_user["uid"]
    items, total = await prediction_repository.list_soil_predictions_paginated(
        user_id=uid, farm_id=farm_id, page=page, page_size=page_size
    )
    total_pages = (total + page_size - 1) // max(1, page_size)
    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": total_pages,
        "predictions": items,
    }


@router.get("/{prediction_id}")
async def get_soil_prediction(
    prediction_id: str,
    current_user: dict = Depends(get_current_user),
):
    """Fetch single soil prediction by ID."""
    doc = await prediction_repository.get_soil_prediction(prediction_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Soil prediction not found.")
    if doc.get("user_id") != current_user["uid"] and current_user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Access denied.")
    return doc
