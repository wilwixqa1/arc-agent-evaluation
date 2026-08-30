"""Judge: rubric-driven evaluation of responses against sealed purposes."""
from .verdict import (
    JudgeAnswers, DerivedVerdict, derive, aggregate, criterion_consistency, RUBRIC_VERSION,
)
from .prompt import SYSTEM, build_prompt, parse_judge_output, blind_attempt, scrub_text
from .providers import get_provider, available_providers, Provider, ProviderError, Completion
from .constraints import check as check_constraints, ConstraintResult, Check, lookup
from .record import (
    build_record, aggregate_records, validate_record, verdict_hash, SCHEMA_VERSION,
)

__all__ = [
    "JudgeAnswers", "DerivedVerdict", "derive", "aggregate", "criterion_consistency",
    "RUBRIC_VERSION", "SYSTEM", "build_prompt", "parse_judge_output", "blind_attempt",
    "scrub_text", "get_provider", "available_providers", "Provider", "ProviderError",
    "Completion", "check_constraints", "ConstraintResult", "Check", "lookup",
    "build_record", "aggregate_records", "validate_record", "verdict_hash",
    "SCHEMA_VERSION",
]
__version__ = "0.1.0"
