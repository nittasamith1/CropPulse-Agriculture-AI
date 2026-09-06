"""
test_auth.py – Authentication and authorization test suite
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi.testclient import TestClient

from backend.main import app

client = TestClient(app)


# ── Fixtures ───────────────────────────────────────────────────────────────────

EXISTING_USER = {
    "uid": "existing-uid-001",
    "email": "existing@example.com",
    "name": "Existing Farmer",
    "hashed_password": "$2b$12$KIX/4SqdZeR5BFCNnPtOxeP6HYqD9M9cI1cMJIjTh1gV2gCnbcfBe",
    "role": "farmer",
    "is_active": True,
    "email_verified": True,
}


def _patch_register(user_exists=None):
    """Return a context manager stack that patches every async call in register."""
    return (
        patch("backend.routers.auth._user_svc"),
        patch("backend.routers.auth._reset_svc"),
        patch("backend.routers.auth.notification_service"),
        patch("backend.routers.auth.email_service"),
    )


# ── Test: POST /api/v1/auth/register ──────────────────────────────────────────

def test_register_success():
    """New user registration should return 201 and a message."""
    with patch("backend.routers.auth._user_svc") as mock_user_svc, \
         patch("backend.routers.auth._reset_svc") as mock_reset_svc, \
         patch("backend.routers.auth.notification_service") as mock_notif, \
         patch("backend.routers.auth.email_service") as mock_email:

        # Simulate: no existing account with this email
        mock_collection = MagicMock()
        mock_collection.find_one = AsyncMock(return_value=None)
        mock_user_svc.collection = mock_collection
        mock_user_svc.create = AsyncMock(return_value=True)

        mock_reset_svc.create = AsyncMock(return_value=True)
        mock_notif.system_notification = AsyncMock(return_value=None)
        mock_email.send_verification_email = AsyncMock(return_value=None)

        payload = {
            "email": "newfarmer@example.com",
            "password": "StrongPass123!",
            "name": "New Farmer",
            "role": "farmer",
            "phone": "+919876543210",
            "state": "Andhra Pradesh",
            "district": "Chittoor",
        }

        response = client.post("/api/v1/auth/register", json=payload)

        assert response.status_code == 201, response.text
        assert "message" in response.json()
        mock_user_svc.create.assert_called_once()


def test_register_duplicate_email():
    """Registering with an already-used email should return 409 Conflict."""
    with patch("backend.routers.auth._user_svc") as mock_user_svc:
        mock_collection = MagicMock()
        mock_collection.find_one = AsyncMock(return_value=EXISTING_USER)
        mock_user_svc.collection = mock_collection

        payload = {
            "email": "existing@example.com",
            "password": "StrongPass123!",
            "name": "Duplicate",
            "role": "farmer",
        }

        response = client.post("/api/v1/auth/register", json=payload)
        # Backend returns 409 Conflict for duplicate emails
        assert response.status_code == 409


# ── Test: POST /api/v1/auth/forgot-password ───────────────────────────────────

def test_forgot_password_known_email():
    """forgot-password with a known email should return 200 with a message."""
    with patch("backend.routers.auth._user_svc") as mock_user_svc, \
         patch("backend.routers.auth._reset_svc") as mock_reset_svc, \
         patch("backend.routers.auth.email_service") as mock_email:

        mock_collection = MagicMock()
        mock_collection.find_one = AsyncMock(return_value=EXISTING_USER)
        mock_user_svc.collection = mock_collection

        mock_reset_svc.create = AsyncMock(return_value=True)
        mock_email.send_password_reset_email = AsyncMock(return_value=None)

        response = client.post(
            "/api/v1/auth/forgot-password",
            json={"email": "existing@example.com"},
        )

        assert response.status_code == 200
        assert "message" in response.json()


def test_forgot_password_unknown_email():
    """forgot-password with unknown email should still return 200 (anti-enumeration)."""
    with patch("backend.routers.auth._user_svc") as mock_user_svc:
        mock_collection = MagicMock()
        mock_collection.find_one = AsyncMock(return_value=None)
        mock_user_svc.collection = mock_collection

        response = client.post(
            "/api/v1/auth/forgot-password",
            json={"email": "ghost@example.com"},
        )

        assert response.status_code == 200
        assert "message" in response.json()


# ── Test: GET /api/v1/auth/me (unauthenticated) ───────────────────────────────

def test_get_profile_unauthorized():
    """Accessing /me without a token should return 401."""
    response = client.get("/api/v1/auth/me")
    assert response.status_code == 401
