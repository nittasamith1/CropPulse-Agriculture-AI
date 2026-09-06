"""
tests/test_risk_service.py – Unit tests for CropRiskEngine and RiskService
Verifies multi-factor risk score calculation, boundary conditions, and contributing factors.
"""

import pytest
from unittest.mock import AsyncMock

from backend.ai.intelligence.risk_engine import CropRiskEngine
from backend.services.risk_service import RiskService


def test_crop_risk_engine_healthy_mild_weather():
    engine = CropRiskEngine()
    result = engine.evaluate_risk(
        disease_detected=False,
        disease_severity="none",
        disease_confidence=0.0,
        temperature=22.0,
        humidity=45.0,
        precipitation_mm=0.0,
        rain_probability_24h=5.0,
        forecast_precipitation_24h=0.0,
        soil_moisture=38.0,
    )

    assert result["risk_score"] < 30
    assert result["risk_level"] == "LOW"
    assert "breakdown" in result


def test_crop_risk_engine_severe_disease_and_high_humidity():
    engine = CropRiskEngine()
    result = engine.evaluate_risk(
        disease_detected=True,
        disease_severity="severe",
        disease_confidence=0.95,
        temperature=24.0,  # Favorable warm fungal range
        humidity=88.0,     # Very high humidity (>80%)
        precipitation_mm=12.0,
        rain_probability_24h=85.0,
        forecast_precipitation_24h=15.0,
        soil_moisture=55.0,
    )

    assert result["risk_score"] >= 70
    assert result["risk_level"] in ["HIGH", "CRITICAL"]
    assert len(result["factors"]) >= 2


def test_crop_risk_engine_score_bounds():
    engine = CropRiskEngine()
    # Test lower bound
    res_low = engine.evaluate_risk(
        disease_detected=False,
        temperature=15.0,
        humidity=30.0,
        soil_moisture=40.0,
    )
    assert 0 <= res_low["risk_score"] <= 100

    # Test upper bound
    res_high = engine.evaluate_risk(
        disease_detected=True,
        disease_severity="severe",
        disease_confidence=1.0,
        temperature=24.0,
        humidity=95.0,
        precipitation_mm=50.0,
        rain_probability_24h=100.0,
        forecast_precipitation_24h=50.0,
        soil_moisture=90.0,
    )
    assert 0 <= res_high["risk_score"] <= 100


@pytest.mark.asyncio
async def test_risk_service_assess_farm_risk():
    mock_weather = AsyncMock()
    mock_weather.get_current_weather.return_value = {
        "temperature": 26.0,
        "humidity": 78.0,
        "precipitation": 2.0,
        "condition": "Cloudy",
    }
    mock_weather.get_forecast.return_value = {
        "next_24h_rain_probability": 30.0,
        "next_24h_precipitation_mm": 1.5,
    }

    mock_farm_repo = AsyncMock()
    mock_farm_repo.get.return_value = {
        "farm_id": "farm-1",
        "name": "Green Valley Plot",
        "crop_types": ["Tomato"],
        "latitude": 17.5,
        "longitude": 78.5,
    }

    mock_pred_repo = AsyncMock()
    mock_pred_repo.list_disease_predictions_paginated.return_value = ([], 0)
    mock_pred_repo.list_soil_predictions_paginated.return_value = ([], 0)

    mock_weather_repo = AsyncMock()
    mock_weather_repo.save_risk_assessment.return_value = True

    service = RiskService(
        weather_svc=mock_weather,
        farm_repo=mock_farm_repo,
        pred_repo=mock_pred_repo,
        weather_repo=mock_weather_repo,
    )

    assessment = await service.assess_farm_risk(
        farm_id="farm-1",
        crop_type="Tomato",
        user_id="user-123",
    )

    assert assessment["farm_id"] == "farm-1"
    assert assessment["crop"] == "Tomato"
    assert "risk_score" in assessment
    assert "risk_level" in assessment
    mock_weather_repo.save_risk_assessment.assert_called_once()
