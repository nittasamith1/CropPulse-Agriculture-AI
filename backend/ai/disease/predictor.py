"""
CropPulse – PyTorch Disease Predictor
Executes low-latency inference using EfficientNet-B0 with Grad-CAM explainability.
"""

from typing import Dict, Any, List, Optional
from loguru import logger

try:
    import torch
    import torch.nn.functional as F
    TORCH_AVAILABLE = True
except ImportError:
    torch = None
    F = None
    TORCH_AVAILABLE = False

from backend.config import settings
from backend.ai.disease.model_manager import disease_model_manager, DISEASE_CLASSES_DISPLAY


class DiseasePredictionError(Exception):
    """Custom exception for disease prediction errors."""
    pass


class ModelNotAvailableError(DiseasePredictionError):
    """Raised when the disease model weights are not loaded."""
    pass


class DiseasePredictor:
    """
    High-performance disease prediction service wrapper around PyTorch EfficientNet-B0.
    """

    def __init__(self, manager=disease_model_manager):
        self.manager = manager

    def predict(
        self,
        image_bytes: bytes,
        crop_hint: Optional[str] = None,
        generate_explanation: bool = True,
    ) -> Dict[str, Any]:
        """
        Run inference on raw leaf image bytes.

        Returns:
            dict containing:
                - disease_class_key
                - disease_name
                - crop
                - confidence
                - severity
                - is_healthy
                - prediction_status
                - top_3
                - explanation_available
                - explanation_data_uri
                - model_version
        """
        model = self.manager.get_model()
        if model is None:
            logger.warning("Prediction requested but disease model is not available.")
            raise ModelNotAvailableError(
                "Disease detection model is not available. Please ensure trained weights (.pth) are placed in the configured model path."
            )

        # Preprocess input image
        from backend.ai.disease.preprocessing import preprocess_image
        input_tensor, pil_image = preprocess_image(image_bytes)
        device = getattr(self.manager, "device", "cpu")
        input_tensor = input_tensor.to(device)

        # Execute optimized inference
        with torch.inference_mode():
            logits = model(input_tensor)
            probabilities = F.softmax(logits, dim=-1)[0]

        top_k = min(3, len(self.manager.classes))
        top_probs, top_indices = torch.topk(probabilities, k=top_k)

        top_idx = top_indices[0].item()
        confidence = float(top_probs[0].item())
        class_key = self.manager.classes[top_idx]
        display_name = DISEASE_CLASSES_DISPLAY.get(class_key, class_key)

        raw_is_healthy_class = "healthy" in class_key.lower()

        # ── Confidence-Gated Health Logic ─────────────────────────────────────
        # Only mark as truly healthy when confidence >= threshold.
        # Low-confidence predictions are UNCERTAIN regardless of class name.
        confidence_threshold = settings.MODEL_CONFIDENCE_THRESHOLD
        if confidence >= confidence_threshold:
            is_healthy = raw_is_healthy_class
            prediction_status = "HEALTHY" if raw_is_healthy_class else "DISEASE_DETECTED"
        else:
            is_healthy = False  # Never assert health when uncertain
            prediction_status = "UNCERTAIN"
            logger.info(
                f"Prediction UNCERTAIN: top_class='{class_key}' confidence={confidence:.4f} "
                f"below threshold={confidence_threshold:.2f}."
            )

        severity = self._compute_severity(confidence, is_healthy, prediction_status)
        crop_name = self._extract_crop_name(class_key)

        top_3: List[Dict[str, Any]] = []
        for prob, idx in zip(top_probs, top_indices):
            c_key = self.manager.classes[idx.item()]
            top_3.append({
                "class_key": c_key,
                "display_name": DISEASE_CLASSES_DISPLAY.get(c_key, c_key),
                "confidence": round(float(prob.item()), 4),
            })

        # Generate Grad-CAM explainability if requested
        explanation_data_uri = None
        explanation_available = False

        if generate_explanation and prediction_status == "DISEASE_DETECTED":
            try:
                from backend.ai.disease.explainability import generate_gradcam_explanation
                target_layer = model.get_features_layer()
                with torch.enable_grad():
                    _, explanation_data_uri = generate_gradcam_explanation(
                        model=model,
                        target_layer=target_layer,
                        input_tensor=input_tensor.clone(),
                        original_pil=pil_image,
                        class_idx=top_idx,
                    )
                    explanation_available = True
            except Exception as e:
                logger.warning(f"Grad-CAM generation failed: {e}")
                explanation_available = False

        return {
            "disease_class_key": class_key,
            "disease_name": display_name,
            "crop": crop_name,
            "confidence": round(confidence, 4),
            "severity": severity,
            "is_healthy": is_healthy,
            "prediction_status": prediction_status,
            "top_3": top_3,
            "explanation_available": explanation_available,
            "explanation_data_uri": explanation_data_uri,
            "model_version": self.manager.version,
        }

    def _compute_severity(self, confidence: float, is_healthy: bool, status: str = "") -> str:
        """Categorize severity based on detection status and confidence."""
        if status == "UNCERTAIN":
            return "uncertain"
        if is_healthy or status == "HEALTHY":
            return "healthy"
        if confidence >= 0.85:
            return "severe"
        if confidence >= 0.65:
            return "moderate"
        return "mild"

    def _extract_crop_name(self, class_key: str) -> str:
        """Extract crop name from class key (e.g. 'Tomato___Early_blight' -> 'Tomato')."""
        parts = class_key.split("___")
        raw_crop = parts[0].replace("_", " ").split("(")[0].strip()
        return raw_crop.replace(",", "").title()


# Module-level singleton
disease_predictor = DiseasePredictor()
