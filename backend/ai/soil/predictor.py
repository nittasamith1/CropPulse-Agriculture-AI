"""
CropPulse – Soil Moisture Predictor
Tabular ML inference for predicting soil moisture percentage.
"""

from typing import Dict, Any
from loguru import logger
import numpy as np

from backend.ai.soil.model_manager import soil_model_manager
from backend.ai.soil.preprocessing import (
    encode_features,
    SOIL_WATER_RETENTION,
    SOIL_FIELD_CAPACITY,
)


class SoilPredictionError(Exception):
    """Custom exception for soil prediction errors."""
    pass


class SoilModelNotAvailableError(SoilPredictionError):
    """Raised when the soil moisture model file is not available."""
    pass


class SoilPredictor:
    """
    Predicts soil moisture percentage from environmental and soil variables.
    """

    def __init__(self, manager=soil_model_manager):
        self.manager = manager

    def predict(
        self,
        temperature: float,
        humidity: float,
        rainfall: float,
        wind_speed: float,
        soil_type: str,
        previous_moisture: float,
    ) -> Dict[str, Any]:
        """
        Run inference on environmental inputs.
        """
        model = self.manager.get_model()
        if model is None:
            logger.warning("Soil moisture prediction requested but model is unavailable.")
            raise SoilModelNotAvailableError(
                "Soil moisture ML model is not available. Please run the training pipeline to generate soil_model.pkl."
            )

        features = encode_features(
            temperature=temperature,
            humidity=humidity,
            rainfall=rainfall,
            wind_speed=wind_speed,
            soil_type=soil_type,
            previous_moisture=previous_moisture,
        )

        try:
            raw_prediction = float(model.predict(features)[0])
        except Exception as e:
            logger.error(f"Soil model prediction failed: {e}")
            raise SoilPredictionError(f"Inference execution failed: {e}")

        # Constrain moisture between 5% and 100%
        predicted_moisture = round(float(np.clip(raw_prediction, 5.0, 100.0)), 2)

        # Agronomic metrics
        s_type = soil_type.lower().strip()
        field_capacity = SOIL_FIELD_CAPACITY.get(s_type, 35.0)
        water_retention = SOIL_WATER_RETENTION.get(s_type, 0.28)

        # Deficit mm calculation
        deficit_percent = max(0.0, field_capacity - predicted_moisture)
        water_requirement_mm = round(deficit_percent * water_retention * 10.0, 2)
        irrigation_recommended = predicted_moisture < (field_capacity * 0.65)

        return {
            "predicted_moisture": predicted_moisture,
            "field_capacity": field_capacity,
            "water_requirement_mm": water_requirement_mm,
            "irrigation_recommended": irrigation_recommended,
            "model_version": self.manager.version,
            "algorithm": self.manager.algorithm,
        }


soil_predictor = SoilPredictor()
