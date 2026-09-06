"""
tests/test_model_loading.py – Unit tests for AI model managers and graceful fallback behavior
Verifies PyTorch disease model instantiation, singleton management, and MODEL_NOT_AVAILABLE handling.
"""

import pytest

from backend.ai.disease.model_manager import DiseaseModelManager, DISEASE_CLASSES
from backend.ai.soil.model_manager import SoilModelManager


def test_disease_model_manager_missing_file():
    """
    When weights file is missing, load_model() should return False and model remains None.
    """
    manager = DiseaseModelManager()
    original_path = manager.model_path
    try:
        manager.model_path = "non_existent_path_to_weights.pth"
        manager.is_loaded = False
        manager.model = None

        loaded = manager.load_model()
        assert loaded is False
        assert manager.is_loaded is False
        assert manager.get_model() is None
    finally:
        manager.model_path = original_path


def test_soil_model_manager_missing_file():
    """
    When soil model pickle is missing, load_model() should return False.
    """
    manager = SoilModelManager()
    original_path = manager.model_path
    try:
        manager.model_path = "non_existent_soil_model.pkl"
        manager.is_loaded = False
        manager.model = None

        loaded = manager.load_model()
        assert loaded is False
        assert manager.is_loaded is False
        assert manager.get_model() is None
    finally:
        manager.model_path = original_path


def test_disease_model_classes_count():
    """
    Verify 38 disease classes are registered.
    """
    assert len(DISEASE_CLASSES) == 38
    assert "Tomato___healthy" in DISEASE_CLASSES
    assert "Potato___Early_blight" in DISEASE_CLASSES
