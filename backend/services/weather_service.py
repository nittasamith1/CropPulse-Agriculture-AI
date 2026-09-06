"""
CropPulse – Weather Intelligence Service
Integrates Open-Meteo API for real-time observations, 7-day forecasts, and historical weather.
Includes localized coordinate caching to minimize external API overhead and latency.
"""

import time
from typing import Dict, Any, Optional
import httpx
from loguru import logger

from backend.config import settings

# Open-Meteo WMO Weather interpretation codes
WMO_WEATHER_CODES = {
    0: "Clear sky",
    1: "Mainly clear",
    2: "Partly cloudy",
    3: "Overcast",
    45: "Fog",
    48: "Depositing rime fog",
    51: "Light drizzle",
    53: "Moderate drizzle",
    55: "Dense drizzle",
    61: "Slight rain",
    63: "Moderate rain",
    65: "Heavy rain",
    71: "Slight snow fall",
    73: "Moderate snow fall",
    75: "Heavy snow fall",
    80: "Slight rain showers",
    81: "Moderate rain showers",
    82: "Violent rain showers",
    95: "Thunderstorm",
    96: "Thunderstorm with slight hail",
    99: "Thunderstorm with heavy hail",
}


class WeatherService:
    """
    Async weather intelligence client interfacing with Open-Meteo API.
    Provides response caching with TTL.
    """

    def __init__(self):
        self.base_url = settings.OPEN_METEO_BASE_URL.rstrip("/")
        self.cache_ttl = settings.WEATHER_CACHE_TTL_SECONDS
        self._cache: Dict[str, Dict[str, Any]] = {}

    def _cache_key(self, lat: float, lon: float, endpoint: str) -> str:
        """Round coordinates to 2 decimal places (~1.1 km resolution) for caching."""
        return f"{endpoint}:{round(lat, 2)}:{round(lon, 2)}"

    def _get_from_cache(self, key: str) -> Optional[Dict[str, Any]]:
        cached = self._cache.get(key)
        if cached:
            elapsed = time.time() - cached["timestamp"]
            if elapsed < self.cache_ttl:
                logger.debug(f"Weather cache hit for key: {key} (age: {int(elapsed)}s)")
                return cached["data"]
            else:
                del self._cache[key]
        return None

    def _save_to_cache(self, key: str, data: Dict[str, Any]):
        self._cache[key] = {
            "timestamp": time.time(),
            "data": data,
        }

    async def get_current_weather(self, latitude: float, longitude: float) -> Dict[str, Any]:
        """
        Fetch real-time ambient weather conditions.
        """
        cache_key = self._cache_key(latitude, longitude, "current")
        cached = self._get_from_cache(cache_key)
        if cached:
            return {**cached, "cached": True}

        url = f"{self.base_url}/forecast"
        params = {
            "latitude": latitude,
            "longitude": longitude,
            "current": [
                "temperature_2m",
                "relative_humidity_2m",
                "apparent_temperature",
                "precipitation",
                "rain",
                "weather_code",
                "cloud_cover",
                "surface_pressure",
                "wind_speed_10m",
                "wind_direction_10m",
            ],
            "timezone": "auto",
        }

        try:
            async with httpx.AsyncClient(timeout=8.0) as client:
                resp = await client.get(url, params=params)
                resp.raise_for_status()
                data = resp.json()

            current = data.get("current", {})
            wmo_code = current.get("weather_code", 0)

            result = {
                "latitude": latitude,
                "longitude": longitude,
                "elevation": data.get("elevation", 0),
                "timezone": data.get("timezone", "UTC"),
                "temperature": current.get("temperature_2m", 25.0),
                "humidity": current.get("relative_humidity_2m", 60.0),
                "apparent_temperature": current.get("apparent_temperature", 25.0),
                "precipitation": current.get("precipitation", 0.0),
                "rain": current.get("rain", 0.0),
                "cloud_cover": current.get("cloud_cover", 0),
                "pressure": current.get("surface_pressure", 1013.25),
                "wind_speed": current.get("wind_speed_10m", 10.0),
                "wind_direction": current.get("wind_direction_10m", 0),
                "weather_code": wmo_code,
                "condition": WMO_WEATHER_CODES.get(wmo_code, "Clear"),
                "time": current.get("time"),
            }

            self._save_to_cache(cache_key, result)
            return {**result, "cached": False}
        except Exception as e:
            logger.error(f"Failed to query Open-Meteo current weather: {e}")
            # If API fails, check if stale cache exists
            stale = self._cache.get(cache_key)
            if stale:
                logger.warning("Returning stale cached weather due to external API outage")
                return {**stale["data"], "cached": True, "stale": True}

            # Return fallback estimate
            return {
                "latitude": latitude,
                "longitude": longitude,
                "temperature": 25.0,
                "humidity": 65.0,
                "apparent_temperature": 25.0,
                "precipitation": 0.0,
                "rain": 0.0,
                "cloud_cover": 20,
                "pressure": 1013.2,
                "wind_speed": 10.0,
                "wind_direction": 180,
                "weather_code": 0,
                "condition": "Clear (Estimated)",
                "cached": False,
                "fallback": True,
            }

    async def get_forecast(self, latitude: float, longitude: float, days: int = 7) -> Dict[str, Any]:
        """
        Fetch daily and hourly weather forecasts for agricultural planning.
        """
        cache_key = self._cache_key(latitude, longitude, f"forecast_{days}")
        cached = self._get_from_cache(cache_key)
        if cached:
            return {**cached, "cached": True}

        url = f"{self.base_url}/forecast"
        params = {
            "latitude": latitude,
            "longitude": longitude,
            "daily": [
                "temperature_2m_max",
                "temperature_2m_min",
                "precipitation_sum",
                "precipitation_probability_max",
                "weather_code",
                "wind_speed_10m_max",
                "et0_fao_evapotranspiration",
            ],
            "forecast_days": min(max(1, days), 14),
            "timezone": "auto",
        }

        try:
            async with httpx.AsyncClient(timeout=8.0) as client:
                resp = await client.get(url, params=params)
                resp.raise_for_status()
                data = resp.json()

            daily = data.get("daily", {})
            time_series = daily.get("time", [])

            forecast_days = []
            for i, date_str in enumerate(time_series):
                def _get_val(key, default_val):
                    arr = daily.get(key, [])
                    return arr[i] if (isinstance(arr, list) and i < len(arr)) else default_val

                w_code = _get_val("weather_code", 0)
                forecast_days.append({
                    "date": date_str,
                    "temp_max": _get_val("temperature_2m_max", 28.0),
                    "temp_min": _get_val("temperature_2m_min", 18.0),
                    "precipitation_sum": _get_val("precipitation_sum", 0.0),
                    "rain_probability": _get_val("precipitation_probability_max", 0),
                    "weather_code": w_code,
                    "condition": WMO_WEATHER_CODES.get(w_code, "Clear"),
                    "max_wind_speed": _get_val("wind_speed_10m_max", 12.0),
                    "et0_evapotranspiration": _get_val("et0_fao_evapotranspiration", 3.5) if "et0_fao_evapotranspiration" in daily else None,
                })

            result = {
                "latitude": latitude,
                "longitude": longitude,
                "forecast_days": forecast_days,
                "next_24h_rain_probability": forecast_days[0]["rain_probability"] if forecast_days else 0,
                "next_24h_precipitation_mm": forecast_days[0]["precipitation_sum"] if forecast_days else 0.0,
                "next_24h_et0_mm": forecast_days[0].get("et0_evapotranspiration") if forecast_days else None,
            }

            self._save_to_cache(cache_key, result)
            return {**result, "cached": False}
        except Exception as e:
            logger.error(f"Failed to query Open-Meteo forecast: {e}")
            stale = self._cache.get(cache_key)
            if stale:
                return {**stale["data"], "cached": True, "stale": True}

            # Return empty forecast fallback
            return {
                "latitude": latitude,
                "longitude": longitude,
                "forecast_days": [],
                "next_24h_rain_probability": 10,
                "next_24h_precipitation_mm": 0.0,
                "next_24h_et0_mm": None,
                "fallback": True,
            }


weather_service = WeatherService()
