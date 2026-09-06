"""
CropPulse root entrypoint alias.
Allows starting the server via 'uvicorn main:app' from the repository root.
"""
import os
import sys

_CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
if _CURRENT_DIR not in sys.path:
    sys.path.insert(0, _CURRENT_DIR)

from backend.main import app

__all__ = ["app"]
