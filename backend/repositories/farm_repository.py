"""
CropPulse – Farm Repository
Data access operations for farms, field boundaries, and geographical attributes.
"""

from typing import Optional, Dict, Any, List, Tuple
from backend.config import settings
from backend.repositories.base_repository import BaseRepository


class FarmRepository(BaseRepository):
    def __init__(self):
        super().__init__(collection_name=settings.COLLECTION_FARMS, id_field="farm_id")

    async def get_user_farms(self, user_id: str) -> List[Dict[str, Any]]:
        """List all farms belonging to a farmer."""
        cursor = self.collection.find({"user_id": user_id}).sort("created_at", -1)
        docs = await cursor.to_list(length=100)
        return [self._serialize_doc(d) for d in docs]

    async def list_markers(self, limit: int = 500) -> List[Dict[str, Any]]:
        """Fetch all farms with valid GPS coordinates for the GIS map."""
        cursor = self.collection.find(
            {"latitude": {"$ne": None}, "longitude": {"$ne": None}}
        ).limit(limit)
        docs = await cursor.to_list(length=limit)
        return [self._serialize_doc(d) for d in docs]


farm_repository = FarmRepository()
