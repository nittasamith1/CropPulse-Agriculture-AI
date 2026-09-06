"""
tests/test_weather_service.py – Unit tests for Open-Meteo WeatherService
Verifies real-time weather fetching, in-memory caching, forecast structures, and WMO code mapping.
"""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock

from backend.services.weather_service import WeatherService


@pytest.mark.asyncio
async def test_weather_service_current_weather():
    mock_open_meteo_resp = {
        "current": {
            "time": "2026-09-05T12:00",
            "temperature_2m": 28.5,
            "relative_humidity_2m": 72.0,
            "apparent_temperature": 31.0,
            "precipitation": 0.2,
            "weather_code": 2,
            "surface_pressure": 1012.3,
            "wind_speed_10m": 14.5,
            "wind_direction_10m": 180,
        }
    }

    mock_client = AsyncMock()
    mock_resp = MagicMock()
    mock_resp.raise_for_status = MagicMock()
    mock_resp.json.return_value = mock_open_meteo_resp
    mock_client.get.return_value = mock_resp
    mock_client.__aenter__.return_value = mock_client
    mock_client.__aexit__.return_value = None

    service = WeatherService()
    service._cache.clear()

    with patch("httpx.AsyncClient", return_value=mock_client):
        result = await service.get_current_weather(latitude=17.3850, longitude=78.4867)

    assert result["temperature"] == 28.5
    assert result["humidity"] == 72.0
    assert result["precipitation"] == 0.2
    assert result["condition"] == "Partly cloudy"
    assert result["wind_speed"] == 14.5

    # Check that in-memory cache was populated
    key = service._cache_key(17.3850, 78.4867, "current")
    cached = service._get_from_cache(key)
    assert cached is not None
    assert cached["temperature"] == 28.5


@pytest.mark.asyncio
async def test_weather_service_cache_hit():
    service = WeatherService()
    key = service._cache_key(17.3850, 78.4867, "current")
    service._save_to_cache(key, {
        "latitude": 17.39,
        "longitude": 78.49,
        "temperature": 27.0,
        "humidity": 65.0,
        "condition": "Clear sky",
    })

    # Calling without mocking httpx - since it's cached, no network call should be made
    result = await service.get_current_weather(latitude=17.3850, longitude=78.4867)

    assert result["temperature"] == 27.0
    assert result["humidity"] == 65.0
    assert result["condition"] == "Clear sky"


@pytest.mark.asyncio
async def test_weather_service_forecast_structure():
    mock_forecast_resp = {
        "daily": {
            "time": ["2026-09-05", "2026-09-06", "2026-09-07"],
            "temperature_2m_max": [32.0, 31.5, 30.0],
            "temperature_2m_min": [22.0, 21.0, 20.5],
            "precipitation_sum": [0.0, 5.2, 12.4],
            "precipitation_probability_max": [10, 45, 80],
            "weather_code": [0, 2, 61],
            "wind_speed_10m_max": [15.0, 18.0, 12.0],
            "et0_fao_evapotranspiration": [4.2, 3.8, 3.1],
        }
    }

    mock_client = AsyncMock()
    mock_resp = MagicMock()
    mock_resp.raise_for_status = MagicMock()
    mock_resp.json.return_value = mock_forecast_resp
    mock_client.get.return_value = mock_resp
    mock_client.__aenter__.return_value = mock_client
    mock_client.__aexit__.return_value = None

    service = WeatherService()
    service._cache.clear()

    with patch("httpx.AsyncClient", return_value=mock_client):
        forecast = await service.get_forecast(latitude=17.3850, longitude=78.4867, days=3)

    assert len(forecast["forecast_days"]) == 3
    assert forecast["forecast_days"][0]["date"] == "2026-09-05"
    assert forecast["forecast_days"][0]["temp_max"] == 32.0
    assert forecast["next_24h_precipitation_mm"] == 0.0
    assert forecast["next_24h_rain_probability"] == 10
