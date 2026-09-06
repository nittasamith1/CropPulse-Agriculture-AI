"""
test_soil_api.py – Soil moisture prediction tests with mocked SoilService
"""
import pytest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch
from fastapi.testclient import TestClient

from backend.main import app
from backend.dependencies import get_current_user

client = TestClient(app)

# ── Shared user override ───────────────────────────────────────────────────────

async def override_get_current_user():
    return {
        "uid": "test-user-123",
        "email": "farmer@example.com",
        "name": "Samith Nitta",
        "role": "farmer",
        "total_predictions": 0,
        "is_active": True,
    }


MOCK_SOIL_SERVICE_RESPONSE = {
    "prediction_id": "soil-test-123",
    "user_id": "test-user-123",
    "farm_id": None,
    "predicted_moisture": 32.5,
    "water_requirement_mm": 5.4,
    "irrigation_recommended": True,
    "irrigation_action": "IRRIGATE",
    "irrigation_reason": "Moisture deficit detected",
    "irrigation_type": "drip",
    "litres_per_hectare": 54000,
    "priority": "high",
    "recommendation_text": "Apply drip irrigation to replenish root zone.",
    "input_features": {"temperature": 24.5, "humidity": 60.0, "soil_type": "loamy"},
    "latitude": 13.5,
    "longitude": 79.2,
    "created_at": datetime.now(timezone.utc),
    "model_version": "XGBoost-v1",
}

VALID_SOIL_PAYLOAD = {
    "temperature": 24.5,
    "humidity": 60.0,
    "rainfall": 10.5,
    "wind_speed": 3.5,
    "soil_type": "loamy",
    "previous_moisture": 30.0,
    "farm_id": None,
    "latitude": 13.5,
    "longitude": 79.2,
}


# ── Test: POST /api/v1/soil/predict ──────────────────────────────────────────

def test_predict_soil_success():
    """Happy-path soil moisture prediction with mocked soil_service."""
    app.dependency_overrides[get_current_user] = override_get_current_user
    try:
        with patch("backend.routers.soil.soil_service.predict_soil_moisture", new_callable=AsyncMock) as mock_svc:
            mock_svc.return_value = MOCK_SOIL_SERVICE_RESPONSE

            response = client.post("/api/v1/soil/predict", json=VALID_SOIL_PAYLOAD)

            assert response.status_code == 201, response.text
            data = response.json()
            assert data["predicted_moisture"] == 32.5
            assert data["irrigation_recommended"] is True
            assert data["irrigation_action"] == "IRRIGATE"
            assert data["model_version"] == "XGBoost-v1"
    finally:
        app.dependency_overrides.clear()


def test_predict_soil_invalid_soil_type():
    """Passing an unsupported soil_type should return 400."""
    app.dependency_overrides[get_current_user] = override_get_current_user
    try:
        bad_payload = {**VALID_SOIL_PAYLOAD, "soil_type": "gravel"}
        response = client.post("/api/v1/soil/predict", json=bad_payload)
        assert response.status_code == 400
    finally:
        app.dependency_overrides.clear()


def test_predict_soil_unauthorized():
    """Calling predict without auth should return 401."""
    app.dependency_overrides.clear()
    response = client.post("/api/v1/soil/predict", json=VALID_SOIL_PAYLOAD)
    assert response.status_code in (401, 403)
