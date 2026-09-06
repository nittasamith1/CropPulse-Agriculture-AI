"""
CropPulse – History Router
GET /api/v1/history           – Paginated combined disease and soil prediction history
GET /api/v1/history/dashboard – Aggregated metrics and analytics for farmer dashboard
"""

from datetime import datetime, timezone, timedelta
from typing import Optional
from fastapi import APIRouter, Depends, Query

from backend.dependencies import get_current_user
from backend.repositories.prediction_repository import prediction_repository
from backend.repositories.farm_repository import farm_repository

router = APIRouter()


@router.get("")
@router.get("/")
async def get_combined_history(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    prediction_type: str = Query(default="all", description="all | disease | soil"),
    farm_id: Optional[str] = Query(default=None),
    current_user: dict = Depends(get_current_user),
):
    """
    Return paginated prediction history with server-side cursor pagination.
    """
    uid = current_user["uid"]
    disease_items = []
    soil_items = []
    d_total = 0
    s_total = 0

    if prediction_type in ("all", "disease"):
        disease_items, d_total = await prediction_repository.list_disease_predictions_paginated(
            user_id=uid, farm_id=farm_id, page=page, page_size=page_size
        )

    if prediction_type in ("all", "soil"):
        soil_items, s_total = await prediction_repository.list_soil_predictions_paginated(
            user_id=uid, farm_id=farm_id, page=page, page_size=page_size
        )

    total_records = d_total + s_total
    total_pages = (max(d_total, s_total) + page_size - 1) // max(1, page_size)

    return {
        "total": total_records,
        "page": page,
        "page_size": page_size,
        "total_pages": total_pages,
        "disease_total": d_total,
        "soil_total": s_total,
        "disease_predictions": disease_items,
        "soil_predictions": soil_items,
    }


@router.get("/dashboard")
async def get_dashboard_stats(current_user: dict = Depends(get_current_user)):
    """
    Return aggregated statistics for user dashboard.
    """
    uid = current_user["uid"]

    # 1. User farms
    farms = await farm_repository.get_user_farms(user_id=uid)

    # 2. Recent predictions with server-side pagination (limit=5)
    recent_disease, total_disease = await prediction_repository.list_disease_predictions_paginated(
        user_id=uid, page=1, page_size=5
    )
    recent_soil, total_soil = await prediction_repository.list_soil_predictions_paginated(
        user_id=uid, page=1, page_size=5
    )

    # 3. Aggregation summary & detailed breakdowns
    summary = await prediction_repository.get_analytics_summary(user_id=uid)
    severity_breakdown = await prediction_repository.get_severity_breakdown(user_id=uid)
    health_counts = await prediction_repository.get_health_counts(user_id=uid)
    soil_summary = await prediction_repository.get_soil_summary(user_id=uid)
    monthly_disease, monthly_soil = await prediction_repository.get_monthly_counts(user_id=uid, months=6)

    # Healthy fields count
    healthy_farms_count = sum(
        1 for f in farms if (f.get("last_severity") in ["healthy", "none"] or f.get("last_severity") is None)
    )

    return {
        "total_farms": len(farms),
        "healthy_farms": healthy_farms_count,
        "total_disease_predictions": total_disease,
        "total_soil_predictions": total_soil,
        "total_predictions": total_disease + total_soil,
        "recent_disease_predictions": recent_disease,
        "recent_soil_predictions": recent_soil,
        "top_diseases": summary.get("top_diseases", []),
        "farms": farms[:10],
        "severity_breakdown": severity_breakdown,
        "healthy_count": health_counts["healthy_count"],
        "diseased_count": health_counts["diseased_count"],
        "average_soil_moisture": soil_summary["average_soil_moisture"],
        "irrigation_needed_count": soil_summary["irrigation_needed_count"],
        "monthly_disease_counts": monthly_disease,
        "monthly_soil_counts": monthly_soil,
    }
