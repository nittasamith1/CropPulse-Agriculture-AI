"""
CropPulse – Authentication Service
Handles JWT tokens (Access and Refresh), password hashing (bcrypt), and verification.
"""

from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any
from jose import jwt, JWTError
from passlib.context import CryptContext
from loguru import logger
from backend.config import settings

# Passlib CryptContext using bcrypt for password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

class AuthService:
    """Manages password hashing and JWT token lifecycle."""

    @staticmethod
    def hash_password(password: str) -> str:
        """Hash plain text password with bcrypt."""
        return pwd_context.hash(password)

    @staticmethod
    def verify_password(plain_password: str, hashed_password: str) -> bool:
        """Verify plain text password against bcrypt hash."""
        try:
            return pwd_context.verify(plain_password, hashed_password)
        except Exception as e:
            logger.error(f"Password verification error: {e}")
            return False

    @staticmethod
    def create_access_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
        """Create JWT access token."""
        to_encode = data.copy()
        if expires_delta:
            expire = datetime.now(timezone.utc) + expires_delta
        else:
            expire = datetime.now(timezone.utc) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        
        to_encode.update({"exp": expire, "type": "access"})
        encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
        return encoded_jwt

    @staticmethod
    def create_refresh_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
        """Create JWT refresh token."""
        to_encode = data.copy()
        if expires_delta:
            expire = datetime.now(timezone.utc) + expires_delta
        else:
            expire = datetime.now(timezone.utc) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
        
        to_encode.update({"exp": expire, "type": "refresh"})
        encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
        return encoded_jwt

    @staticmethod
    def decode_token(token: str) -> Dict[str, Any]:
        """
        Decode a JWT token.
        Raises JWTError if expired, invalid, etc.
        """
        return jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])

    @staticmethod
    def verify_token(token: str, expected_type: str = "access") -> Optional[Dict[str, Any]]:
        """
        Verify and decode a token, returning the payload if valid.
        Returns None if invalid.
        """
        try:
            payload = AuthService.decode_token(token)
            if payload.get("type") != expected_type:
                logger.warning(f"Token type mismatch: expected {expected_type}, got {payload.get('type')}")
                return None
            return payload
        except JWTError as e:
            logger.warning(f"JWT Verification failed: {e} | Token prefix: {token[:15]}...")
            return None

