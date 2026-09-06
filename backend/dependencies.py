"""
CropPulse – Shared FastAPI Dependencies
Provides reusable dependency-injected services:
  - JWT token verification and decoding
  - Current user retrieval (MongoDB)
  - Admin role guard
  - Database client connection
"""

from typing import Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from loguru import logger

from backend.config import settings
from backend.database import get_database
from backend.services.auth_service import AuthService
from backend.services.mongodb_service import MongoDBService

from fastapi.security import APIKeyHeader
import re

# APIKeyHeader security scheme (shows Authorize button in Swagger where user enters "Bearer <token>")
api_key_scheme = APIKeyHeader(name="Authorization", auto_error=False)

# MongoDB users helper
_user_svc = MongoDBService(settings.COLLECTION_USERS, id_field="uid")

async def verify_jwt_token(
    auth_header: Optional[str] = Depends(api_key_scheme),
) -> dict:
    """
    Verify and decode a JWT Access Token from the Authorization header.
    Supports standard Bearer prefix, duplicate Bearer (Swagger), quotes, and raw tokens.
    Returns the decoded token payload.
    """
    if not auth_header:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authorization header missing. Please include 'Bearer <token>'.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # 1. Clean whitespace
    token = auth_header.strip()

    # 2. Handle double Bearer if user typed "Bearer <token>" in Swagger's Bearer input
    if token.lower().startswith("bearer "):
        token = token[7:].strip()
    if token.lower().startswith("bearer "):
        token = token[7:].strip()

    # 3. Clean quotes if wrapped (e.g. stringified JSON or double-quotes from frontend storage)
    token = token.strip('"').strip("'")

    # 4. Handle JSON-like formats e.g. {"access_token": "..."} or "access_token": "..."
    if "access_token" in token:
        match = re.search(r'"access_token"\s*:\s*"([^"]+)"', token)
        if match:
            token = match.group(1)

    # 5. Verify the token type and payload
    payload = AuthService.verify_token(token, expected_type="access")
    
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired access token. Please log in again.",
            headers={"WWW-Authenticate": "Bearer"},
        )
        
    return payload


async def get_current_user(
    token_data: dict = Depends(verify_jwt_token),
) -> dict:
    """
    Returns the verified token payload enriched with the MongoDB user profile.
    Exposes: uid, email, name, role, farm_ids, is_active, etc.
    """
    uid = token_data.get("uid")
    if not uid:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, 
            detail="UID not found in authentication token."
        )

    user_data = await _user_svc.get(uid)
    if not user_data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User account not found."
        )

    if not user_data.get("is_active", True):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account has been deactivated."
        )

    return user_data

async def require_admin(
    current_user: dict = Depends(get_current_user),
) -> dict:
    """
    Guards admin-only routes. Raises 403 Forbidden if user is not an admin.
    """
    if current_user.get("role") != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin privileges required to access this resource.",
        )
    return current_user

def get_db():
    """Dependency yielding the active MongoDB database client instance."""
    return get_database()
