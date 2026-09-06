"""
CropPulse – AI-Powered Crop Intelligence Platform
Application Configuration.
Loads all settings from environment variables (.env file).
Uses pydantic-settings for type-safe config management.
MongoDB Atlas + PyTorch + Open-Meteo + JWT.
"""

import os
import sys
from functools import lru_cache
from typing import List

# Bootstrap sys.path so 'backend.*' imports succeed regardless of cwd
_CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
_PARENT_DIR = os.path.dirname(_CURRENT_DIR)
for _path in (_PARENT_DIR, _CURRENT_DIR):
    if _path not in sys.path:
        sys.path.insert(0, _path)

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """
    Application settings loaded from environment variables.
    All fields map directly to .env / .env.example keys.
    """

    # ── Application ──────────────────────────────────────────
    APP_NAME: str = "CropPulse"
    APP_ENV: str = "development"
    APP_PORT: int = 8000
    FRONTEND_URL: str = "https://crop-pulse-agriculture-ai.vercel.app"

    # ── Security ─────────────────────────────────────────────
    SECRET_KEY: str = "change-this-secret-key-in-production-use-64-chars"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    REFRESH_TOKEN_EXPIRE_DAYS: int = 30

    # ── MongoDB Atlas ─────────────────────────────────────────
    MONGODB_URI: str = "mongodb://localhost:27017"
    MONGODB_DB_NAME: str = "croppulse"

    # ── MongoDB Collection Names ──────────────────────────────
    COLLECTION_USERS: str = "users"
    COLLECTION_FARMS: str = "farms"
    COLLECTION_FIELDS: str = "fields"
    COLLECTION_DISEASE_PREDICTIONS: str = "disease_predictions"
    COLLECTION_SOIL_PREDICTIONS: str = "soil_predictions"
    COLLECTION_PREDICTIONS: str = "predictions"
    COLLECTION_WEATHER_OBSERVATIONS: str = "weather_observations"
    COLLECTION_RISK_ASSESSMENTS: str = "risk_assessments"
    COLLECTION_IRRIGATION_RECOMMENDATIONS: str = "irrigation_recommendations"
    COLLECTION_NOTIFICATIONS: str = "notifications"
    COLLECTION_REPORTS: str = "reports"
    COLLECTION_ANALYTICS: str = "analytics"
    COLLECTION_ACTIVITY_LOGS: str = "activity_logs"
    COLLECTION_ADMIN_LOGS: str = "admin_logs"
    COLLECTION_SETTINGS: str = "settings"
    COLLECTION_REFRESH_TOKENS: str = "refresh_tokens"
    COLLECTION_RESET_TOKENS: str = "reset_tokens"

    # ── SMTP Email ────────────────────────────────────────────
    SMTP_HOST: str = "smtp.gmail.com"
    SMTP_PORT: int = 587
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""
    FROM_EMAIL: str = "noreply@croppulse.app"
    FROM_NAME: str = "CropPulse"
    EMAIL_ENABLED: bool = False

    # ── AI Model Configurations ───────────────────────────────
    # PyTorch EfficientNet-B0 Disease Model (.pth)
    DISEASE_MODEL_PATH: str = "./ai_models/disease_model/disease_model.pth"
    # XGBoost / Scikit-Learn Tabular Soil Model (.pkl)
    SOIL_MODEL_PATH: str = "./ai_models/soil_model/soil_model.pkl"
    DISEASE_CLASSES_PATH: str = "./datasets/disease/disease_labels.csv"
    MODEL_CONFIDENCE_THRESHOLD: float = 0.65

    # ── Weather Intelligence (Open-Meteo) ─────────────────────
    OPEN_METEO_BASE_URL: str = "https://api.open-meteo.com/v1"
    WEATHER_CACHE_TTL_SECONDS: int = 1800  # 30-minute cache TTL

    # ── CORS ──────────────────────────────────────────────────
    ALLOWED_ORIGINS: str = (
        "http://localhost:3000,http://localhost:8000,http://localhost:8080,"
        "http://127.0.0.1:3000,http://127.0.0.1:8000,http://127.0.0.1:8080,"
        "https://crop-pulse-agriculture-ai.vercel.app,https://croppulse.vercel.app"
    )

    @property
    def cors_origins(self) -> List[str]:
        raw = self.ALLOWED_ORIGINS.strip()
        if raw == "*":
            return [
                "http://localhost:3000", "http://localhost:8000", "http://localhost:8080",
                "http://127.0.0.1:8080",
                "https://crop-pulse-agriculture-ai.vercel.app",
                "https://croppulse.vercel.app",
            ]
        origins = [o.strip() for o in raw.split(",") if o.strip() and o.strip() != "*"]
        return origins if origins else ["http://localhost:8080"]

    # ── Rate Limiting ─────────────────────────────────────────
    RATE_LIMIT_REQUESTS: int = 100
    RATE_LIMIT_WINDOW_SECONDS: int = 60

    # ── File Upload ───────────────────────────────────────────
    MAX_UPLOAD_SIZE_MB: int = 10
    ALLOWED_IMAGE_EXTENSIONS: str = "jpg,jpeg,png,webp"
    UPLOAD_TEMP_DIR: str = "./tmp/croppulse_uploads"

    @property
    def allowed_extensions(self) -> List[str]:
        return [e.strip().lower() for e in self.ALLOWED_IMAGE_EXTENSIONS.split(",")]

    @property
    def max_upload_bytes(self) -> int:
        return self.MAX_UPLOAD_SIZE_MB * 1024 * 1024

    # ── Logging ───────────────────────────────────────────────
    LOG_LEVEL: str = "INFO"
    LOG_FILE: str = "./logs/croppulse.log"

    model_config = {
        "env_file": (
            ".env",
            os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env"),
        ),
        "env_file_encoding": "utf-8",
        "case_sensitive": True,
        "extra": "ignore",
    }


@lru_cache()
def get_settings() -> Settings:
    """Return a cached Settings instance."""
    return Settings()


# Module-level singleton for direct imports
settings = get_settings()
