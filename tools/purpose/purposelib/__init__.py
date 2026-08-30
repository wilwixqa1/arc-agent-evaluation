"""Purpose document tooling for the Arc agent evaluation project."""
from .core import (
    canonicalize, purpose_hash, seal, verify_seal,
    validate, load_schema, specificity,
    ValidationResult, Specificity,
)

__all__ = [
    "canonicalize", "purpose_hash", "seal", "verify_seal",
    "validate", "load_schema", "specificity",
    "ValidationResult", "Specificity",
]
__version__ = "0.1.0"
