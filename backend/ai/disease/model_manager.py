"""
CropPulse – PyTorch Disease Model Manager
Thread-safe singleton lifecycle manager for the EfficientNet-B0 disease model.
Ensures the weights are loaded once at startup and reused across requests.
"""

import os
import threading
from typing import Optional, Dict, Any, List
from loguru import logger

try:
    import torch
    TORCH_AVAILABLE = True
except ImportError:
    torch = None
    TORCH_AVAILABLE = False

from backend.config import settings


# 38 PlantVillage disease classes in standard index order
DISEASE_CLASSES = [
    "Apple___Apple_scab",
    "Apple___Black_rot",
    "Apple___Cedar_apple_rust",
    "Apple___healthy",
    "Blueberry___healthy",
    "Cherry_(including_sour)___Powdery_mildew",
    "Cherry_(including_sour)___healthy",
    "Corn_(maize)___Cercospora_leaf_spot Gray_leaf_spot",
    "Corn_(maize)___Common_rust_",
    "Corn_(maize)___Northern_Leaf_Blight",
    "Corn_(maize)___healthy",
    "Grape___Black_rot",
    "Grape___Esca_(Black_Measles)",
    "Grape___Leaf_blight_(Isariopsis_Leaf_Spot)",
    "Grape___healthy",
    "Orange___Haunglongbing_(Citrus_greening)",
    "Peach___Bacterial_spot",
    "Peach___healthy",
    "Pepper,_bell___Bacterial_spot",
    "Pepper,_bell___healthy",
    "Potato___Early_blight",
    "Potato___Late_blight",
    "Potato___healthy",
    "Raspberry___healthy",
    "Soybean___healthy",
    "Squash___Powdery_mildew",
    "Strawberry___Leaf_scorch",
    "Strawberry___healthy",
    "Tomato___Bacterial_spot",
    "Tomato___Early_blight",
    "Tomato___Late_blight",
    "Tomato___Leaf_Mold",
    "Tomato___Septoria_leaf_spot",
    "Tomato___Spider_mites Two-spotted_spider_mite",
    "Tomato___Target_Spot",
    "Tomato___Tomato_Yellow_Leaf_Curl_Virus",
    "Tomato___Tomato_mosaic_virus",
    "Tomato___healthy",
]

DISEASE_CLASSES_DISPLAY = {
    cls: cls.replace("___", " – ").replace("_", " ") for cls in DISEASE_CLASSES
}


class DiseaseModelManager:
    """
    Singleton manager for loading, caching, and serving the PyTorch disease model.
    """

    _instance: Optional["DiseaseModelManager"] = None
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
        self.model = None
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu") if TORCH_AVAILABLE else "cpu"
        self.is_loaded = False
        self.model_path = settings.DISEASE_MODEL_PATH
        self.version = "1.0.0"
        self.architecture = "EfficientNet-B0"
        self.classes: List[str] = DISEASE_CLASSES

    def load_model(self) -> bool:
        """
        Load weights from disk into memory.
        Returns True if loaded, False if model file or runtime is not found.
        """
        if not TORCH_AVAILABLE:
            logger.warning("⚠️ PyTorch is not installed in the current environment. Status: MODEL_NOT_AVAILABLE.")
            self.is_loaded = False
            self.model = None
            return False

        if self.is_loaded and self.model is not None:
            return True

        with self._lock:
            if self.is_loaded and self.model is not None:
                return True

            logger.info(f"Checking for disease model at '{self.model_path}' on device '{self.device}'...")

            if not os.path.exists(self.model_path):
                logger.warning(
                    f"⚠️ Disease model weights file not found at '{self.model_path}'. "
                    "Status: MODEL_NOT_AVAILABLE. (Place trained .pth file to enable predictions)."
                )
                self.is_loaded = False
                self.model = None
                return False

            try:
                from backend.ai.disease.model import build_disease_model
                checkpoint = torch.load(self.model_path, map_location=self.device, weights_only=False)

                arch = "auto"
                if isinstance(checkpoint, dict):
                    arch = checkpoint.get("architecture", "auto")
                    state_dict = checkpoint.get("state_dict", checkpoint)
                else:
                    state_dict = checkpoint

                model = build_disease_model(
                    num_classes=len(self.classes),
                    architecture=arch,
                    state_dict=state_dict,
                )
                if any(k.startswith("backbone.") for k in state_dict.keys()):
                    model.load_state_dict(state_dict)
                elif hasattr(model, "backbone"):
                    try:
                        model.backbone.load_state_dict(state_dict)
                    except Exception:
                        prefixed = {f"backbone.{k}": v for k, v in state_dict.items()}
                        model.load_state_dict(prefixed)
                else:
                    model.load_state_dict(state_dict)
                model.to(self.device)
                model.eval()

                self.model = model
                self.is_loaded = True
                logger.success(f"✅ PyTorch Disease Model loaded successfully ({self.architecture}, device: {self.device})")
                return True
            except Exception as e:
                logger.error(f"❌ Failed to load PyTorch disease model: {e}")
                self.is_loaded = False
                self.model = None
                return False

    def get_model(self) -> Optional[Any]:
        """Return the active model instance or None."""
        if not self.is_loaded:
            self.load_model()
        return self.model

    def get_metadata(self) -> Dict[str, Any]:
        """Return model metadata and operational status."""
        return {
            "model": "crop_disease_efficientnet_b0",
            "architecture": self.architecture,
            "framework": "pytorch",
            "version": self.version,
            "device": str(self.device),
            "is_loaded": self.is_loaded,
            "classes_count": len(self.classes),
            "weights_path": self.model_path,
        }


# Module-level singleton
disease_model_manager = DiseaseModelManager()
