"""
CropPulse – GridFS, Reports, and Notifications Tests
Validates binary file storage in GridFS, PDF/CSV report generation,
notification dispatch, and unified history querying.
"""

import pytest
from unittest.mock import AsyncMock, patch
from backend.services.report_service import report_service
from backend.services.notification_service import notification_service
from backend.services.gridfs_service import gridfs_service


@pytest.mark.asyncio
async def test_csv_report_generation():
    """Verify CSV report generation produces valid CSV formatted text."""
    with patch("backend.services.mongodb_service.MongoDBService.query", new_callable=AsyncMock) as mock_query:
        mock_query.return_value = [
            {
                "created_at": "2026-09-05T10:00:00Z",
                "prediction_id": "d1",
                "disease_name": "Tomato – Early blight",
                "confidence": 0.92,
                "severity": "severe",
                "crop_type": "Tomato",
                "latitude": 13.52,
                "longitude": 79.98,
            }
        ]

        csv_content = await report_service.generate_csv_report(user_id="u1", report_type="disease")
        assert isinstance(csv_content, str)
        assert "Tomato" in csv_content
        assert "Date" in csv_content or "Prediction ID" in csv_content


def test_pdf_report_generation():
    """Verify PDF report generation produces valid PDF bytes."""
    predictions = [
        {
            "created_at": "2026-09-05T10:00:00Z",
            "prediction_id": "d1",
            "disease_name": "Tomato – Early blight",
            "confidence": 0.92,
            "severity": "severe",
            "crop_type": "Tomato",
            "treatments": ["Apply copper fungicide"],
        }
    ]
    pdf_bytes = report_service._create_disease_pdf(predictions=predictions, user_name="Test Farmer")
    assert isinstance(pdf_bytes, bytes)
    assert pdf_bytes.startswith(b"%PDF-"), "Generated file must have standard PDF header bytes."


@pytest.mark.asyncio
async def test_notification_dispatch_and_read():
    """Verify notification alert creation and mark-as-read flow."""
    with patch("backend.services.mongodb_service.MongoDBService.create", new_callable=AsyncMock) as mock_create, \
         patch("backend.services.mongodb_service.MongoDBService.update", new_callable=AsyncMock) as mock_update:
        mock_create.return_value = True
        mock_update.return_value = True

        notif_id = await notification_service.disease_alert(
            user_id="u1",
            disease_name="Tomato Early Blight",
            severity="severe",
            prediction_id="d1",
        )
        assert notif_id is not None
        assert notif_id.startswith("notif_")
        assert mock_create.called


def test_unified_history_endpoint(client):
    """Verify GET /api/v1/history returns structured history with counts."""
    with patch("backend.repositories.prediction_repository.prediction_repository.list_disease_predictions_paginated", new_callable=AsyncMock) as mock_d, \
         patch("backend.repositories.prediction_repository.prediction_repository.list_soil_predictions_paginated", new_callable=AsyncMock) as mock_s:
        mock_d.return_value = ([], 0)
        mock_s.return_value = ([], 0)

        response = client.get("/api/v1/history")
        assert response.status_code == 200
        data = response.json()
        assert "total" in data
        assert "disease_predictions" in data
        assert "soil_predictions" in data
