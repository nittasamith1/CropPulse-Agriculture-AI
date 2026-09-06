"""
CropPulse – Pytest Shared Configuration & Fixtures
Provides FastAPI test client, mocked user dependencies, and mock database fixtures.
"""

import os
import sys

_ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT_DIR not in sys.path:
    sys.path.insert(0, _ROOT_DIR)

import pytest
from unittest.mock import AsyncMock, MagicMock
from fastapi.testclient import TestClient

from backend.main import app
from backend.dependencies import get_current_user


@pytest.fixture
def test_user():
    return {
        "uid": "test-farmer-001",
        "email": "farmer@croppulse.ai",
        "name": "Arjun Patel",
        "role": "farmer",
        "total_predictions": 12,
        "is_active": True,
    }


@pytest.fixture
def admin_user():
    return {
        "uid": "test-admin-001",
        "email": "admin@croppulse.ai",
        "name": "Platform Administrator",
        "role": "admin",
        "is_active": True,
    }


@pytest.fixture
def client(test_user):
    """
    FastAPI TestClient with authenticated farmer dependency override.
    """
    async def override_user():
        return test_user

    app.dependency_overrides[get_current_user] = override_user
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture
def admin_client(admin_user):
    """
    FastAPI TestClient with authenticated admin dependency override.
    """
    from backend.dependencies import require_admin
    async def override_admin():
        return admin_user

    app.dependency_overrides[get_current_user] = override_admin
    app.dependency_overrides[require_admin] = override_admin
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture
def unauthenticated_client():
    """
    FastAPI TestClient without dependency overrides to verify 401/403 security.
    """
    app.dependency_overrides.clear()
    with TestClient(app) as test_client:
        yield test_client
