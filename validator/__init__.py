"""
validator package exports

Canonical implementation lives in: integrity_validator.py

Public import surface:
    from validator import validate_output, ValidationError
"""

from integrity_validator import validate_output, ValidationError

__all__ = ["validate_output", "ValidationError"]