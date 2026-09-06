"""
CropPulse – Authentication & Authorization Flows Tests
Validates JWT lifecycle, password hashing, login, refresh tokens, role-based access
control (farmer vs admin), and unauthorized endpoint protection.
"""

from datetime import timedelta
import pytest
from unittest.mock import AsyncMock, patch, MagicMock, PropertyMock
from backend.services.auth_service import AuthService
from backend.dependencies import require_admin


def test_password_hashing_and_verification():
    """Verify bcrypt password hashing and verification."""
    password = "SuperSecretPassword123!"
    hashed = AuthService.hash_password(password)

    assert hashed != password
    assert hashed.startswith("$2b$")
    assert AuthService.verify_password(password, hashed) is True
    assert AuthService.verify_password("WrongPassword", hashed) is False


def test_jwt_access_and_refresh_token_lifecycle():
    """Verify access and refresh token creation, type distinction, and decoding."""
    payload = {"uid": "user-123", "role": "farmer", "email": "test@crop.ai"}

    # Access token
    access_token = AuthService.create_access_token(payload)
    decoded_access = AuthService.verify_token(access_token, expected_type="access")
    assert decoded_access is not None
    assert decoded_access["uid"] == "user-123"
    assert decoded_access["type"] == "access"

    # Refresh token
    refresh_token = AuthService.create_refresh_token(payload)
    decoded_refresh = AuthService.verify_token(refresh_token, expected_type="refresh")
    assert decoded_refresh is not None
    assert decoded_refresh["type"] == "refresh"

    # Mismatched expected type must fail
    assert AuthService.verify_token(access_token, expected_type="refresh") is None
    assert AuthService.verify_token(refresh_token, expected_type="access") is None


def test_expired_token_rejected():
    """Expired tokens must be rejected."""
    payload = {"uid": "user-expired"}
    expired_token = AuthService.create_access_token(payload, expires_delta=timedelta(seconds=-10))
    assert AuthService.verify_token(expired_token, expected_type="access") is None


def test_admin_route_forbidden_for_regular_farmer(client):
    """Regular farmers must receive 403 Forbidden when attempting admin operations."""
    response = client.get("/api/v1/admin/analytics")
    assert response.status_code == 403
    assert "Admin privileges required" in str(response.json())


def test_admin_route_allowed_for_admin_user(admin_client):
    """Admin users must receive 200 OK when accessing admin endpoints."""
    with patch("backend.services.mongodb_service.MongoDBService.list_all", new_callable=AsyncMock) as mock_list:
        mock_list.return_value = []

        response = admin_client.get("/api/v1/admin/analytics")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, dict)
        assert "users" in data or "total_users" in data


def test_login_flow_invalid_credentials(unauthenticated_client):
    """Login with wrong password must return 401 Unauthorized."""
    from unittest.mock import PropertyMock
    from backend.services.mongodb_service import MongoDBService

    mock_col = MagicMock()
    mock_col.find_one = AsyncMock(return_value={
        "uid": "u1",
        "email": "user@test.com",
        "hashed_password": AuthService.hash_password("correct_pass"),
        "is_active": True,
    })
    with patch.object(MongoDBService, "collection", new_callable=PropertyMock) as mock_prop:
        mock_prop.return_value = mock_col
        res = unauthenticated_client.post(
            "/api/v1/auth/login",
            json={"email": "user@test.com", "password": "wrong_password"},
        )
        assert res.status_code == 401
