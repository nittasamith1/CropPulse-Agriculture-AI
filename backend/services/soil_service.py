"""
CropPulse – Soil Moisture Business Service
Orchestrates soil moisture regression, precision irrigation logic, and history persistence.
"""

from typing import Dict, Any, Optional
from loguru import logger

from backend.ai.soil.predictor import soil_predictor, SoilModelNotAvailableError
from backend.ai.intelligence.recommendation_engine import precision_irrigation_engine
from backend.repositories.prediction_repository import prediction_repository
from backend.repositories.farm_repository import farm_repository
from backend.services.notification_service import notification_service
from backend.utils.helpers import generate_id, utc_now


class SoilService:
    def __init__(self, predictor=soil_predictor, pred_repo=prediction_repository, farm_repo=farm_repository):
        self.predictor = predictor
        self.pred_repo = pred_repo
        self.farm_repo = farm_repo

    async def predict_soil_moisture(
        self,
        temperature: float,
        humidity: float,
        rainfall: float,
        wind_speed: float,
        soil_type: str,
        previous_moisture: float,
        user_id: str,
        farm_id: Optional[str] = None,
        crop_type: Optional[str] = None,
        latitude: Optional[float] = None,
        longitude: Optional[float] = None,
    ) -> Dict[str, Any]:
        """
        Execute soil prediction and precision irrigation evaluation.
        """
        # 1. Run Tabular ML Model
        soil_result = self.predictor.predict(
            temperature=temperature,
            humidity=humidity,
            rainfall=rainfall,
            wind_speed=wind_speed,
            soil_type=soil_type,
            previous_moisture=previous_moisture,
        )

        predicted_moisture = soil_result["predicted_moisture"]

        # 2. Precision Irrigation Analysis
        irrigation_advice = precision_irrigation_engine.generate_recommendation(
            soil_moisture=predicted_moisture,
            temperature=temperature,
            humidity=humidity,
            rain_probability_24h=10.0 if rainfall < 5.0 else 60.0,
            forecast_precipitation_24h=rainfall,
            crop_type=crop_type,
            soil_type=soil_type,
        )

        # 3. Location linking
        farm_lat, farm_lon, district, state = latitude, longitude, None, None
        if farm_id:
            farm_doc = await self.farm_repo.get(farm_id)
            if farm_doc:
                farm_lat = farm_lat or farm_doc.get("latitude")
                farm_lon = farm_lon or farm_doc.get("longitude")
                district = farm_doc.get("district")
                state = farm_doc.get("state")

        prediction_id = generate_id("spred")
        now = utc_now()

        record = {
            "prediction_id": prediction_id,
            "user_id": user_id,
            "farm_id": farm_id,
            "predicted_moisture": predicted_moisture,
            "water_requirement_mm": soil_result["water_requirement_mm"],
            "irrigation_recommended": irrigation_advice["action"] in ["IRRIGATE", "REDUCE_IRRIGATION", "REDUCE IRRIGATION"],
            "irrigation_action": irrigation_advice["action"],
            "irrigation_reason": irrigation_advice["reason"],
            "irrigation_type": irrigation_advice["recommended_method"],
            "litres_per_hectare": irrigation_advice["litres_per_hectare"],
            "priority": irrigation_advice["priority"],
            "recommendation_text": irrigation_advice["reason"],
            "input_features": {
                "temperature": temperature,
                "humidity": humidity,
                "rainfall": rainfall,
                "wind_speed": wind_speed,
                "soil_type": soil_type,
                "previous_moisture": previous_moisture,
            },
            "latitude": farm_lat,
            "longitude": farm_lon,
            "district": district,
            "state": state,
            "model_version": soil_result.get("model_version", "1.0.0"),
            "disclaimer": irrigation_advice["disclaimer"],
            "created_at": now,
        }

        # 4. Save to Database
        await self.pred_repo.save_soil_prediction(record)

        # 5. Low Moisture Alert
        if predicted_moisture < 25.0:
            try:
                await notification_service.soil_moisture_alert(
                    user_id=user_id,
                    moisture_level=predicted_moisture,
                    farm_name=farm_id or "Farm",
                    prediction_id=prediction_id,
                )
            except Exception as e:
                logger.warning(f"Failed to trigger soil alert: {e}")

        # Update farm record
        if farm_id:
            await self.farm_repo.update(farm_id, {
                "last_moisture": predicted_moisture,
                "last_soil_date": now,
            })

        return record


soil_service = SoilService()
