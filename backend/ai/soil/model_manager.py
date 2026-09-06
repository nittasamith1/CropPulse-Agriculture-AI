"""
CropPulse – Soil Model Manager
Thread-safe singleton manager for loading the tabular soil moisture prediction model.
"""

import os
import threading
from typing import Optional, Dict, Any
import joblib
from loguru import logger

from backend.config import settings


class SoilModelManager:
    """
    Singleton manager for loading, caching, and serving the Tabular ML Soil Model (XGBoost/RF).
    """

    _instance: Optional["SoilModelManager"] = None
    _lock = threading.Lock()

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if getattr(self, "_initialized", False):
            return
        self._initialized = True
        self.model: Optional[Any] = None
        self.is_loaded = False
        self.model_path = settings.SOIL_MODEL_PATH
        self.algorithm = "XGBoost Regressor / Random Forest"
        self.version = "1.0.0"

    def load_model(self) -> bool:
        """Load trained pipeline (.pkl) from disk."""
        if self.is_loaded and self.model is not None:
            return True

        with self._lock:
            if self.is_loaded and self.model is not None:
                return True

            logger.info(f"Checking for soil model at '{self.model_path}'...")
            if not os.path.exists(self.model_path):
                logger.warning(
                    f"⚠️ Soil moisture model file not found at '{self.model_path}'. "
                    "Status: MODEL_NOT_AVAILABLE. (Run training pipeline to generate soil_model.pkl)."
                )
                self.is_loaded = False
                self.model = None
                return False

            try:
                self.model = joblib.load(self.model_path)
                self.is_loaded = True
                logger.success(f"✅ Soil moisture model loaded from {self.model_path}")
                return True
            except Exception as e:
                logger.error(f"❌ Failed to load soil model from {self.model_path}: {e}")
                self.is_loaded = False
                self.model = None
                return False

    def get_model(self) -> Optional[Any]:
        if not self.is_loaded:
            self.load_model()
        return self.model

    def get_metadata(self) -> Dict[str, Any]:
        return {
            "model": "soil_moisture_regressor",
            "algorithm": self.algorithm,
            "version": self.version,
            "is_loaded": self.is_loaded,
            "weights_path": self.model_path,
        }


soil_model_manager = SoilModelManager()
