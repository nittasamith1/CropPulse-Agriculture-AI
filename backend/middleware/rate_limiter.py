"""
CropPulse – Rate Limiter Configuration
Uses slowapi (Starlette-compatible) with per-route and global limits.
"""

from slowapi import Limiter
from slowapi.util import get_remote_address

# Global limiter instance — imported in main.py and individual routers
limiter = Limiter(
    key_func=get_remote_address,
    default_limits=["200/minute"],
    headers_enabled=True,   # Adds X-RateLimit-* headers to responses
    strategy="fixed-window", # fixed-window | moving-window
)

# Per-route limit decorators (import and use as @limiter.limit("..."))
LIMITS = {
    "auth_register": "10/minute",
    "auth_login": "20/minute",
    "disease_predict": "30/minute",
    "soil_predict": "30/minute",
    "admin": "200/minute",
    "general": "100/minute",
}
