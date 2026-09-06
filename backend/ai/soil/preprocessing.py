"""
CropPulse – Soil Moisture Feature Preprocessing
Encodes environmental and soil features for tabular ML regression models.
"""

from typing import Dict, Any
import numpy as np


SOIL_TYPE_MAP = {
    "sandy": 0,
    "loamy": 1,
    "clay": 2,
    "silt": 3,
    "peaty": 4,
}

SOIL_WATER_RETENTION = {
    "sandy": 0.12,
    "loamy": 0.28,
    "clay": 0.42,
    "silt": 0.32,
    "peaty": 0.50,
}

SOIL_FIELD_CAPACITY = {
    "sandy": 20.0,
    "loamy": 35.0,
    "clay": 45.0,
    "silt": 38.0,
    "peaty": 55.0,
}


def encode_features(
    temperature: float,
    humidity: float,
    rainfall: float,
    wind_speed: float,
    soil_type: str,
    previous_moisture: float,
) -> np.ndarray:
    """
    Encode features into a tabular numerical vector suitable for ML regression:
    [temp_norm, humidity_norm, rainfall_norm, wind_norm, soil_type_idx_norm, prev_moisture_norm]
    """
    soil_idx = SOIL_TYPE_MAP.get(soil_type.lower().strip(), 1)
    
    features = np.array([
        temperature / 50.0,
        humidity / 100.0,
        min(rainfall, 200.0) / 200.0,
        min(wind_speed, 100.0) / 100.0,
        soil_idx / 4.0,
        previous_moisture / 100.0,
    ], dtype=np.float32).reshape(1, -1)

    return features
