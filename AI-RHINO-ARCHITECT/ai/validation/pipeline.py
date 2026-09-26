"""Validation pipeline for AI RHINO ARCHITECT.

Orchestrates geometry, dimensional, and regulatory validation with
automatic correction and feedback loop to planner.
"""

from __future__ import annotations

import logging
import time
import uuid
from dataclasses import dataclass, field
from typing import Any

from rhino.adapters.base import RhinoAdapter

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

logger = logging.getLogger(__name__)


@dataclass
class PipelineResult:
    """Result of running the full validation pipeline."""

    pipeline_id: str
    timestamp: float = field(default_factory=time.time)
    model_id: str | None = None
    geometry_result: ValidationResult | None = None
    dimensional_result: ValidationResult | None = None
    regulatory_result: ValidationResult | None = None
    combined_issues: list[ValidationIssue] = field(default_factory=list)
    corrections_applied: list[CorrectionResult] = field(default_factory=list)
    success: bool = False
    execution_time: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)

    def has_errors(self) -> bool:
        """Check if any validation errors exist."""
        return any(
            r and r.has_errors()
            for r in [self.geometry_result, self.dimensional_result, self.regulatory_result]
        )

    def has_warnings(self) -> bool:
        """Check if any validation warnings exist."""
        return any(
            r and r.has_warnings()
            for r in [self.geometry_result, self.dimensional_result, self.regulatory_result]
        )

    def get_all_issues(self) -> list[ValidationIssue]:
        """Get all issues from all validators."""
        issues = []
        for r in [self.geometry_result, self.dimensional_result, self.regulatory_result]:
            if r:
                issues.extend(r.issues)
        return issues

    def get_issues_by_category(self, category: ValidationCategory) -> list[ValidationIssue]:
        """Get issues filtered by category."""
        return [i for i in self.get_all_issues() if i.category == category]

    def get_issues_by_severity(self, severity: ValidationSeverity) -> list[ValidationIssue]:
        """Get issues filtered by severity."""
        return [i for i in self.get_all_issues() if i.severity == severity]

    def to_dict(self) -> dict[str, Any]:
        return {
            "pipeline_id": self.pipeline_id,
            "timestamp": self.timestamp,
            "model_id": self.model_id,
            "geometry_result": self.geometry_result.to_dict() if self.geometry_result else None,
            "dimensional_result": self.dimensional_result.to_dict() if self.dimensional_result else None,
            "regulatory_result": self.regulatory_result.to_dict() if self.regulatory_result else None,
            "combined_issues": [i.to_dict() for i in self.get_all_issues()],
            "corrections_applied": [
                {
                    "strategy_id": c.strategy_id,
                    "issue_rule_id": c.issue.rule_id,
                    "success": c.success,
                    "message": c.message,
                    "modified_elements": c.modified_elements,
                    "execution_time": c.execution_time,
                }
                for c in self.corrections_applied
            ],
            "success": self.success,
            "execution_time": self.execution_time,
            "metadata": self.metadata,
        }


