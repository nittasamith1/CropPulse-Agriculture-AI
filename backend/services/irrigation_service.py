"""
CropPulse – Precision Irrigation Business Service
Evaluates multi-factor precision irrigation guidance and water requirement estimates.
"""

from typing import Dict, Any, Optional
from loguru import logger

from backend.ai.intelligence.recommendation_engine import precision_irrigation_engine
from backend.services.weather_service import weather_service
from backend.repositories.farm_repository import farm_repository
from backend.repositories.prediction_repository import prediction_repository
from backend.repositories.weather_repository import weather_repository
from backend.utils.helpers import generate_id, utc_now


class IrrigationService:
    def __init__(
        self,
        engine=precision_irrigation_engine,
        weather_svc=weather_service,
        farm_repo=farm_repository,
        pred_repo=prediction_repository,
        weather_repo=weather_repository,
    ):
        self.engine = engine
        self.weather_svc = weather_svc
        self.farm_repo = farm_repo
        self.pred_repo = pred_repo
        self.weather_repo = weather_repo

    async def get_farm_irrigation_recommendation(
        self,
        farm_id: Optional[str] = None,
        crop_type: Optional[str] = None,
        soil_type: Optional[str] = None,
        latitude: Optional[float] = None,
        longitude: Optional[float] = None,
        user_id: Optional[str] = None,
        growth_stage: str = "mid",
        soil_moisture: Optional[float] = None,
        temperature: Optional[float] = None,
        humidity: Optional[float] = None,
        rain_probability_24h: Optional[float] = None,
        forecast_precipitation_24h: Optional[float] = None,
    ) -> Dict[str, Any]:
        """
        Generate precision irrigation schedule for a specific field or plot.
        """
        lat = latitude or 17.3850
        lon = longitude or 78.4867
        crop = crop_type or "Tomato"
        s_type = soil_type or "loamy"
        farm_name = "Farm Plot"

        if farm_id:
            farm = await self.farm_repo.get(farm_id)
            if farm:
                lat = farm.get("latitude") or lat
                lon = farm.get("longitude") or lon
                crop = (farm.get("crop_types") or [crop])[0]
                s_type = farm.get("soil_type") or s_type
                farm_name = farm.get("name", farm_name)

        # 1. Fetch live weather & forecast
        weather = await self.weather_svc.get_current_weather(lat, lon)
        forecast = await self.weather_svc.get_forecast(lat, lon, days=2)

        # 2. Latest soil moisture observation
        moisture_val = soil_moisture
        if moisture_val is None:
            moisture_val = 38.0
            if user_id:
                s_preds, _ = await self.pred_repo.list_soil_predictions_paginated(
                    user_id=user_id, farm_id=farm_id, page=1, page_size=1
                )
                if s_preds:
                    moisture_val = s_preds[0].get("predicted_moisture", 38.0)

        # 3. Precision recommendation
        effective_temp = temperature if temperature is not None else weather.get("temperature", 25.0)
        effective_hum = humidity if humidity is not None else weather.get("humidity", 60.0)
        effective_rain_prob = rain_probability_24h if rain_probability_24h is not None else forecast.get("next_24h_rain_probability", 10.0)
        effective_precip_24h = forecast_precipitation_24h if forecast_precipitation_24h is not None else forecast.get("next_24h_precipitation_mm", 0.0)
        effective_et0 = forecast.get("next_24h_et0_mm")

        recommendation = self.engine.generate_recommendation(
            soil_moisture=moisture_val,
            temperature=effective_temp,
            humidity=effective_hum,
            rain_probability_24h=effective_rain_prob,
            forecast_precipitation_24h=effective_precip_24h,
            crop_type=crop,
            growth_stage=growth_stage,
            recent_rainfall_mm=weather.get("precipitation", 0.0),
            soil_type=s_type,
            et0_mm=effective_et0,
        )

        rec_id = generate_id("irrig")
        now = utc_now()

        doc = {
            "recommendation_id": rec_id,
            "farm_id": farm_id,
            "farm_name": farm_name,
            "user_id": user_id,
            "crop": crop,
            "growth_stage": growth_stage,
            "soil_type": s_type,
            "action": recommendation["action"],
            "decision_confidence": recommendation.get("decision_confidence", "HIGH"),
            "confidence": recommendation["confidence"],
            "reason": recommendation["reason"],
            "priority": recommendation["priority"],
            "water_amount_mm": recommendation["water_amount_mm"],
            "litres_per_hectare": recommendation["litres_per_hectare"],
            "recommended_method": recommendation["recommended_method"],
            "soil_moisture_level": moisture_val,
            "field_capacity_reference": recommendation["field_capacity_reference"],
            "water_balance": recommendation.get("water_balance"),
            "disclaimer": recommendation["disclaimer"],
            "weather_forecast_summary": {
                "rain_probability_24h": forecast.get("next_24h_rain_probability"),
                "precipitation_forecast_24h": forecast.get("next_24h_precipitation_mm"),
                "et0_evapotranspiration": effective_et0,
            },
            "created_at": now,
        }

        # 4. Save recommendation
        await self.weather_repo.save_irrigation_recommendation(doc)
        return doc


irrigation_service = IrrigationService()
