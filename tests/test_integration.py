"""
test_integration.py – Integration tests for system health and basic endpoints
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi.testclient import TestClient
from backend.main import app

client = TestClient(app)

def test_health_check():
    """Verify that the health check endpoint returns 200 and healthy status when DB is ok."""
    # We patch backend.main.db to simulate a healthy MongoDB connection
    with patch("backend.main.db") as mock_db:
        # Create a mock for client.admin.command
        mock_db.client = MagicMock()
        mock_db.client.admin = MagicMock()
        mock_db.client.admin.command = AsyncMock(return_value={"ok": 1})

        response = client.get("/api/health")
        assert response.status_code == 200
        assert response.json()["status"] == "healthy"
        assert response.json()["database"]["connected"] is True

def test_root_endpoint():
    """Verify that the root endpoint returns welcome message."""
    response = client.get("/")
    assert response.status_code == 200
    assert "CropPulse" in response.json()["platform"]

def test_docs_exist():
    """Verify OpenAPI documentation exists."""
    response = client.get("/api/openapi.json")
    assert response.status_code == 200
    assert "openapi" in response.json()


def test_dashboard_endpoint_payload_structure(client):
    """Verify /api/v1/history/dashboard returns all fields expected by frontend dashboard.js."""
    with patch("backend.routers.history.farm_repository") as mock_farm_repo, \
         patch("backend.routers.history.prediction_repository") as mock_pred_repo:

        mock_farm_repo.get_user_farms = AsyncMock(return_value=[
            {"farm_id": "farm-1", "name": "Green Valley", "last_severity": "healthy"}
        ])
        mock_pred_repo.list_disease_predictions_paginated = AsyncMock(return_value=([], 0))
        mock_pred_repo.list_soil_predictions_paginated = AsyncMock(return_value=([], 0))
        mock_pred_repo.get_analytics_summary = AsyncMock(return_value={"top_diseases": []})
        mock_pred_repo.get_severity_breakdown = AsyncMock(return_value={
            "healthy": 5, "mild": 2, "moderate": 1, "severe": 0, "uncertain": 1
        })
        mock_pred_repo.get_health_counts = AsyncMock(return_value={"healthy_count": 5, "diseased_count": 3})
        mock_pred_repo.get_soil_summary = AsyncMock(return_value={"average_soil_moisture": 32.5, "irrigation_needed_count": 2})
        mock_pred_repo.get_monthly_counts = AsyncMock(return_value=({"Mar 2026": 3}, {"Mar 2026": 2}))

        response = client.get("/api/v1/history/dashboard")
        assert response.status_code == 200
        data = response.json()

        # Core counts
        assert "total_farms" in data
        assert "healthy_farms" in data
        assert "total_predictions" in data
        # Newly added fields critical for dashboard.js and charts.js
        assert "severity_breakdown" in data
        assert data["severity_breakdown"]["healthy"] == 5
        assert "healthy_count" in data
        assert "diseased_count" in data
        assert "average_soil_moisture" in data
        assert data["average_soil_moisture"] == 32.5
        assert "irrigation_needed_count" in data
        assert data["irrigation_needed_count"] == 2
        assert "monthly_disease_counts" in data
        assert "monthly_soil_counts" in data

