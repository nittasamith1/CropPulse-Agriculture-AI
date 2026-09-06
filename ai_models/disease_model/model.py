"""
CropPulse – PyTorch Disease Model Architecture for Training
Re-exports the core architecture from backend.ai.disease.model.
"""

from backend.ai.disease.model import CropDiseaseEfficientNet, build_disease_model

__all__ = ["CropDiseaseEfficientNet", "build_disease_model"]
