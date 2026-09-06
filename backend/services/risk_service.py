"""
CropPulse – Crop Risk Intelligence Service
Synthesizes disease symptoms, live weather, forecast conditions, and soil data to evaluate farm risk.
"""

from typing import Dict, Any, Optional
from loguru import logger

from backend.ai.intelligence.risk_engine import risk_engine
from backend.services.weather_service import weather_service
from backend.repositories.farm_repository import farm_repository
from backend.repositories.prediction_repository import prediction_repository
from backend.repositories.weather_repository import weather_repository
from backend.services.notification_service import notification_service
from backend.utils.helpers import generate_id, utc_now


class RiskService:
    def __init__(
        self,
        engine=risk_engine,
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

    async def assess_farm_risk(
        self,
        farm_id: Optional[str] = None,
        crop_type: Optional[str] = None,
        latitude: Optional[float] = None,
        longitude: Optional[float] = None,
        user_id: Optional[str] = None,
        temperature: Optional[float] = None,
        humidity: Optional[float] = None,
        rainfall_mm: Optional[float] = None,
        recent_disease_count: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Synthesize real-time weather, forecast, disease state, and soil moisture for comprehensive risk score.
        """
        # Resolve location
        lat = latitude or 17.3850
        lon = longitude or 78.4867
        crop = crop_type or "Tomato"
        farm_name = "Field Plot"

        if farm_id:
            farm = await self.farm_repo.get(farm_id)
            if farm:
                lat = farm.get("latitude") or lat
                lon = farm.get("longitude") or lon
                crop = (farm.get("crop_types") or [crop])[0]
                farm_name = farm.get("name", farm_name)

        # 1. Real-time Weather
        weather = await self.weather_svc.get_current_weather(lat, lon)
        forecast = await self.weather_svc.get_forecast(lat, lon, days=3)

        # 2. Latest Disease Prediction
        disease_detected = False
        disease_severity = "none"
        disease_confidence = 0.0

        if user_id:
            d_preds, _ = await self.pred_repo.list_disease_predictions_paginated(
                user_id=user_id, farm_id=farm_id, page=1, page_size=1
            )
            if d_preds:
                latest_d = d_preds[0]
                disease_detected = not latest_d.get("is_healthy", False)
                disease_severity = latest_d.get("severity", "none")
                disease_confidence = latest_d.get("confidence", 0.0)

        # 3. Latest Soil Moisture
        soil_moisture = 40.0
        if user_id:
            s_preds, _ = await self.pred_repo.list_soil_predictions_paginated(
                user_id=user_id, farm_id=farm_id, page=1, page_size=1
            )
            if s_preds:
                soil_moisture = s_preds[0].get("predicted_moisture", 40.0)

        # 4. Run Risk Engine
        effective_temp = temperature if temperature is not None else weather.get("temperature", 25.0)
        effective_humidity = humidity if humidity is not None else weather.get("humidity", 60.0)
        effective_precip = rainfall_mm if rainfall_mm is not None else weather.get("precipitation", 0.0)
        hist_count = recent_disease_count if recent_disease_count is not None else 0

        assessment = self.engine.evaluate_risk(
            disease_detected=disease_detected,
            disease_severity=disease_severity,
            disease_confidence=disease_confidence,
            temperature=effective_temp,
            humidity=effective_humidity,
            precipitation_mm=effective_precip,
            rain_probability_24h=forecast.get("next_24h_rain_probability", 10.0),
            forecast_precipitation_24h=forecast.get("next_24h_precipitation_mm", 0.0),
            soil_moisture=soil_moisture,
            crop_type=crop,
            historical_outbreaks_count=hist_count,
        )

        assessment_id = generate_id("risk")
        now = utc_now()

        doc = {
            "assessment_id": assessment_id,
            "farm_id": farm_id,
            "farm_name": farm_name,
            "user_id": user_id,
            "crop": crop,
            "latitude": lat,
            "longitude": lon,
            "risk_score": assessment["risk_score"],
            "risk_level": assessment["risk_level"],
            "factors": assessment["factors"],
            "breakdown": assessment["breakdown"],
            "disclaimer": assessment["disclaimer"],
            "weather_summary": {
                "temperature": weather.get("temperature"),
                "humidity": weather.get("humidity"),
                "condition": weather.get("condition"),
                "rain_probability_24h": forecast.get("next_24h_rain_probability"),
            },
            "created_at": now,
        }

        # 5. Persist assessment
        await self.weather_repo.save_risk_assessment(doc)

        # 6. Critical Alert if risk is high/critical
        if assessment["risk_score"] >= 75 and user_id:
            try:
                await notification_service.create_notification(
                    user_id=user_id,
                    title="⚠️ Elevated Disease Risk Alert",
                    message=f"High crop risk ({assessment['risk_score']}/100) on {farm_name}. High humidity and favorable temperature detected.",
                    type="risk_alert",
                    severity="high",
                    data={"farm_id": farm_id, "risk_score": assessment["risk_score"]},
                )
            except Exception as e:
                logger.warning(f"Could not emit risk notification: {e}")

        return doc


risk_service = RiskService()
