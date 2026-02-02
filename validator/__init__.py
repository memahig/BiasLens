
"""
validator package exports

Streamlit and some call sites import:

    from validator import validate_output, ValidationError

Canonical implementation currently lives in: integrity_validator.py
"""

from integrity_validator import validate_output, validate_report_pack

# Keep ValidationError consistent with the canonical validator
from integrity_validator import ValidationError

__all__ = ["validate_output", "validate_report_pack", "ValidationError"]
