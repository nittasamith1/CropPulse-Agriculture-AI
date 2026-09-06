"""
CropPulse – Auth Middleware
Provides JWT token verification as middleware and utility functions
for extracting user context from requests.
"""

from fastapi import Request, HTTPException, status
from starlette.middleware.base import BaseHTTPMiddleware
from loguru import logger
from backend.services.auth_service import AuthService

# Routes that do NOT require authentication
PUBLIC_ROUTES = {
    "/",
    "/api/health",
    "/api/docs",
    "/api/redoc",
    "/api/openapi.json",
    "/api/v1/auth/register",
    "/api/v1/auth/login",
    "/api/v1/auth/forgot-password",
    "/api/v1/auth/verify-email",
}


class JWTAuthMiddleware(BaseHTTPMiddleware):
    """
    Optional middleware that attaches the decoded JWT token payload
    to request.state.user for downstream use.
    This does NOT enforce auth — use Depends(get_current_user) for that.
    """

    async def dispatch(self, request: Request, call_next):
        request.state.user = None
        auth_header = request.headers.get("Authorization", "")

        token = auth_header.strip()
        if token.lower().startswith("bearer "):
            token = token[7:].strip()
            
        if token:
            try:
                # Clean quotes if present
                token = token.strip('"').strip("'")
                decoded = AuthService.verify_token(token, expected_type="access")
                request.state.user = decoded
            except Exception as e:
                logger.debug(f"Token pre-verification failed (non-critical): {e}")

        response = await call_next(request)
        return response


def extract_uid_from_request(request: Request) -> str:
    """
    Extract the User UID from the request state set by middleware.
    Raises 401 if not authenticated.
    """
    user = getattr(request.state, "user", None)
    if not user or not user.get("uid"):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required.",
        )
    return user["uid"]
