"""
CropPulse – Map Router
GET /api/v1/map/markers         – All farm markers with disease status
GET /api/v1/map/heatmap         – Heatmap data points
GET /api/v1/map/disease-hotspots – Disease outbreak clusters
GET /api/v1/map/my-farms        – Current user's farms on map
"""

from typing import Optional
from fastapi import APIRouter, Depends, Query
from loguru import logger

from backend.config import settings
from backend.dependencies import get_current_user
from backend.services.mongodb_service import MongoDBService
from backend.utils.helpers import marker_color_from_severity

router = APIRouter()

_farm_svc = MongoDBService(settings.COLLECTION_FARMS, id_field="farm_id")
_disease_svc = MongoDBService(settings.COLLECTION_DISEASE_PREDICTIONS, id_field="prediction_id")


@router.get("/markers")
async def get_map_markers(
    disease: Optional[str] = Query(default=None, description="Filter by disease name"),
    severity: Optional[str] = Query(default=None, description="Filter by severity"),
    district: Optional[str] = Query(default=None, description="Filter by district"),
    crop: Optional[str] = Query(default=None, description="Filter by crop type"),
    limit: int = Query(default=200, le=500),
    current_user: dict = Depends(get_current_user),
):
    """
    Return all farm markers for the GIS map.
    Each marker includes the latest disease/soil status for color coding.
    """
    # Fetch recent disease predictions
    disease_preds = await _disease_svc.list_all(limit=500)

    # Build farm_id → latest prediction lookup
    farm_latest: dict = {}
    for pred in disease_preds:
        fid = pred.get("farm_id")
        if not fid:
            continue
        existing = farm_latest.get(fid)
        # Handle string comparisons correctly
        pred_created = str(pred.get("created_at", ""))
        existing_created = str(existing.get("created_at", "")) if existing else ""
        if not existing or pred_created > existing_created:
            farm_latest[fid] = pred

    # Fetch all farms
    farms = await _farm_svc.list_all(limit=limit)
    markers = []

    for farm in farms:
        lat = farm.get("latitude")
        lon = farm.get("longitude")
        if lat is None or lon is None:
            continue

        latest = farm_latest.get(farm.get("farm_id", ""), {})
        last_disease = latest.get("disease_name", "No data")
        last_severity = latest.get("severity", "unknown")
        color = marker_color_from_severity(last_severity) if latest else "grey"

        marker = {
            "farm_id": farm.get("farm_id"),
            "name": farm.get("name", "Unknown Farm"),
            "user_id": farm.get("user_id"),
            "latitude": lat,
            "longitude": lon,
            "district": farm.get("district"),
            "state": farm.get("state"),
            "crop_types": farm.get("crop_types", []),
            "soil_type": farm.get("soil_type"),
            "last_disease": last_disease,
            "last_severity": last_severity,
            "last_moisture": farm.get("last_moisture"),
            "marker_color": color,
            "total_predictions": farm.get("total_predictions", 0),
        }

        # Apply filters
        if disease and disease.lower() not in last_disease.lower():
            continue
        if severity and severity.lower() != last_severity.lower():
            continue
        if district and farm.get("district", "").lower() != district.lower():
            continue
        if crop and not any(crop.lower() in c.lower() for c in farm.get("crop_types", [])):
            continue

        markers.append(marker)

    return {"markers": markers, "total": len(markers)}


@router.get("/heatmap")
async def get_heatmap_data(
    current_user: dict = Depends(get_current_user),
):
    """
    Return heatmap data points (lat, lng, intensity) for disease severity visualization.
    Intensity is mapped from severity: healthy=0.1, mild=0.3, moderate=0.6, severe=1.0
    """
    preds = await _disease_svc.list_all(limit=500)
    intensity_map = {"healthy": 0.1, "mild": 0.3, "moderate": 0.6, "severe": 1.0}
    points = []
    for p in preds:
        lat = p.get("latitude")
        lon = p.get("longitude")
        if lat and lon:
            severity = p.get("severity", "healthy")
            intensity = intensity_map.get(severity, 0.5)
            points.append([lat, lon, intensity])

    return {"points": points, "total": len(points)}


@router.get("/disease-hotspots")
async def get_disease_hotspots(
    current_user: dict = Depends(get_current_user),
):
    """
    Return severe/moderate disease hotspot clusters for the map.
    """
    preds = await _disease_svc.list_all(limit=500)
    hotspots = []
    for p in preds:
        if p.get("severity") in ("severe", "moderate") and p.get("latitude"):
            hotspots.append({
                "prediction_id": p.get("prediction_id"),
                "disease_name": p.get("disease_name"),
                "severity": p.get("severity"),
                "confidence": p.get("confidence"),
                "crop_type": p.get("crop_type"),
                "district": p.get("district"),
                "state": p.get("state"),
                "latitude": p.get("latitude"),
                "longitude": p.get("longitude"),
                "created_at": str(p.get("created_at", "")),
            })
    return {"hotspots": hotspots, "total": len(hotspots)}


@router.get("/my-farms")
async def get_my_farm_markers(current_user: dict = Depends(get_current_user)):
    """Return only the current user's farms as map markers."""
    uid = current_user["uid"]
    farms = await _farm_svc.query("user_id", "==", uid, limit=50)
    markers = [
        {
            "farm_id": f.get("farm_id"),
            "name": f.get("name"),
            "latitude": f.get("latitude"),
            "longitude": f.get("longitude"),
            "crop_types": f.get("crop_types", []),
            "soil_type": f.get("soil_type"),
            "district": f.get("district"),
            "state": f.get("state"),
            "marker_color": "blue",
        }
        for f in farms if f.get("latitude") and f.get("longitude")
    ]
    return {"markers": markers, "total": len(markers)}
