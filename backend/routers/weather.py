"""
CropPulse – Weather Intelligence Router
GET /api/v1/weather/current   – Real-time weather observation from Open-Meteo
GET /api/v1/weather/forecast  – 7-day agricultural weather forecast
"""

from fastapi import APIRouter, Depends, Query, HTTPException, status
from slowapi import Limiter
from slowapi.util import get_remote_address

from backend.dependencies import get_current_user
from backend.services.weather_service import weather_service
from backend.models.weather import CurrentWeatherResponse, WeatherForecastResponse

router = APIRouter()
limiter = Limiter(key_func=get_remote_address)


@router.get("/current", response_model=CurrentWeatherResponse)
async def get_current_weather(
    lat: float = Query(..., ge=-90.0, le=90.0, description="Latitude coordinate"),
    lon: float = Query(..., ge=-180.0, le=180.0, description="Longitude coordinate"),
    current_user: dict = Depends(get_current_user),
):
    """
    Fetch real-time ambient weather conditions for a given farm coordinate.
    Uses Open-Meteo API with localized 30-minute caching.
    """
    try:
        data = await weather_service.get_current_weather(latitude=lat, longitude=lon)
        return data
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Weather service unavailable: {str(e)}",
        )


@router.get("/forecast", response_model=WeatherForecastResponse)
async def get_weather_forecast(
    lat: float = Query(..., ge=-90.0, le=90.0, description="Latitude coordinate"),
    lon: float = Query(..., ge=-180.0, le=180.0, description="Longitude coordinate"),
    days: int = Query(default=7, ge=1, le=14, description="Forecast horizon in days"),
    current_user: dict = Depends(get_current_user),
):
    """
    Fetch up to 14 days of agricultural weather forecast including rainfall probability and evapotranspiration.
    """
    try:
        data = await weather_service.get_forecast(latitude=lat, longitude=lon, days=days)
        return data
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Weather forecast service unavailable: {str(e)}",
        )
