"""Validation models for AI RHINO ARCHITECT.

Defines validation rules, results, and correction strategies.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class ValidationSeverity(str, Enum):
    """Severity level of a validation issue."""

    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class ValidationCategory(str, Enum):
    """Category of validation check."""

    GEOMETRY = "geometry"           # Geometric validity (closed, manifold, etc.)
    DIMENSIONAL = "dimensional"     # Dimensional constraints
    REGULATORY = "regulatory"       # Building code compliance
    TOPOLOGICAL = "topological"     # Spatial relationships
    PERFORMANCE = "performance"     # Structural, thermal, etc.


class ValidationStatus(str, Enum):
    """Status of a validation check."""

    PASSED = "passed"
    FAILED = "failed"
    SKIPPED = "skipped"
    PENDING = "pending"


@dataclass
class ValidationIssue:
    """A single validation issue found during checking."""

    rule_id: str
    category: ValidationCategory
    severity: ValidationSeverity
    message: str
    element_id: str | None = None  # GUID of the element that failed
    element_type: str | None = None  # Type of element (wall, floor, etc.)
    location: dict[str, Any] | None = None  # Spatial location info
    expected: Any = None
    actual: Any = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "rule_id": self.rule_id,
            "category": self.category.value,
            "severity": self.severity.value,
            "message": self.message,
            "element_id": self.element_id,
            "element_type": self.element_type,
            "location": self.location,
            "expected": self.expected,
            "actual": self.actual,
            "metadata": self.metadata,
        }


@dataclass
class ValidationResult:
    """Result of running validation checks on a model."""

    validation_id: str
    timestamp: datetime = field(default_factory=datetime.now)
    model_id: str | None = None  # Project/model identifier
    status: ValidationStatus = ValidationStatus.PENDING
    issues: list[ValidationIssue] = field(default_factory=list)
    passed_count: int = 0
    failed_count: int = 0
    warning_count: int = 0
    info_count: int = 0
    execution_time: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)

    def add_issue(self, issue: ValidationIssue) -> None:
        """Add an issue and update counters."""
        self.issues.append(issue)
        if issue.severity == ValidationSeverity.ERROR or issue.severity == ValidationSeverity.CRITICAL:
            self.failed_count += 1
        elif issue.severity == ValidationSeverity.WARNING:
            self.warning_count += 1
        elif issue.severity == ValidationSeverity.INFO:
            self.info_count += 1

    def has_errors(self) -> bool:
        """Check if any errors or critical issues exist."""
        return self.failed_count > 0

    def has_warnings(self) -> bool:
        """Check if any warnings exist."""
        return self.warning_count > 0

    def get_issues_by_category(self, category: ValidationCategory) -> list[ValidationIssue]:
        """Get issues filtered by category."""
        return [i for i in self.issues if i.category == category]

    def get_issues_by_severity(self, severity: ValidationSeverity) -> list[ValidationIssue]:
        """Get issues filtered by severity."""
        return [i for i in self.issues if i.severity == severity]

    def to_dict(self) -> dict[str, Any]:
        return {
            "validation_id": self.validation_id,
            "timestamp": self.timestamp.isoformat(),
            "model_id": self.model_id,
            "status": self.status.value,
            "issues": [i.to_dict() for i in self.issues],
            "passed_count": self.passed_count,
            "failed_count": self.failed_count,
            "warning_count": self.warning_count,
            "info_count": self.info_count,
            "execution_time": self.execution_time,
            "metadata": self.metadata,
        }


class ValidationRule(BaseModel):
    """Definition of a validation rule."""

    rule_id: str = Field(..., description="Unique rule identifier")
    name: str = Field(..., description="Human-readable rule name")
    description: str = Field(..., description="What this rule checks")
    category: ValidationCategory = Field(..., description="Rule category")
    severity: ValidationSeverity = Field(default=ValidationSeverity.ERROR, description="Default severity")
    applies_to: list[str] = Field(default_factory=list, description="Element types this rule applies to")
    parameters: dict[str, Any] = Field(default_factory=dict, description="Rule-specific parameters")
    enabled: bool = Field(default=True, description="Whether rule is active")
    jurisdiction: str | None = Field(None, description="Applicable jurisdiction (for regulatory rules)")
    references: list[str] = Field(default_factory=list, description="Code/standard references")

    def matches_element(self, element_type: str) -> bool:
        """Check if rule applies to an element type."""
        return not self.applies_to or element_type in self.applies_to


class CorrectionStrategy(BaseModel):
    """Strategy for automatically correcting a validation issue."""

    strategy_id: str = Field(..., description="Unique strategy identifier")
    rule_id: str = Field(..., description="Rule this strategy addresses")
    name: str = Field(..., description="Human-readable strategy name")
    description: str = Field(..., description="How the correction works")
    auto_applicable: bool = Field(default=False, description="Can be applied automatically")
    parameters: dict[str, Any] = Field(default_factory=dict, description="Strategy parameters")
    risk_level: str = Field(default="low", description="Risk of applying: low, medium, high")
    side_effects: list[str] = Field(default_factory=list, description="Potential side effects")


@dataclass
class CorrectionResult:
    """Result of applying a correction strategy."""

    strategy_id: str
    issue: ValidationIssue
    success: bool
    message: str
    modified_elements: list[str] = field(default_factory=list)  # GUIDs of modified elements
    new_issues: list[ValidationIssue] = field(default_factory=list)  # Issues introduced by correction
    execution_time: float = 0.0


class ValidationRuleSet(BaseModel):
    """Collection of validation rules for a specific context."""

    ruleset_id: str
    name: str
    description: str
    version: str
    rules: list[ValidationRule] = Field(default_factory=list)
    strategies: list[CorrectionStrategy] = Field(default_factory=list)
    jurisdiction: str | None = None
    building_type: str | None = None
    occupancy: str | None = None

    def get_enabled_rules(self, category: ValidationCategory | None = None) -> list[ValidationRule]:
        """Get enabled rules, optionally filtered by category."""
        rules = [r for r in self.rules if r.enabled]
        if category:
            rules = [r for r in rules if r.category == category]
        return rules

    def get_strategy_for_rule(self, rule_id: str) -> CorrectionStrategy | None:
        """Get correction strategy for a rule."""
        for s in self.strategies:
            if s.rule_id == rule_id:
                return s
        return None