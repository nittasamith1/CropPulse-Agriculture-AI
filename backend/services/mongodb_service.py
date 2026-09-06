"""
CropPulse – MongoDB Async Service
Exposes typed wrapper methods for MongoDB collection operations.
"""

from typing import Any, Dict, List, Optional
from loguru import logger
from backend.database import db
from backend.utils.helpers import utc_now

class MongoDBService:
    """
    Generic MongoDB Async CRUD Service.
    Integrates with Motor client.
    All operations are non-blocking.
    """

    def __init__(self, collection_name: str, id_field: str = "id"):
        self.collection_name = collection_name
        self.id_field = id_field

    @property
    def collection(self):
        """Return the Motor collection instance."""
        return db.db[self.collection_name]

    @staticmethod
    def _serialize_doc(doc: Dict[str, Any]) -> Dict[str, Any]:
        """Convert BSON ObjectIds to string IDs and format dates if needed."""
        if not doc:
            return doc
        doc = dict(doc)
        if "_id" in doc:
            doc["_id"] = str(doc["_id"])
        
        # Ensure any datetime object or customized types are handled if necessary
        # Motor already returns datetime objects, which Pydantic/FastAPI handles natively.
        return doc

    async def create(self, doc_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Create or overwrite a document."""
        data = dict(data)
        data[self.id_field] = doc_id
        # Use upsert to replicate set behavior
        await self.collection.replace_one(
            {self.id_field: doc_id},
            data,
            upsert=True
        )
        return data

    async def get(self, doc_id: str) -> Optional[Dict[str, Any]]:
        """Fetch a single document by ID field. Returns None if not found."""
        doc = await self.collection.find_one({self.id_field: doc_id})
        if doc:
            return self._serialize_doc(doc)
        return None

    async def update(self, doc_id: str, data: Dict[str, Any]) -> bool:
        """Update specific fields in a document."""
        data = dict(data)
        # Prevent changing ID
        data.pop(self.id_field, None)
        data.pop("_id", None)
        
        result = await self.collection.update_one(
            {self.id_field: doc_id},
            {"$set": data}
        )
        return result.modified_count > 0 or result.matched_count > 0

    async def delete(self, doc_id: str) -> bool:
        """Delete a document by ID field."""
        result = await self.collection.delete_one({self.id_field: doc_id})
        return result.deleted_count > 0

    async def list_all(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Return all documents in the collection (up to limit)."""
        cursor = self.collection.find().limit(limit)
        docs = await cursor.to_list(length=limit)
        return [self._serialize_doc(d) for d in docs]

    async def query(
        self,
        field: str,
        op: str,
        value: Any,
        order_by: Optional[str] = None,
        limit: int = 50,
        descending: bool = True,
    ) -> List[Dict[str, Any]]:
        """
        Simple single-field query.
        op: '==' | '<' | '<=' | '>' | '>=' | 'in' | 'array_contains'
        """
        mongo_op = {
            "==": "$eq",
            "<": "$lt",
            "<=": "$lte",
            ">": "$gt",
            ">=": "$gte",
            "in": "$in",
            "array_contains": "$elemMatch"  # simple array contains or equality
        }.get(op, "$eq")

        if op == "array_contains":
            query_filter = {field: value}  # In MongoDB, {field: val} automatically checks array elements
        elif op == "in" and not isinstance(value, list):
            query_filter = {field: {mongo_op: [value]}}
        else:
            query_filter = {field: {mongo_op: value}}

        cursor = self.collection.find(query_filter)

        if order_by:
            direction = -1 if descending else 1
            cursor = cursor.sort(order_by, direction)

        cursor = cursor.limit(limit)
        docs = await cursor.to_list(length=limit)
        return [self._serialize_doc(d) for d in docs]

    async def query_by_user(self, user_id: str, limit: int = 50, order_by: str = "created_at") -> List[Dict[str, Any]]:
        """Convenience: query all docs belonging to a specific user."""
        return await self.query("user_id", "==", user_id, order_by=order_by, limit=limit)

    async def count(self, field: Optional[str] = None, value: Any = None) -> int:
        """Count documents (optionally filtered)."""
        query_filter = {}
        if field and value is not None:
            query_filter = {field: value}
        return await self.collection.count_documents(query_filter)
