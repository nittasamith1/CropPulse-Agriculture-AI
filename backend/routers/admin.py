"""
CropPulse – Admin Router
Protected endpoints for platform administrators. Handles user moderation, platform-wide analytics, and logs.
"""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from loguru import logger

from backend.config import settings
from backend.dependencies import require_admin
from backend.services.mongodb_service import MongoDBService
from backend.utils.helpers import utc_now

router = APIRouter()

_user_svc = MongoDBService(settings.COLLECTION_USERS, id_field="uid")
_disease_svc = MongoDBService(settings.COLLECTION_DISEASE_PREDICTIONS, id_field="prediction_id")
_soil_svc = MongoDBService(settings.COLLECTION_SOIL_PREDICTIONS, id_field="prediction_id")
_farm_svc = MongoDBService(settings.COLLECTION_FARMS, id_field="farm_id")
_report_svc = MongoDBService(settings.COLLECTION_REPORTS, id_field="report_id")


@router.get("/users")
async def list_users(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    role: str = Query(default="all", description="all | farmer | admin"),
    admin: dict = Depends(require_admin),
):
    """Return all registered users with pagination."""
    all_users = await _user_svc.list_all(limit=1000)
    if role != "all":
        all_users = [u for u in all_users if u.get("role") == role]
    total = len(all_users)
    start = (page - 1) * page_size
    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "users": all_users[start: start + page_size],
    }


@router.get("/users/{uid}")
async def get_user(uid: str, admin: dict = Depends(require_admin)):
    """Get a single user's full profile."""
    doc = await _user_svc.get(uid)
    if not doc:
        raise HTTPException(status_code=404, detail="User not found.")
    return doc


@router.delete("/users/{uid}")
async def delete_user(uid: str, admin: dict = Depends(require_admin)):
    """
    Delete a user from the platform (MongoDB).
    Also deletes their predictions and farm records.
    """
    if uid == admin["uid"]:
        raise HTTPException(status_code=400, detail="Cannot delete your own admin account.")

    # Delete user profile document
    deleted = await _user_svc.delete(uid)
    if not deleted:
        raise HTTPException(status_code=404, detail="User not found.")

    # Clean up predictions
    d_preds = await _disease_svc.query("user_id", "==", uid, limit=200)
    for p in d_preds:
        await _disease_svc.delete(p["prediction_id"])

    s_preds = await _soil_svc.query("user_id", "==", uid, limit=200)
    for p in s_preds:
        await _soil_svc.delete(p["prediction_id"])

    # Clean up farms
    farms = await _farm_svc.query("user_id", "==", uid, limit=50)
    for f in farms:
        await _farm_svc.delete(f["farm_id"])

    logger.info(f"Admin {admin['uid']} deleted user {uid}")
    return {"message": f"User {uid} deleted successfully.", "success": True}


@router.post("/users/{uid}/toggle-status")
async def toggle_user_status(uid: str, admin: dict = Depends(require_admin)):
    """Enable or disable a user account."""
    doc = await _user_svc.get(uid)
    if not doc:
        raise HTTPException(status_code=404, detail="User not found.")
    new_status = not doc.get("is_active", True)
    await _user_svc.update(uid, {"is_active": new_status, "updated_at": utc_now()})
    action = "activated" if new_status else "deactivated"
    logger.info(f"Admin {admin['uid']} {action} user {uid}")
    return {"message": f"User {action} successfully.", "is_active": new_status}


@router.get("/analytics")
async def get_platform_analytics(admin: dict = Depends(require_admin)):
    """
    Return platform-wide analytics for the admin dashboard.
    """
    all_users = await _user_svc.list_all(limit=5000)
    all_disease = await _disease_svc.list_all(limit=5000)
    all_soil = await _soil_svc.list_all(limit=5000)
    all_farms = await _farm_svc.list_all(limit=5000)

    # User stats
    total_users = len(all_users)
    active_users = sum(1 for u in all_users if u.get("is_active", True))
    farmers = sum(1 for u in all_users if u.get("role") == "farmer")
    admins = sum(1 for u in all_users if u.get("role") == "admin")

    # Disease stats
    severity_breakdown = {"healthy": 0, "mild": 0, "moderate": 0, "severe": 0}
    disease_counts: dict = {}
    crop_counts: dict = {}

    for p in all_disease:
        sev = p.get("severity", "unknown")
        if sev in severity_breakdown:
            severity_breakdown[sev] += 1
        disease = p.get("disease_name", "Unknown")
        disease_counts[disease] = disease_counts.get(disease, 0) + 1
        crop = p.get("crop_type", "Unknown")
        crop_counts[crop] = crop_counts.get(crop, 0) + 1

    # Top diseases
    top_diseases = sorted(disease_counts.items(), key=lambda x: x[1], reverse=True)[:10]

    # Soil stats
    irrigation_count = sum(1 for p in all_soil if p.get("irrigation_recommended"))
    avg_moisture = (
        sum(p.get("predicted_moisture", 0) for p in all_soil) / len(all_soil)
        if all_soil else 0
    )

    return {
        "users": {
            "total": total_users,
            "active": active_users,
            "inactive": total_users - active_users,
            "farmers": farmers,
            "admins": admins,
        },
        "disease_predictions": {
            "total": len(all_disease),
            "severity_breakdown": severity_breakdown,
            "top_diseases": [{"name": k, "count": v} for k, v in top_diseases],
            "top_crops": sorted(
                [{"crop": k, "count": v} for k, v in crop_counts.items()],
                key=lambda x: x["count"], reverse=True
            )[:10],
        },
        "soil_predictions": {
            "total": len(all_soil),
            "irrigation_recommended_count": irrigation_count,
            "average_moisture": round(avg_moisture, 1),
        },
        "farms": {
            "total": len(all_farms),
        },
        "platform_totals": {
            "total_predictions": len(all_disease) + len(all_soil),
        },
    }


@router.get("/disease-outbreaks")
async def get_disease_outbreaks(
    severity: str = Query(default="severe", description="severe | moderate"),
    admin: dict = Depends(require_admin),
):
    """Return active disease outbreaks filtered by severity."""
    preds = await _disease_svc.list_all(limit=1000)
    outbreaks = [
        p for p in preds
        if p.get("severity") == severity and p.get("latitude")
    ]
    # Group by district
    by_district: dict = {}
    for p in outbreaks:
        district = p.get("district", "Unknown")
        if district not in by_district:
            by_district[district] = []
        by_district[district].append(p)

    return {
        "total_outbreaks": len(outbreaks),
        "severity_filter": severity,
        "outbreaks": outbreaks[:100],
        "by_district": {k: len(v) for k, v in by_district.items()},
    }


@router.get("/reports")
async def list_all_reports(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, le=100),
    admin: dict = Depends(require_admin),
):
    """Return all reports generated on the platform."""
    all_reports = await _report_svc.list_all(limit=500)
    total = len(all_reports)
    start = (page - 1) * page_size
    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "reports": all_reports[start: start + page_size],
    }
