"""AI RHINO ARCHITECT - Validation Module.

Provides geometry, dimensional, and regulatory validation with
automatic correction and feedback loop to planner.
"""

from __future__ import annotations

from ai.validation.models import (
    CorrectionResult,
    CorrectionStrategy,
    ValidationCategory,
    ValidationIssue,
    ValidationResult,
    ValidationRule,
    ValidationRuleSet,
    ValidationSeverity,
    ValidationStatus,
)
from ai.validation.geometry import GeometryValidator, GEOMETRY_RULES, GEOMETRY_STRATEGIES
from ai.validation.dimensional import DimensionalValidator, DIMENSIONAL_RULES, DIMENSIONAL_STRATEGIES
from ai.validation.regulatory import RegulatoryValidator, REGULATORY_RULES, REGULATORY_STRATEGIES
from ai.validation.pipeline import ValidationPipeline, PipelineResult, ValidationFeedback

__all__ = [
    # Models
    "ValidationIssue",
    "ValidationResult",
    "ValidationRule",
    "ValidationRuleSet",
    "ValidationCategory",
    "ValidationSeverity",
    "ValidationStatus",
    "CorrectionStrategy",
    "CorrectionResult",
    # Validators
    "GeometryValidator",
    "DimensionalValidator",
    "RegulatoryValidator",
    # Pipeline
    "ValidationPipeline",
    "PipelineResult",
    "ValidationFeedback",
    # Built-in rules and strategies
    "GEOMETRY_RULES",
    "GEOMETRY_STRATEGIES",
    "DIMENSIONAL_RULES",
    "DIMENSIONAL_STRATEGIES",
    "REGULATORY_RULES",
    "REGULATORY_STRATEGIES",
]