class ValidationPipeline:
    """Orchestrates multi-category validation with auto-correction."""

    def __init__(
        self,
        adapter: RhinoAdapter,
        jurisdiction: str = "IBC 2021",
        auto_correct: bool = False,
        max_correction_iterations: int = 3,
    ) -> None:
        """Initialize the validation pipeline.

        Args:
            adapter: Rhino adapter for executing validation scripts
            jurisdiction: Building code jurisdiction
            auto_correct: Whether to automatically apply corrections
            max_correction_iterations: Maximum correction attempts per issue
        """
        self._adapter = adapter
        self._jurisdiction = jurisdiction
        self._auto_correct = auto_correct
        self._max_iterations = max_correction_iterations

        # Initialize validators
        self._geometry = GeometryValidator(adapter)
        self._dimensional = DimensionalValidator(adapter)
        self._regulatory = RegulatoryValidator(adapter, jurisdiction)

        # Build rule sets
        self._geometry_rules = GEOMETRY_RULES
        self._geometry_strategies = {s.strategy_id: s for s in GEOMETRY_STRATEGIES}
        self._dimensional_rules = DIMENSIONAL_RULES
        self._dimensional_strategies = {s.strategy_id: s for s in DIMENSIONAL_STRATEGIES}
        self._regulatory_rules = REGULATORY_RULES
        self._regulatory_strategies = {s.strategy_id: s for s in REGULATORY_STRATEGIES}

    async def validate(
        self,
        object_ids: list[str],
        element_types: dict[str, str],
        project_context: dict[str, Any] | None = None,
        categories: list[ValidationCategory] | None = None,
    ) -> PipelineResult:
        """Run full validation pipeline.

        Args:
            object_ids: List of object GUIDs to validate
            element_types: Mapping of object_id -> element_type
            project_context: Project-level context for regulatory checks
            categories: Specific categories to validate (default: all)

        Returns:
            PipelineResult with combined results
        """
        start_time = time.time()
        pipeline_id = f"pipe_{uuid.uuid4().hex[:8]}"
        model_id = object_ids[0] if object_ids else None

        result = PipelineResult(
            pipeline_id=pipeline_id,
            model_id=model_id,
            metadata={"jurisdiction": self._jurisdiction, "project_context": project_context or {}},
        )

        # Determine which categories to run
        if categories is None:
            categories = [ValidationCategory.GEOMETRY, ValidationCategory.DIMENSIONAL, ValidationCategory.REGULATORY]

        # Run geometry validation
        if ValidationCategory.GEOMETRY in categories:
            logger.info(f"Running geometry validation on {len(object_ids)} objects")
            result.geometry_result = await self._geometry.validate_objects(
                object_ids, element_types, self._geometry_rules
            )
            result.combined_issues.extend(result.geometry_result.issues)

        # Run dimensional validation
        if ValidationCategory.DIMENSIONAL in categories:
            logger.info(f"Running dimensional validation on {len(object_ids)} objects")
            result.dimensional_result = await self._dimensional.validate_objects(
                object_ids, element_types, self._dimensional_rules
            )
            result.combined_issues.extend(result.dimensional_result.issues)

        # Run regulatory validation
        if ValidationCategory.REGULATORY in categories:
            logger.info(f"Running regulatory validation on {len(object_ids)} objects")
            result.regulatory_result = await self._regulatory.validate_objects(
                object_ids, element_types, self._regulatory_rules, project_context
            )
            result.combined_issues.extend(result.regulatory_result.issues)

        # Apply auto-corrections if enabled
        if self._auto_correct and result.has_errors():
            logger.info("Auto-correction enabled, attempting fixes")
            result.corrections_applied = await self._apply_corrections(result.combined_issues, element_types)

            # Re-validate after corrections
            if result.corrections_applied:
                logger.info("Re-validating after corrections")
                # Re-run validations for corrected objects
                corrected_ids = set()
                for c in result.corrections_applied:
                    corrected_ids.update(c.modified_elements)

                if corrected_ids:
                    # Re-validate corrected objects
                    corrected_types = {oid: element_types.get(oid, "unknown") for oid in corrected_ids}
                    if ValidationCategory.GEOMETRY in categories:
                        result.geometry_result = await self._geometry.validate_objects(
                            list(corrected_ids), corrected_types, self._geometry_rules
                        )
                    if ValidationCategory.DIMENSIONAL in categories:
                        result.dimensional_result = await self._dimensional.validate_objects(
                            list(corrected_ids), corrected_types, self._dimensional_rules
                        )
                    if ValidationCategory.REGULATORY in categories:
                        result.regulatory_result = await self._regulatory.validate_objects(
                            list(corrected_ids), corrected_types, self._regulatory_rules, project_context
                        )

        result.success = not result.has_errors()
        result.execution_time = time.time() - start_time
        return result

    async def _apply_corrections(
        self,
        issues: list[ValidationIssue],
        element_types: dict[str, str],
    ) -> list[CorrectionResult]:
        """Apply correction strategies for issues."""
        corrections = []

        # Group issues by rule_id
        issues_by_rule: dict[str, list[ValidationIssue]] = {}
        for issue in issues:
            if issue.severity in (ValidationSeverity.ERROR, ValidationSeverity.CRITICAL):
                issues_by_rule.setdefault(issue.rule_id, []).append(issue)

        for rule_id, rule_issues in issues_by_rule.items():
            # Get strategy for this rule
            strategy = self._get_strategy_for_rule(rule_id)
            if not strategy or not strategy.auto_applicable:
                continue

            for issue in rule_issues:
                try:
                    correction = await self._apply_strategy(strategy, issue)
                    corrections.append(correction)
                    if not correction.success:
                        logger.warning(f"Correction {strategy.strategy_id} failed for {issue.rule_id}: {correction.message}")
                except Exception as e:
                    logger.error(f"Correction {strategy.strategy_id} raised exception: {e}")
                    corrections.append(CorrectionResult(
                        strategy_id=strategy.strategy_id,
                        issue=issue,
                        success=False,
                        message=f"Correction failed with exception: {e}",
                    ))

        return corrections

    def _get_strategy_for_rule(self, rule_id: str) -> CorrectionStrategy | None:
        """Get correction strategy for a rule."""
        for strategies in [self._geometry_strategies, self._dimensional_strategies, self._regulatory_strategies]:
            if rule_id in strategies:
                return strategies[rule_id]
        return None

    async def _apply_strategy(
        self,
        strategy: CorrectionStrategy,
        issue: ValidationIssue,
    ) -> CorrectionResult:
        """Apply a specific correction strategy."""
        if strategy.strategy_id in self._geometry_strategies:
            return await self._geometry.apply_correction(strategy, issue)
        elif strategy.strategy_id in self._dimensional_strategies:
            return await self._dimensional.apply_correction(strategy, issue)
        elif strategy.strategy_id in self._regulatory_strategies:
            return await self._regulatory.apply_correction(strategy, issue)
        else:
            return CorrectionResult(
                strategy_id=strategy.strategy_id,
                issue=issue,
                success=False,
                message=f"No validator found for strategy {strategy.strategy_id}",
            )

    async def validate_single(
        self,
        object_id: str,
        element_type: str,
        project_context: dict[str, Any] | None = None,
    ) -> PipelineResult:
        """Validate a single object."""
        return await self.validate([object_id], {object_id: element_type}, project_context)

    def create_ruleset(
        self,
        ruleset_id: str,
        name: str,
        description: str,
        version: str = "1.0.0",
        custom_rules: list[ValidationRule] | None = None,
        custom_strategies: list[CorrectionStrategy] | None = None,
    ) -> ValidationRuleSet:
        """Create a custom validation rule set."""
        all_rules = list(self._geometry_rules) + list(self._dimensional_rules) + list(self._regulatory_rules)
        if custom_rules:
            all_rules.extend(custom_rules)

        all_strategies = list(self._geometry_strategies.values()) + list(self._dimensional_strategies.values()) + list(self._regulatory_strategies.values())
        if custom_strategies:
            all_strategies.extend(custom_strategies)

        return ValidationRuleSet(
            ruleset_id=ruleset_id,
            name=name,
            description=description,
            version=version,
            rules=all_rules,
            strategies=all_strategies,
            jurisdiction=self._jurisdiction,
        )

    def get_available_rules(self, category: ValidationCategory | None = None) -> list[ValidationRule]:
        """Get all available validation rules."""
        all_rules = list(self._geometry_rules) + list(self._dimensional_rules) + list(self._regulatory_rules)
        if category:
            return [r for r in all_rules if r.category == category]
        return all_rules

    def get_available_strategies(self) -> list[CorrectionStrategy]:
        """Get all available correction strategies."""
        return list(self._geometry_strategies.values()) + list(self._dimensional_strategies.values()) + list(self._regulatory_strategies.values())


