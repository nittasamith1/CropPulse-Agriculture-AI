"""
CropPulse – Real Soil AI Pipeline Tests
Validates XGBoost / Scikit-Learn soil moisture inference, feature preprocessing,
bounds checking, agricultural deficit calculation, and missing-model handling.
"""

import os
import pytest
from fastapi import HTTPException

from backend.ai.soil.model_manager import soil_model_manager
from backend.ai.soil.predictor import soil_predictor, SoilModelNotAvailableError, SoilPredictor
from backend.utils.validators import validate_soil_prediction_input


def test_soil_model_file_exists():
    """Verify that the soil model artifact exists on disk."""
    assert os.path.exists("ai_models/soil_model/soil_model.pkl"), (
        "ai_models/soil_model/soil_model.pkl must exist for production inference."
    )


def test_soil_model_loading():
    """Verify soil model loading and metadata."""
    loaded = soil_model_manager.load_model()
    assert loaded is True
    assert soil_model_manager.is_loaded is True

    meta = soil_model_manager.get_metadata()
    assert "XGBoost" in meta["algorithm"]
    assert meta["is_loaded"] is True


def test_real_soil_prediction_values():
    """Verify soil prediction output structure and realistic value ranges."""
    res = soil_predictor.predict(
        temperature=30.0,
        humidity=60.0,
        rainfall=5.0,
        wind_speed=10.0,
        soil_type="clay",
        previous_moisture=25.0,
    )
    assert "predicted_moisture" in res
    assert 5.0 <= res["predicted_moisture"] <= 100.0
    assert "field_capacity" in res
    assert "water_requirement_mm" in res
    assert isinstance(res["irrigation_recommended"], bool)


def test_soil_input_validation_out_of_bounds():
    """Verify out-of-bounds soil input parameters raise HTTPException."""
    # Invalid temperature > 60
    with pytest.raises(HTTPException) as exc1:
        validate_soil_prediction_input(temperature=85.0, humidity=50.0, rainfall=10.0)
    assert exc1.value.status_code == 422

    # Invalid humidity < 0
    with pytest.raises(HTTPException) as exc2:
        validate_soil_prediction_input(temperature=25.0, humidity=-10.0, rainfall=10.0)
    assert exc2.value.status_code == 422

    # Invalid rainfall < 0
    with pytest.raises(HTTPException) as exc3:
        validate_soil_prediction_input(temperature=25.0, humidity=50.0, rainfall=-5.0)
    assert exc3.value.status_code == 422


def test_missing_soil_model_fails_safely():
    """SoilPredictor raises SoilModelNotAvailableError when model is absent."""
    class FakeEmptyManager:
        def get_model(self):
            return None

    unavail = SoilPredictor(manager=FakeEmptyManager())
    with pytest.raises(SoilModelNotAvailableError):
        unavail.predict(
            temperature=25.0,
            humidity=50.0,
            rainfall=0.0,
            wind_speed=5.0,
            soil_type="loamy",
            previous_moisture=20.0,
        )
