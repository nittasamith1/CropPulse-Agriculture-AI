"""
CropPulse – Validators
Request/file validation utilities for API endpoints.
"""

from typing import List, Tuple, Optional
from fastapi import UploadFile, HTTPException, status
from PIL import Image
import io
from loguru import logger

from backend.config import settings


ALLOWED_EXTENSIONS = {"jpg", "jpeg", "png", "webp", "bmp"}
MIME_TYPES = {
    "image/jpeg": "jpg",
    "image/png": "png",
    "image/webp": "webp",
    "image/bmp": "bmp",
}


async def validate_image_upload(
    file: UploadFile,
    max_size_mb: Optional[int] = None,
) -> bytes:
    """
    Validate an uploaded image file.
    Returns the image bytes if valid, raises HTTPException otherwise.
    """
    if max_size_mb is None:
        max_size_mb = settings.MAX_UPLOAD_SIZE_MB

    # Check filename
    if not file.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File must have a name.",
        )

    # Check file extension
    ext = file.filename.split(".")[-1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid file type. Allowed: {', '.join(ALLOWED_EXTENSIONS)}",
        )

    # Check MIME type
    if file.content_type not in MIME_TYPES:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=f"Unsupported MIME type: {file.content_type}",
        )

    # Read file content
    try:
        content = await file.read()
    except Exception as e:
        logger.error(f"Failed to read file: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Could not read file.",
        )

    # Check file size
    max_bytes = max_size_mb * 1024 * 1024
    if len(content) > max_bytes:
        raise HTTPException(
            status_code=status.HTTP_413_CONTENT_TOO_LARGE,
            detail=f"File too large. Maximum size: {max_size_mb}MB.",
        )

    if len(content) == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File is empty.",
        )

    # Validate image structure
    try:
        img = Image.open(io.BytesIO(content))
        img.verify()
        logger.info(f"Image validated: {file.filename} ({img.size})")
    except Exception as e:
        logger.error(f"Invalid image file: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or corrupted image file.",
        )

    return content


def validate_soil_prediction_input(
    temperature: float,
    humidity: float,
    rainfall: float,
    soil_temperature: Optional[float] = None,
    wind_speed: Optional[float] = None,
) -> None:
    """
    Validate soil prediction input parameters.
    Raises HTTPException if invalid.
    """
    errors = []

    if not -50 <= temperature <= 60:
        errors.append("Temperature must be between -50°C and 60°C")

    if not 0 <= humidity <= 100:
        errors.append("Humidity must be between 0% and 100%")

    if not 0 <= rainfall <= 500:
        errors.append("Rainfall must be between 0mm and 500mm")

    if soil_temperature is not None and not -20 <= soil_temperature <= 70:
        errors.append("Soil temperature must be between -20°C and 70°C")

    if wind_speed is not None and not 0 <= wind_speed <= 100:
        errors.append("Wind speed must be between 0 and 100 km/h")

    if errors:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="; ".join(errors),
        )


def validate_coordinates(latitude: float, longitude: float) -> None:
    """Validate geographic coordinates."""
    if not -90 <= latitude <= 90:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Latitude must be between -90 and 90.",
        )

    if not -180 <= longitude <= 180:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Longitude must be between -180 and 180.",
        )


def validate_pagination(page: int, page_size: int) -> Tuple[int, int]:
    """Validate pagination parameters."""
    page = max(1, page)
    page_size = min(100, max(1, page_size))  # Cap at 100
    return page, page_size
