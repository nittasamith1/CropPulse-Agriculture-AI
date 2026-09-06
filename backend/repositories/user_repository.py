"""
CropPulse – User Repository
Data access operations for user profiles, credentials, and authentication tokens.
"""

from typing import Optional, Dict, Any, List
from datetime import datetime
from backend.config import settings
from backend.repositories.base_repository import BaseRepository
from backend.database import db


class UserRepository(BaseRepository):
    def __init__(self):
        super().__init__(collection_name=settings.COLLECTION_USERS, id_field="uid")

    async def get_by_email(self, email: str) -> Optional[Dict[str, Any]]:
        """Retrieve user by unique email address."""
        doc = await self.collection.find_one({"email": email.lower().strip()})
        return self._serialize_doc(doc)

    async def get_by_uid(self, uid: str) -> Optional[Dict[str, Any]]:
        """Retrieve user by UID."""
        return await self.get(uid)

    async def store_refresh_token(self, token: str, uid: str, expires_at: datetime) -> bool:
        """Store hashed or raw refresh token in MongoDB with TTL expiry."""
        await db.db[settings.COLLECTION_REFRESH_TOKENS].insert_one({
            "token": token,
            "uid": uid,
            "expires_at": expires_at,
            "created_at": datetime.utcnow(),
        })
        return True

    async def find_refresh_token(self, token: str) -> Optional[Dict[str, Any]]:
        """Look up refresh token."""
        doc = await db.db[settings.COLLECTION_REFRESH_TOKENS].find_one({"token": token})
        return self._serialize_doc(doc)

    async def revoke_refresh_token(self, token: str) -> bool:
        """Invalidate refresh token upon logout."""
        result = await db.db[settings.COLLECTION_REFRESH_TOKENS].delete_one({"token": token})
        return result.deleted_count > 0

    async def store_reset_token(self, token: str, email: str, expires_at: datetime) -> bool:
        """Store password reset token."""
        await db.db[settings.COLLECTION_RESET_TOKENS].insert_one({
            "token": token,
            "email": email.lower().strip(),
            "expires_at": expires_at,
            "created_at": datetime.utcnow(),
        })
        return True

    async def find_reset_token(self, token: str) -> Optional[Dict[str, Any]]:
        """Look up password reset token."""
        doc = await db.db[settings.COLLECTION_RESET_TOKENS].find_one({"token": token})
        return self._serialize_doc(doc)

    async def revoke_reset_token(self, token: str) -> bool:
        """Invalidate reset token after password update."""
        result = await db.db[settings.COLLECTION_RESET_TOKENS].delete_one({"token": token})
        return result.deleted_count > 0


user_repository = UserRepository()
