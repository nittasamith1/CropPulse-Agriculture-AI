"""
CropPulse – Disease Detection Router
POST /api/v1/disease/detect   – Upload leaf image and run PyTorch disease detection with Grad-CAM
POST /api/v1/disease/predict  – Backward-compatible alias
GET  /api/v1/disease/history  – Paginated disease prediction history for current user
GET  /api/v1/disease/{id}     – Get single prediction by ID
"""

from typing import Optional
from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile, status
from slowapi import Limiter
from slowapi.util import get_remote_address

from backend.dependencies import get_current_user
from backend.services.disease_service import disease_service
from backend.repositories.prediction_repository import prediction_repository
from backend.ai.disease.predictor import ModelNotAvailableError

router = APIRouter()
limiter = Limiter(key_func=get_remote_address)


async def _handle_detection(
    file: UploadFile,
    farm_id: Optional[str],
    crop_type: Optional[str],
    latitude: Optional[float],
    longitude: Optional[float],
    notes: Optional[str],
    current_user: dict,
):
    uid = current_user["uid"]
    try:
        result = await disease_service.detect_disease(
            file=file,
            user_id=uid,
            farm_id=farm_id,
            crop_type=crop_type,
            latitude=latitude,
            longitude=longitude,
            notes=notes,
        )
        return {"success": True, **result}
    except ModelNotAvailableError as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "code": "MODEL_NOT_AVAILABLE",
                "message": str(e),
                "instructions": "Place trained PyTorch weights at the configured DISEASE_MODEL_PATH (.pth).",
            },
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Disease detection failed: {str(e)}",
        )


@router.post("/detect", status_code=status.HTTP_201_CREATED)
@limiter.limit("30/minute")
async def detect_disease(
    request: Request,
    file: UploadFile = File(..., description="Crop leaf image (JPG, PNG, WEBP)"),
    farm_id: Optional[str] = Form(default=None),
    crop_type: Optional[str] = Form(default=None),
    latitude: Optional[float] = Form(default=None),
    longitude: Optional[float] = Form(default=None),
    notes: Optional[str] = Form(default=None),
    current_user: dict = Depends(get_current_user),
):
    """
    Upload crop leaf image and detect plant disease using PyTorch EfficientNet-B0.
    Returns disease classification, confidence, severity, Grad-CAM visual heatmap, and treatments.
    """
    return await _handle_detection(
        file=file,
        farm_id=farm_id,
        crop_type=crop_type,
        latitude=latitude,
        longitude=longitude,
        notes=notes,
        current_user=current_user,
    )


@router.post("/predict", status_code=status.HTTP_201_CREATED)
@limiter.limit("30/minute")
async def predict_disease_alias(
    request: Request,
    file: UploadFile = File(..., description="Crop leaf image (JPG, PNG, WEBP)"),
    farm_id: Optional[str] = Form(default=None),
    crop_type: Optional[str] = Form(default=None),
    latitude: Optional[float] = Form(default=None),
    longitude: Optional[float] = Form(default=None),
    notes: Optional[str] = Form(default=None),
    current_user: dict = Depends(get_current_user),
):
    """Backward-compatible alias for /detect."""
    return await _handle_detection(
        file=file,
        farm_id=farm_id,
        crop_type=crop_type,
        latitude=latitude,
        longitude=longitude,
        notes=notes,
        current_user=current_user,
    )


@router.get("/history")
async def get_disease_history(
    page: int = 1,
    page_size: int = 20,
    farm_id: Optional[str] = None,
    current_user: dict = Depends(get_current_user),
):
    """Return paginated disease prediction history for the current user."""
    uid = current_user["uid"]
    preds, total = await prediction_repository.list_disease_predictions_paginated(
        user_id=uid, farm_id=farm_id, page=page, page_size=page_size
    )
    total_pages = (total + page_size - 1) // max(1, page_size)
    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": total_pages,
        "predictions": preds,
    }


@router.get("/{prediction_id}")
async def get_disease_prediction(
    prediction_id: str,
    current_user: dict = Depends(get_current_user),
):
    """Fetch single disease prediction by ID."""
    doc = await prediction_repository.get_disease_prediction(prediction_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Prediction not found.")
    if doc.get("user_id") != current_user["uid"] and current_user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Access denied.")
    return doc
