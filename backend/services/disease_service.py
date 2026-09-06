"""
CropPulse – Disease Detection Business Service
Coordinates validation, file storage, PyTorch inference, Grad-CAM, agronomic recommendations,
and database persistence.
"""

from typing import Dict, Any, Optional
from loguru import logger
from fastapi import UploadFile

from backend.ai.disease.predictor import disease_predictor, ModelNotAvailableError
from backend.ai.intelligence.recommendation_engine import get_disease_recommendations, get_crop_from_class
from backend.services.file_service import file_service
from backend.repositories.prediction_repository import prediction_repository
from backend.repositories.farm_repository import farm_repository
from backend.services.notification_service import notification_service
from backend.utils.helpers import generate_id, utc_now
from backend.utils.validators import validate_image_upload

# Shown when model confidence is below threshold
_UNCERTAIN_RECOMMENDATIONS = {
    "treatments": [
        "AI prediction confidence is too low for reliable treatment advice.",
        "Upload a clear, close-up image of the affected leaf in good natural lighting.",
        "Ensure the leaf fills at least 60% of the frame and is in sharp focus.",
    ],
    "prevention": [
        "Monitor the plant daily for visible symptom changes.",
        "Consult a local agricultural extension officer if symptoms persist or worsen.",
    ],
    "pesticides": ["No pesticide recommendation — diagnosis is uncertain. Do not apply chemicals without confirmed diagnosis."],
    "organic": ["No organic remedy recommendation — diagnosis uncertain."],
}


class DiseaseService:
    def __init__(self, predictor=disease_predictor, pred_repo=prediction_repository, farm_repo=farm_repository):
        self.predictor = predictor
        self.pred_repo = pred_repo
        self.farm_repo = farm_repo

    async def detect_disease(
        self,
        file: UploadFile,
        user_id: str,
        farm_id: Optional[str] = None,
        crop_type: Optional[str] = None,
        latitude: Optional[float] = None,
        longitude: Optional[float] = None,
        notes: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Process uploaded leaf image through the complete disease intelligence pipeline.
        """
        # 1. Validate file strictly
        image_bytes = await validate_image_upload(file)

        # 2. Upload leaf image to storage
        filename = file.filename or "leaf.jpg"
        content_type = file.content_type or "image/jpeg"
        image_url = await file_service.upload_file(
            content=image_bytes,
            filename=filename,
            content_type=content_type,
            metadata={"user_id": user_id, "category": "leaf"},
        )

        # 3. PyTorch Model Inference
        # Raises ModelNotAvailableError if weights are missing
        pred_result = self.predictor.predict(image_bytes=image_bytes, crop_hint=crop_type)

        # 4. Resolve Agronomic Recommendations
        # UNCERTAIN predictions get a generic "retake image" response,
        # not disease-specific treatments.
        detected_crop = crop_type or pred_result["crop"]
        prediction_status = pred_result.get("prediction_status", "UNCERTAIN")
        if prediction_status == "UNCERTAIN":
            recommendations = _UNCERTAIN_RECOMMENDATIONS
        else:
            recommendations = get_disease_recommendations(
                disease_class_key=pred_result["disease_class_key"],
                is_healthy=pred_result["is_healthy"],
            )

        # 5. Farm Geospatial Linking
        farm_lat, farm_lon, district, state = latitude, longitude, None, None
        if farm_id:
            farm_doc = await self.farm_repo.get(farm_id)
            if farm_doc:
                farm_lat = farm_lat or farm_doc.get("latitude")
                farm_lon = farm_lon or farm_doc.get("longitude")
                district = farm_doc.get("district")
                state = farm_doc.get("state")

        # 6. Build Document Record
        prediction_id = generate_id("dpred")
        now = utc_now()

        prediction_doc = {
            "prediction_id": prediction_id,
            "user_id": user_id,
            "farm_id": farm_id,
            "image_url": image_url,
            "disease_name": pred_result["disease_name"],
            "disease_class_key": pred_result["disease_class_key"],
            "confidence": pred_result["confidence"],
            "prediction_status": prediction_status,
            "severity": pred_result["severity"],
            "is_healthy": pred_result["is_healthy"],
            "crop_type": detected_crop,
            "treatments": recommendations.get("treatments", []),
            "prevention_tips": recommendations.get("prevention", []),
            "recommended_pesticides": recommendations.get("pesticides", []),
            # Store under both keys so old and new frontend both work
            "organic_remedies": recommendations.get("organic", []),
            "organic_alternatives": recommendations.get("organic", []),
            "top_3": pred_result.get("top_3", []),
            "explanation_available": pred_result.get("explanation_available", False),
            "explanation_data_uri": pred_result.get("explanation_data_uri"),
            "latitude": farm_lat,
            "longitude": farm_lon,
            "district": district,
            "state": state,
            "notes": notes,
            "model_version": pred_result.get("model_version", "1.0.0"),
            "created_at": now,
        }

        # 7. Persist to MongoDB
        await self.pred_repo.save_disease_prediction(prediction_doc)

        # 8. Notification only for confirmed moderate/severe disease detections
        if prediction_status == "DISEASE_DETECTED" and pred_result["severity"] in ["moderate", "severe"]:
            try:
                await notification_service.disease_detected_alert(
                    user_id=user_id,
                    disease_name=pred_result["disease_name"],
                    severity=pred_result["severity"],
                    farm_name=farm_id or "Farm",
                    prediction_id=prediction_id,
                )
            except Exception as e:
                logger.warning(f"Failed to emit notification: {e}")

        # Update farm metadata if farm_id was provided
        if farm_id:
            await self.farm_repo.update(farm_id, {
                "last_disease": pred_result["disease_name"],
                "last_severity": pred_result["severity"],
                "last_prediction_date": now,
            })

        return prediction_doc


disease_service = DiseaseService()
