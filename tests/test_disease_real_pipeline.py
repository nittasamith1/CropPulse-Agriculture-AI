"""
CropPulse – Real PyTorch Disease Pipeline Tests
Validates real model loading, EfficientNet-B0 inference, Grad-CAM explainability,
edge-case handling, upload validation, error responses, and concurrent safety.
"""

import io
import os
import threading
import pytest
from PIL import Image
from unittest.mock import patch
from fastapi import UploadFile

from backend.ai.disease.model_manager import (
    disease_model_manager,
    DISEASE_CLASSES,
    DISEASE_CLASSES_DISPLAY,
)
from backend.ai.disease.predictor import (
    disease_predictor,
    ModelNotAvailableError,
    DiseasePredictor,
)
from backend.ai.disease.preprocessing import preprocess_image
from backend.ai.disease.explainability import generate_gradcam_explanation


def _create_test_image_bytes(color=(34, 139, 34), size=(224, 224), format="JPEG") -> bytes:
    """Helper to generate in-memory test image bytes."""
    img = Image.new("RGB", size, color=color)
    buf = io.BytesIO()
    img.save(buf, format=format)
    return buf.getvalue()


def test_disease_model_weights_exist():
    """Verify that the PyTorch disease model checkpoint exists on disk."""
    assert os.path.exists("ai_models/disease_model/disease_model.pth"), (
        "ai_models/disease_model/disease_model.pth must exist for production inference."
    )


def test_disease_model_loading_and_metadata():
    """Verify real disease model loads correctly and sets eval mode."""
    loaded = disease_model_manager.load_model()
    assert loaded is True
    assert disease_model_manager.is_loaded is True

    model = disease_model_manager.get_model()
    assert model is not None
    assert not model.training, "PyTorch model must be in eval() mode for inference."

    meta = disease_model_manager.get_metadata()
    assert meta["architecture"] == "EfficientNet-B0"
    assert meta["framework"] == "pytorch"
    assert meta["classes_count"] == 38


def test_real_disease_inference_pipeline():
    """Test full inference pipeline with real model on synthetic leaf image."""
    img_bytes = _create_test_image_bytes()
    result = disease_predictor.predict(img_bytes)

    assert "disease_class_key" in result
    assert result["disease_class_key"] in DISEASE_CLASSES
    assert "disease_name" in result
    assert "confidence" in result
    assert 0.0 <= result["confidence"] <= 1.0
    assert result["severity"] in ["healthy", "mild", "moderate", "severe", "uncertain"]
    assert "prediction_status" in result
    assert result["prediction_status"] in ["HEALTHY", "DISEASE_DETECTED", "UNCERTAIN"]
    assert "top_3" in result
    assert len(result["top_3"]) == 3
    assert "model_version" in result


def test_gradcam_generation():
    """Verify Grad-CAM produces a valid JPEG overlay and base64 URI."""
    img_bytes = _create_test_image_bytes(color=(139, 69, 19))
    tensor, pil_img = preprocess_image(img_bytes)

    model = disease_model_manager.get_model()
    target_layer = model.get_features_layer()

    overlay_bytes, data_uri = generate_gradcam_explanation(
        model=model,
        target_layer=target_layer,
        input_tensor=tensor,
        original_pil=pil_img,
        class_idx=0,
    )

    assert len(overlay_bytes) > 500
    assert data_uri.startswith("data:image/jpeg;base64,")


def test_corrupt_image_rejection(client):
    """Corrupt or non-image bytes should be safely rejected with 400 Bad Request."""
    corrupt_data = b"NOT_A_VALID_IMAGE_CONTENT"
    response = client.post(
        "/api/v1/disease/detect",
        files={"file": ("test.jpg", corrupt_data, "image/jpeg")},
    )
    assert response.status_code == 400
    assert "Invalid or corrupted" in str(response.json())


def test_unsupported_file_extension_rejection(client):
    """Files with non-image extensions should be rejected with 400 Bad Request."""
    img_bytes = _create_test_image_bytes()
    response = client.post(
        "/api/v1/disease/detect",
        files={"file": ("malicious.exe", img_bytes, "image/jpeg")},
    )
    assert response.status_code == 400
    assert "Invalid file type" in str(response.json())


