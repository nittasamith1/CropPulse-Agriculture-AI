"""
CropPulse – Base MongoDB Repository
Provides generic asynchronous CRUD operations, pagination, projections, and aggregation pipelines.
"""

from typing import Any, Dict, List, Optional, Tuple
from loguru import logger
import pymongo
from backend.database import db


class BaseRepository:
    """
    Abstract base repository wrapping Motor collection operations with pagination and projections.
    """

    def __init__(self, collection_name: str, id_field: str = "id"):
        self.collection_name = collection_name
        self.id_field = id_field

    @property
    def collection(self):
        """Return Motor collection instance."""
        return db.db[self.collection_name]

    @staticmethod
    def _serialize_doc(doc: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """Convert BSON ObjectIds to string IDs."""
        if not doc:
            return None
        doc = dict(doc)
        if "_id" in doc:
            doc["_id"] = str(doc["_id"])
        return doc

    async def create(self, doc_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Insert or replace document by primary ID."""
        data = dict(data)
        data[self.id_field] = doc_id
        await self.collection.replace_one(
            {self.id_field: doc_id},
            data,
            upsert=True,
        )
        return data

    async def get(self, doc_id: str, projection: Optional[Dict[str, int]] = None) -> Optional[Dict[str, Any]]:
        """Find a single document by its domain ID field."""
        doc = await self.collection.find_one({self.id_field: doc_id}, projection)
        return self._serialize_doc(doc)

    async def update(self, doc_id: str, update_dict: Dict[str, Any]) -> bool:
        """Update specific fields in a document."""
        data = dict(update_dict)
        data.pop(self.id_field, None)
        data.pop("_id", None)
        result = await self.collection.update_one(
            {self.id_field: doc_id},
            {"$set": data},
        )
        return result.modified_count > 0 or result.matched_count > 0

    async def delete(self, doc_id: str) -> bool:
        """Delete a document by domain ID."""
        result = await self.collection.delete_one({self.id_field: doc_id})
        return result.deleted_count > 0

    async def count(self, filter_query: Optional[Dict[str, Any]] = None) -> int:
        """Count documents matching criteria."""
        return await self.collection.count_documents(filter_query or {})

    async def list_paginated(
        self,
        filter_query: Optional[Dict[str, Any]] = None,
        page: int = 1,
        page_size: int = 20,
        sort_by: str = "created_at",
        descending: bool = True,
        projection: Optional[Dict[str, int]] = None,
    ) -> Tuple[List[Dict[str, Any]], int]:
        """
        Query documents with server-side pagination and projection.
        Returns: (items, total_count)
        """
        filter_query = filter_query or {}
        page = max(1, page)
        page_size = min(max(1, page_size), 100)
        skip = (page - 1) * page_size

        direction = pymongo.DESCENDING if descending else pymongo.ASCENDING

        total = await self.collection.count_documents(filter_query)
        cursor = (
            self.collection.find(filter_query, projection)
            .sort(sort_by, direction)
            .skip(skip)
            .limit(page_size)
        )

        docs = await cursor.to_list(length=page_size)
        items = [self._serialize_doc(d) for d in docs]
        return items, total

    async def aggregate(self, pipeline: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Run aggregation pipeline on collection."""
        cursor = self.collection.aggregate(pipeline)
        docs = await cursor.to_list(length=500)
        return [self._serialize_doc(d) for d in docs]
