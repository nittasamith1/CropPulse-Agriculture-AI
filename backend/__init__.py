# CropPulse Backend Package
import os
import sys

_CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
_PARENT_DIR = os.path.dirname(_CURRENT_DIR)
for _p in (_PARENT_DIR, _CURRENT_DIR):
    if _p not in sys.path:
        sys.path.insert(0, _p)

