"""
CropPulse – Weather Schemas
Pydantic schemas for Open-Meteo current observations and forecasts.
"""

from typing import List, Optional
from pydantic import BaseModel, Field


class CurrentWeatherResponse(BaseModel):
    latitude: float
    longitude: float
    elevation: Optional[float] = None
    timezone: Optional[str] = "UTC"
    temperature: float = Field(..., description="Temperature in °C")
    humidity: float = Field(..., description="Relative humidity %")
    apparent_temperature: float
    precipitation: float = Field(default=0.0, description="Precipitation in mm")
    rain: float = Field(default=0.0, description="Rain in mm")
    cloud_cover: int = Field(default=0, description="Cloud cover %")
    pressure: float = Field(default=1013.25, description="Surface pressure in hPa")
    wind_speed: float = Field(default=10.0, description="Wind speed in km/h")
    wind_direction: int = Field(default=0, description="Wind direction degrees")
    weather_code: int
    condition: str
    time: Optional[str] = None
    cached: bool = False
    fallback: Optional[bool] = False


class ForecastDayItem(BaseModel):
    date: str
    temp_max: float
    temp_min: float
    precipitation_sum: float
    rain_probability: int
    weather_code: int
    condition: str
    max_wind_speed: float
    et0_evapotranspiration: Optional[float] = None


class WeatherForecastResponse(BaseModel):
    latitude: float
    longitude: float
    forecast_days: List[ForecastDayItem]
    next_24h_rain_probability: int
    next_24h_precipitation_mm: float
    cached: bool = False