class ValidationFeedback:
    """Generates feedback for planner based on validation results."""

    @staticmethod
    def generate_feedback(pipeline_result: PipelineResult) -> dict[str, Any]:
        """Generate structured feedback for planner."""
        all_issues = pipeline_result.get_all_issues()
        feedback = {
            "validation_passed": pipeline_result.success,
            "total_issues": len(all_issues),
            "errors": pipeline_result.get_issues_by_severity(ValidationSeverity.ERROR),
            "warnings": pipeline_result.get_issues_by_severity(ValidationSeverity.WARNING),
            "critical": pipeline_result.get_issues_by_severity(ValidationSeverity.CRITICAL),
            "by_category": {},
            "suggested_corrections": [],
            "replan_required": False,
        }

        # Group by category
        for category in ValidationCategory:
            issues = pipeline_result.get_issues_by_category(category)
            if issues:
                feedback["by_category"][category.value] = {
                    "count": len(issues),
                    "errors": len([i for i in issues if i.severity in (ValidationSeverity.ERROR, ValidationSeverity.CRITICAL)]),
                    "warnings": len([i for i in issues if i.severity == ValidationSeverity.WARNING]),
                    "issues": [i.to_dict() for i in issues],
                }

        # Determine if replan is needed
        error_count = len(feedback["errors"]) + len(feedback["critical"])
        if error_count > 0:
            feedback["replan_required"] = True
            feedback["suggested_corrections"] = [
                {
                    "rule_id": c.issue.rule_id,
                    "strategy_id": c.strategy_id,
                    "success": c.success,
                    "message": c.message,
                }
                for c in pipeline_result.corrections_applied
            ]

        return feedback

    @staticmethod
    def format_for_llm(pipeline_result: PipelineResult) -> str:
        """Format validation results for LLM consumption."""
        all_issues = pipeline_result.get_all_issues()
        lines = [
            f"Validation Result: {'PASSED' if pipeline_result.success else 'FAILED'}",
            f"Total Issues: {len(all_issues)}",
            f"Errors: {len(pipeline_result.get_issues_by_severity(ValidationSeverity.ERROR))}",
            f"Warnings: {len(pipeline_result.get_issues_by_severity(ValidationSeverity.WARNING))}",
            "",
        ]

        for category in ValidationCategory:
            issues = pipeline_result.get_issues_by_category(category)
            if issues:
                lines.append(f"## {category.value.upper()} Issues:")
                for issue in issues:
                    lines.append(f"  - [{issue.severity.value.upper()}] {issue.rule_id}: {issue.message}")
                    if issue.element_id:
                        lines.append(f"    Element: {issue.element_id} ({issue.element_type})")
                    if issue.expected is not None:
                        lines.append(f"    Expected: {issue.expected}, Actual: {issue.actual}")
                lines.append("")

        if pipeline_result.corrections_applied:
            lines.append("## Corrections Applied:")
            for c in pipeline_result.corrections_applied:
                status = "SUCCESS" if c.success else "FAILED"
                lines.append(f"  - [{status}] {c.strategy_id}: {c.message}")

        return "\n".join(lines)