def test_unsupported_mime_type_rejection(client):
    """Unsupported MIME types should be rejected with 415 Unsupported Media Type."""
    img_bytes = _create_test_image_bytes()
    response = client.post(
        "/api/v1/disease/detect",
        files={"file": ("test.jpg", img_bytes, "application/pdf")},
    )
    assert response.status_code == 415


def test_oversized_upload_rejection(client):
    """Uploads exceeding max_size_mb should be rejected with 413 Payload Too Large."""
    # Test validator with small size limit
    from backend.utils.validators import validate_image_upload
    from fastapi import UploadFile, HTTPException

    mock_file = UploadFile(
        filename="giant_leaf.jpg",
        file=io.BytesIO(b"X" * (11 * 1024 * 1024)),
        headers={"content-type": "image/jpeg"},
    )
    with pytest.raises(HTTPException) as exc_info:
        import asyncio
        asyncio.run(validate_image_upload(mock_file, max_size_mb=10))
    assert exc_info.value.status_code == 413


def test_missing_model_fails_safely():
    """Predictor should raise ModelNotAvailableError when model fails to load."""
    class FakeEmptyManager:
        def get_model(self):
            return None

    unavail_predictor = DiseasePredictor(manager=FakeEmptyManager())
    with pytest.raises(ModelNotAvailableError):
        unavail_predictor.predict(_create_test_image_bytes())


def test_concurrent_inference_thread_safety():
    """Multiple simultaneous threads running inference must not corrupt state."""
    img_bytes = _create_test_image_bytes()
    results = []
    errors = []

    def worker():
        try:
            res = disease_predictor.predict(img_bytes)
            results.append(res)
        except Exception as e:
            errors.append(e)

    threads = [threading.Thread(target=worker) for _ in range(5)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert len(errors) == 0, f"Concurrent inference encountered errors: {errors}"
    assert len(results) == 5
    for r in results:
        assert "disease_class_key" in r


def test_uncertain_status_on_low_confidence_never_claims_healthy():
    """Verify that low confidence never asserts healthy even if top class contains 'healthy'."""
    import torch
    import torch.nn as nn
    from backend.ai.disease.predictor import DiseasePredictor

    class MockLowConfidenceManager:
        classes = ["Pepper,_bell___healthy", "Tomato___Late_blight"]
        version = "1.0.0"
        device = "cpu"

        def get_model(self):
            # Returns almost uniform distribution across classes (~50% < 65% threshold)
            class UniformModel(nn.Module):
                def __call__(self, x):
                    return torch.tensor([[0.05, 0.01]])
                def get_features_layer(self):
                    return None
            return UniformModel()

    predictor = DiseasePredictor(manager=MockLowConfidenceManager())
    res = predictor.predict(_create_test_image_bytes(), generate_explanation=False)

    assert res["prediction_status"] == "UNCERTAIN"
    assert res["is_healthy"] is False
    assert res["severity"] == "uncertain"
    assert res["confidence"] < 0.65


def test_high_confidence_healthy_marked_healthy():
    """Verify high confidence healthy class correctly sets is_healthy=True."""
    import torch
    import torch.nn as nn
    from backend.ai.disease.predictor import DiseasePredictor

    class MockHighConfidenceHealthyManager:
        classes = ["Tomato___healthy", "Tomato___Late_blight"]
        version = "1.0.0"
        device = "cpu"

        def get_model(self):
            class ConfidentHealthyModel(nn.Module):
                def __call__(self, x):
                    return torch.tensor([[10.0, -10.0]])
                def get_features_layer(self):
                    return None
            return ConfidentHealthyModel()

    predictor = DiseasePredictor(manager=MockHighConfidenceHealthyManager())
    res = predictor.predict(_create_test_image_bytes(), generate_explanation=False)

    assert res["prediction_status"] == "HEALTHY"
    assert res["is_healthy"] is True
    assert res["severity"] == "healthy"
    assert res["confidence"] > 0.90

