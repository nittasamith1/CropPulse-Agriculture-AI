"""
CropPulse – Helper Utilities
Common utilities for ID generation, timestamp handling, data sanitization, etc.
"""

import uuid
import string
from datetime import datetime, timezone
from typing import Any, Dict, Optional


def generate_id(prefix: str = "ag") -> str:
    """Generate a unique ID with a given prefix."""
    unique_part = uuid.uuid4().hex[:12]
    return f"{prefix}_{unique_part}"


def utc_now() -> datetime:
    """Return current UTC datetime."""
    return datetime.now(timezone.utc)


def sanitize_dict(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Remove None and empty values from a dict for MongoDB updates.
    Use when building $set payloads to avoid overwriting fields with None.
    """
    return {k: v for k, v in data.items() if v is not None}


def severity_from_confidence(confidence: float, is_healthy: bool = False) -> str:
    """
    Map confidence score to severity level.
    Higher confidence = more severe disease.
    """
    if is_healthy or confidence < 0.3:
        return "healthy"
    elif confidence < 0.55:
        return "mild"
    elif confidence < 0.75:
        return "moderate"
    else:
        return "severe"


def marker_color_from_severity(severity: str) -> str:
    """Map severity level to a color for map markers."""
    colors = {
        "healthy": "#28a745",    # Green
        "mild": "#ffc107",       # Yellow
        "moderate": "#fd7e14",   # Orange
        "severe": "#dc3545",     # Red
    }
    return colors.get(severity, "#6c757d")  # Gray fallback


def confidence_to_percentage(confidence: float) -> str:
    """Convert confidence (0-1) to percentage string."""
    return f"{confidence * 100:.1f}%"


def parse_pagination_params(page: int = 1, page_size: int = 20) -> tuple:
    """
    Validate and return pagination parameters.
    Returns (offset, limit).
    """
    page = max(1, page)
    page_size = min(100, max(1, page_size))  # Cap at 100
    offset = (page - 1) * page_size
    return offset, page_size


def validate_coordinates(latitude: float, longitude: float) -> bool:
    """Validate geographic coordinates."""
    return -90 <= latitude <= 90 and -180 <= longitude <= 180


def truncate_string(text: str, max_length: int = 500) -> str:
    """Truncate text to max length, respecting word boundaries."""
    if len(text) <= max_length:
        return text
    return text[:max_length].rsplit(" ", 1)[0] + "..."


def format_phone_number(phone: str) -> str:
    """Format phone number (basic validation/cleanup)."""
    # Remove all non-digit characters
    digits = "".join(c for c in phone if c.isdigit())
    return f"+{digits}" if digits else phone


def is_valid_email(email: str) -> bool:
    """Basic email validation."""
    return "@" in email and "." in email.split("@")[-1]


def generate_slug(text: str) -> str:
    """Generate URL-safe slug from text."""
    valid_chars = "-_.() %s%s" % (string.ascii_letters, string.digits)
    filename = "".join(c if c in valid_chars else "_" for c in text)
    return filename.lower().replace(" ", "-")
