"""
CropPulse – Weather & Risk Repository
Data access operations for weather records, risk assessments, and irrigation recommendations.
"""

from typing import Optional, Dict, Any, List, Tuple
from datetime import datetime
from backend.config import settings
from backend.repositories.base_repository import BaseRepository


class WeatherRepository:
    def __init__(self):
        self.weather_repo = BaseRepository(
            collection_name=settings.COLLECTION_WEATHER_OBSERVATIONS,
            id_field="observation_id",
        )
        self.risk_repo = BaseRepository(
            collection_name=settings.COLLECTION_RISK_ASSESSMENTS,
            id_field="assessment_id",
        )
        self.irrigation_repo = BaseRepository(
            collection_name=settings.COLLECTION_IRRIGATION_RECOMMENDATIONS,
            id_field="recommendation_id",
        )

    async def save_observation(self, data: Dict[str, Any]) -> Dict[str, Any]:
        return await self.weather_repo.create(data["observation_id"], data)

    async def save_risk_assessment(self, data: Dict[str, Any]) -> Dict[str, Any]:
        return await self.risk_repo.create(data["assessment_id"], data)

    async def get_latest_risk(self, farm_id: str) -> Optional[Dict[str, Any]]:
        cursor = self.risk_repo.collection.find({"farm_id": farm_id}).sort("created_at", -1).limit(1)
        docs = await cursor.to_list(length=1)
        return self.risk_repo._serialize_doc(docs[0]) if docs else None

    async def save_irrigation_recommendation(self, data: Dict[str, Any]) -> Dict[str, Any]:
        return await self.irrigation_repo.create(data["recommendation_id"], data)

    async def get_latest_irrigation(self, farm_id: str) -> Optional[Dict[str, Any]]:
        cursor = self.irrigation_repo.collection.find({"farm_id": farm_id}).sort("created_at", -1).limit(1)
        docs = await cursor.to_list(length=1)
        return self.irrigation_repo._serialize_doc(docs[0]) if docs else None


weather_repository = WeatherRepository()
