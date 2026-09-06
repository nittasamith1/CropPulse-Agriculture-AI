"""
CropPulse – Notifications Router
GET  /api/v1/notifications/          – List user notifications
POST /api/v1/notifications/{id}/read – Mark single notification as read
POST /api/v1/notifications/read-all  – Mark all as read
GET  /api/v1/notifications/unread-count – Unread badge count
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from loguru import logger

from backend.dependencies import get_current_user
from backend.services.notification_service import notification_service

router = APIRouter()


@router.get("/")
async def list_notifications(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    unread_only: bool = Query(default=False),
    current_user: dict = Depends(get_current_user),
):
    """Return paginated notifications for the current user."""
    uid = current_user["uid"]
    all_notifs = await notification_service.get_user_notifications(
        user_id=uid, limit=200, unread_only=unread_only
    )
    total = len(all_notifs)
    start = (page - 1) * page_size
    notifs = all_notifs[start: start + page_size]
    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "unread_count": await notification_service.get_unread_count(uid),
        "notifications": notifs,
    }


@router.get("/unread-count")
async def get_unread_count(current_user: dict = Depends(get_current_user)):
    """Return the count of unread notifications (for badge display)."""
    count = await notification_service.get_unread_count(current_user["uid"])
    return {"unread_count": count}


@router.post("/{notification_id}/read")
async def mark_read(
    notification_id: str,
    current_user: dict = Depends(get_current_user),
):
    """Mark a single notification as read."""
    success = await notification_service.mark_as_read(notification_id, current_user["uid"])
    if not success:
        raise HTTPException(status_code=404, detail="Notification not found or access denied.")
    return {"message": "Notification marked as read.", "success": True}


@router.post("/read-all")
async def mark_all_read(current_user: dict = Depends(get_current_user)):
    """Mark all notifications as read for the current user."""
    count = await notification_service.mark_all_read(current_user["uid"])
    return {"message": f"{count} notifications marked as read.", "updated_count": count}
