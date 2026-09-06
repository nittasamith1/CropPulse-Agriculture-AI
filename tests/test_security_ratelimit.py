"""
CropPulse – Security, Rate Limiting, and CORS Tests
Validates rate limiting, CORS configuration, response headers, and structured error responses.
"""

import pytest
from backend.config import settings


def test_cors_origins_configuration():
    """Verify CORS origins parsing and localhost/Vercel support."""
    from backend.config import get_settings
    get_settings.cache_clear()
    s = get_settings()
    origins = s.cors_origins
    assert isinstance(origins, list)
    assert any("localhost" in o for o in origins)
    assert any("crop-pulse-agriculture-ai.vercel.app" in o for o in origins)


def test_api_process_time_header(client):
    """Verify that every response contains the X-Process-Time-Ms timing header."""
    response = client.get("/api/health")
    assert response.status_code == 200
    assert "X-Process-Time-Ms" in response.headers


def test_structured_404_error_response(client):
    """Verify non-existent endpoints return standardized structured JSON."""
    response = client.get("/api/v1/nonexistent-route-endpoint")
    assert response.status_code == 404
    data = response.json()
    assert data["success"] is False
    assert "error" in data


def test_structured_422_validation_error_response(client):
    """Verify validation errors return structured 422 JSON payload."""
    response = client.post("/api/v1/soil/predict", json={"temperature": "invalid_string_not_float"})
    assert response.status_code == 422
    data = response.json()
    assert data["success"] is False
    assert "error" in data


def test_rate_limiting_registration_active():
    """Verify rate limiter is initialized on FastAPI app."""
    from backend.main import app
    assert hasattr(app.state, "limiter")
    assert app.state.limiter is not None
