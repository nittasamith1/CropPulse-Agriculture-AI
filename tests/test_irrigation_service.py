"""
tests/test_irrigation_service.py – Unit tests for PrecisionIrrigationEngine and IrrigationService
Tests precision irrigation rules: rain imminent -> WAIT, over-capacity -> REDUCE, moisture deficit -> IRRIGATE.
"""

import pytest
from unittest.mock import AsyncMock

from backend.ai.intelligence.recommendation_engine import PrecisionIrrigationEngine
from backend.services.irrigation_service import IrrigationService


def test_irrigation_decision_imminent_heavy_rain():
    engine = PrecisionIrrigationEngine()
    result = engine.generate_recommendation(
        soil_moisture=20.0,
        temperature=28.0,
        humidity=60.0,
        rain_probability_24h=80.0,
        forecast_precipitation_24h=15.0,
        crop_type="Tomato",
        growth_stage="mid",
        soil_type="loamy",
    )

    assert result["action"] == "WAIT"
    assert result["water_amount_mm"] == 0.0
    assert "Rain expected" in result["reason"]


def test_irrigation_decision_soil_saturated():
    engine = PrecisionIrrigationEngine()
    # Loamy field capacity is ~35%, passing 42%
    result = engine.generate_recommendation(
        soil_moisture=42.0,
        temperature=25.0,
        humidity=65.0,
        rain_probability_24h=10.0,
        forecast_precipitation_24h=0.0,
        crop_type="Tomato",
        soil_type="loamy",
    )

    assert result["action"] == "REDUCE IRRIGATION"
    assert result["water_amount_mm"] == 0.0


def test_irrigation_decision_critical_deficit():
    engine = PrecisionIrrigationEngine()
    # Loamy field capacity ~35%, passing 12% moisture (far below 50% FC)
    result = engine.generate_recommendation(
        soil_moisture=12.0,
        temperature=30.0,
        humidity=50.0,
        rain_probability_24h=5.0,
        forecast_precipitation_24h=0.0,
        crop_type="Tomato",
        growth_stage="mid",
        soil_type="loamy",
    )

    assert result["action"] == "IRRIGATE"
    assert result["water_amount_mm"] > 0
    assert result["litres_per_hectare"] > 0
    assert result["priority"] in ["high", "urgent"]


def test_irrigation_decision_optimal_moisture():
    engine = PrecisionIrrigationEngine()
    result = engine.generate_recommendation(
        soil_moisture=30.0,
        temperature=26.0,
        humidity=55.0,
        rain_probability_24h=5.0,
        forecast_precipitation_24h=0.0,
        crop_type="Tomato",
        growth_stage="mid",
        soil_type="loamy",
    )

    assert result["action"] == "MONITOR"
    assert result["water_amount_mm"] == 0.0
    assert result["priority"] == "low"


@pytest.mark.asyncio
async def test_irrigation_service_get_recommendation():
    mock_weather = AsyncMock()
    mock_weather.get_current_weather.return_value = {
        "temperature": 27.0,
        "humidity": 62.0,
        "precipitation": 0.0,
    }
    mock_weather.get_forecast.return_value = {
        "next_24h_rain_probability": 10.0,
        "next_24h_precipitation_mm": 0.0,
    }

    mock_farm_repo = AsyncMock()
    mock_farm_repo.get.return_value = {
        "farm_id": "farm-42",
        "name": "Sunrise Orchard",
        "crop_types": ["Apple"],
        "soil_type": "loamy",
        "latitude": 31.1,
        "longitude": 77.1,
    }

    mock_pred_repo = AsyncMock()
    mock_pred_repo.list_soil_predictions_paginated.return_value = ([], 0)

    mock_weather_repo = AsyncMock()
    mock_weather_repo.save_irrigation_recommendation.return_value = True

    service = IrrigationService(
        weather_svc=mock_weather,
        farm_repo=mock_farm_repo,
        pred_repo=mock_pred_repo,
        weather_repo=mock_weather_repo,
    )

    rec = await service.get_farm_irrigation_recommendation(
        farm_id="farm-42",
        user_id="user-xyz",
    )

    assert rec["farm_id"] == "farm-42"
    assert rec["action"] in ["IRRIGATE", "WAIT", "REDUCE IRRIGATION", "MONITOR"]
    assert "litres_per_hectare" in rec
    mock_weather_repo.save_irrigation_recommendation.assert_called_once()


def test_water_balance_mathematical_invariants():
    """Verify FAO-56 water balance math invariants: TAW, RAW, depletion, and L/ha."""
    engine = PrecisionIrrigationEngine()
    result = engine.generate_recommendation(
        soil_moisture=15.0,
        temperature=32.0,
        humidity=40.0,
        crop_type="Tomato",
        growth_stage="mid",
        soil_type="loamy",
        et0_mm=4.5,
    )

    wb = result.get("water_balance")
    assert wb is not None
    assert wb["et0_source"] == "open_meteo"
    assert wb["et0_mm"] == 4.5
    # Loamy: FC=35%, WP=16%, RZD=600mm
    # TAW = (35 - 16) * 600 / 100 = 114 mm
    assert wb["taw_mm"] == 114.0
    # RAW = 114 * 0.5 = 57 mm
    assert wb["raw_mm"] == 57.0
    # 1 mm of water = 10,000 L / hectare
    assert result["litres_per_hectare"] == int(round(result["water_amount_mm"] * 10_000))

