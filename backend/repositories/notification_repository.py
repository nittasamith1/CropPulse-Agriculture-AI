"""
CropPulse – Notification Repository
Data access operations for system and agricultural alerts.
"""

from typing import Optional, Dict, Any, List, Tuple
from backend.config import settings
from backend.repositories.base_repository import BaseRepository


class NotificationRepository(BaseRepository):
    def __init__(self):
        super().__init__(collection_name=settings.COLLECTION_NOTIFICATIONS, id_field="notification_id")

    async def list_user_notifications(
        self,
        user_id: str,
        unread_only: bool = False,
        page: int = 1,
        page_size: int = 20,
    ) -> Tuple[List[Dict[str, Any]], int]:
        query: Dict[str, Any] = {"user_id": user_id}
        if unread_only:
            query["read"] = False

        return await self.list_paginated(
            filter_query=query, page=page, page_size=page_size, sort_by="created_at", descending=True
        )

    async def mark_as_read(self, notification_id: str, user_id: str) -> bool:
        result = await self.collection.update_one(
            {"notification_id": notification_id, "user_id": user_id},
            {"$set": {"read": True}},
        )
        return result.modified_count > 0

    async def mark_all_as_read(self, user_id: str) -> int:
        result = await self.collection.update_many(
            {"user_id": user_id, "read": False},
            {"$set": {"read": True}},
        )
        return result.modified_count


notification_repository = NotificationRepository()
