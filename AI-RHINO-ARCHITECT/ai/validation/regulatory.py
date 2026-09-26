"""Regulatory validation engine for AI RHINO ARCHITECT.

Implements building code compliance checks for architectural elements.
"""

from __future__ import annotations

import json
import logging
from typing import Any

from rhino.adapters.base import RhinoAdapter

from ai.validation.models import (
    CorrectionResult,
    CorrectionStrategy,
    ValidationCategory,
    ValidationIssue,
    ValidationResult,
    ValidationRule,
    ValidationSeverity,
    ValidationStatus,
)

logger = logging.getLogger(__name__)


# Built-in regulatory validation rules (IBC 2021 baseline, extensible for local codes)
REGULATORY_RULES = [
    ValidationRule(
        rule_id="reg_ibc_occupancy_classification",
        name="Occupancy Classification",
        description="Verify building has valid occupancy classification",
        category=ValidationCategory.REGULATORY,
        severity=ValidationSeverity.ERROR,
        applies_to=["building", "project"],
        parameters={"allowed_occupancies": ["A", "B", "E", "F", "H", "I", "M", "R", "S", "U"]},
        jurisdiction="IBC 2021",
        references=["IBC 2021 Chapter 3"],
    ),
    ValidationRule(
        rule_id="reg_ibc_construction_type",
        name="Construction Type",
        description="Verify construction type matches height/area limits",
        category=ValidationCategory.REGULATORY,
        severity=ValidationSeverity.ERROR,
        applies_to=["building", "project"],
        parameters={"allowed_types": ["IA", "IB", "IIA", "IIB", "IIIA", "IIIB", "IV", "VA", "VB"]},
        jurisdiction="IBC 2021",
        references=["IBC 2021 Chapter 6"],
    ),
    ValidationRule(
        rule_id="reg_ibc_fire_resistance",
        name="Fire Resistance Rating",
        description="Verify fire resistance ratings for building elements",
        category=ValidationCategory.REGULATORY,
        severity=ValidationSeverity.ERROR,
        applies_to=["wall", "floor", "column", "beam", "door", "window"],
        parameters={},
        jurisdiction="IBC 2021",
        references=["IBC 2021 Table 601", "IBC 2021 Section 703"],
    ),
    ValidationRule(
        rule_id="reg_ibc_means_of_egress",
        name="Means of Egress",
        description="Verify adequate means of egress provided",
        category=ValidationCategory.REGULATORY,
        severity=ValidationSeverity.ERROR,
        applies_to=["building", "floor", "door", "stair", "corridor"],
        parameters={},
        jurisdiction="IBC 2021",
        references=["IBC 2021 Chapter 10"],
    ),
    ValidationRule(
        rule_id="reg_ibc_accessibility",
        name="Accessibility Requirements",
        description="Verify accessibility compliance (ADA/ANSI A117.1)",
        category=ValidationCategory.REGULATORY,
        severity=ValidationSeverity.ERROR,
        applies_to=["door", "window", "stair", "ramp", "restroom", "parking"],
        parameters={},
        jurisdiction="IBC 2021 / ADA 2010",
        references=["IBC 2021 Chapter 11", "ADA 2010 Standards"],
    ),
    ValidationRule(
        rule_id="reg_ibc_structural_loads",
        name="Structural Load Compliance",
        description="Verify structural elements meet load requirements",
        category=ValidationCategory.REGULATORY,
        severity=ValidationSeverity.ERROR,
        applies_to=["column", "beam", "floor", "roof", "wall", "foundation"],
        parameters={},
        jurisdiction="IBC 2021",
        references=["IBC 2021 Chapter 16", "ASCE 7"],
    ),
    ValidationRule(
        rule_id="reg_ibc_energy_efficiency",
        name="Energy Efficiency",
        description="Verify building envelope meets energy code",
        category=ValidationCategory.REGULATORY,
        severity=ValidationSeverity.WARNING,
        applies_to=["wall", "floor", "roof", "window", "door"],
        parameters={},
        jurisdiction="IECC 2021",
        references=["IECC 2021", "ASHRAE 90.1"],
    ),
    ValidationRule(
        rule_id="reg_ibc_material_standards",
        name="Material Standards",
        description="Verify materials meet referenced standards",
        category=ValidationCategory.REGULATORY,
        severity=ValidationSeverity.WARNING,
        applies_to=["wall", "floor", "column", "beam", "roof", "door", "window"],
        parameters={},
        jurisdiction="IBC 2021",
        references=["IBC 2021 Chapters 14-23"],
    ),
    ValidationRule(
        rule_id="reg_ibc_interior_finish",
        name="Interior Finish Requirements",
        description="Verify interior finishes meet flame spread/smoke development",
        category=ValidationCategory.REGULATORY,
        severity=ValidationSeverity.WARNING,
        applies_to=["wall", "floor", "ceiling"],
        parameters={},
        jurisdiction="IBC 2021",
        references=["IBC 2021 Chapter 8"],
    ),
    ValidationRule(
        rule_id="reg_ibc_plumbing_fixture_count",
        name="Plumbing Fixture Count",
        description="Verify adequate plumbing fixtures for occupancy",
        category=ValidationCategory.REGULATORY,
        severity=ValidationSeverity.WARNING,
        applies_to=["building", "restroom"],
        parameters={},
        jurisdiction="IBC 2021 / IPC 2021",
        references=["IBC 2021 Chapter 29", "IPC 2021 Chapter 4"],
    ),
]


# Built-in correction strategies for regulatory issues
REGULATORY_STRATEGIES = [
    CorrectionStrategy(
        strategy_id="fix_fire_rating",
        rule_id="reg_ibc_fire_resistance",
        name="Upgrade Fire Rating",
        description="Increase fire resistance rating of element",
        auto_applicable=False,
        parameters={"target_rating_hours": 1.0},
        risk_level="medium",
        side_effects=["May require material changes", "Increases cost"],
    ),
    CorrectionStrategy(
        strategy_id="fix_egress_width",
        rule_id="reg_ibc_means_of_egress",
        name="Increase Egress Width",
        description="Widen corridors, doors, or stairs for egress capacity",
        auto_applicable=False,
        parameters={},
        risk_level="high",
        side_effects=["Major layout changes", "Affects floor area"],
    ),
    CorrectionStrategy(
        strategy_id="fix_accessibility",
        rule_id="reg_ibc_accessibility",
        name="Add Accessibility Features",
        description="Add ramps, widen doors, adjust hardware for accessibility",
        auto_applicable=False,
        parameters={},
        risk_level="medium",
        side_effects=["Layout modifications", "Cost increase"],
    ),
    CorrectionStrategy(
        strategy_id="fix_structural_capacity",
        rule_id="reg_ibc_structural_loads",
        name="Increase Structural Capacity",
        description="Increase member sizes or change materials for load compliance",
        auto_applicable=False,
        parameters={},
        risk_level="high",
        side_effects=["Major structural changes", "Requires engineer review"],
    ),
    CorrectionStrategy(
        strategy_id="fix_energy_envelope",
        rule_id="reg_ibc_energy_efficiency",
        name="Improve Energy Envelope",
        description="Add insulation, improve glazing, reduce thermal bridging",
        auto_applicable=False,
        parameters={},
        risk_level="medium",
        side_effects=["Wall/roof thickness changes", "Window specification changes"],
    ),
]


class RegulatoryValidator:
    """Validates building code compliance of architectural elements."""

    def __init__(self, adapter: RhinoAdapter, jurisdiction: str = "IBC 2021") -> None:
        """Initialize the regulatory validator.

        Args:
            adapter: Rhino adapter for executing validation scripts
            jurisdiction: Building code jurisdiction (IBC 2021, local amendments, etc.)
        """
        self._adapter = adapter
        self._jurisdiction = jurisdiction

    async def validate_object(
        self,
        object_id: str,
        element_type: str,
        rules: list[ValidationRule] | None = None,
        project_context: dict[str, Any] | None = None,
    ) -> ValidationResult:
        """Validate a single object against regulatory rules.

        Args:
            object_id: GUID of the Rhino object
            element_type: Type of element
            rules: Optional custom rules
            project_context: Project-level context (occupancy, construction type, etc.)

        Returns:
            ValidationResult with issues found
        """
        import uuid
        result = ValidationResult(
            validation_id=f"val_{uuid.uuid4().hex[:8]}",
            model_id=object_id,
            metadata={"jurisdiction": self._jurisdiction, "project_context": project_context or {}},
        )

        if rules is None:
            rules = [r for r in REGULATORY_RULES if r.matches_element(element_type) and (r.jurisdiction is None or self._jurisdiction in r.jurisdiction)]

        for rule in rules:
            try:
                issues = await self._check_rule(object_id, element_type, rule, project_context)
                for issue in issues:
                    result.add_issue(issue)
            except Exception as e:
                logger.error(f"Rule {rule.rule_id} failed for {object_id}: {e}")
                result.add_issue(ValidationIssue(
                    rule_id=rule.rule_id,
                    category=rule.category,
                    severity=ValidationSeverity.ERROR,
                    message=f"Validation rule execution failed: {e}",
                    element_id=object_id,
                    element_type=element_type,
                ))

        result.status = ValidationStatus.FAILED if result.has_errors() else ValidationStatus.PASSED
        return result

    async def validate_objects(
        self,
        object_ids: list[str],
        element_types: dict[str, str],
        rules: list[ValidationRule] | None = None,
        project_context: dict[str, Any] | None = None,
    ) -> ValidationResult:
        """Validate multiple objects."""
        import uuid
        combined = ValidationResult(
            validation_id=f"val_{uuid.uuid4().hex[:8]}",
            metadata={"jurisdiction": self._jurisdiction, "project_context": project_context or {}},
        )

        for obj_id in object_ids:
            elem_type = element_types.get(obj_id, "unknown")
            obj_result = await self.validate_object(obj_id, elem_type, rules, project_context)
            combined.issues.extend(obj_result.issues)
            combined.passed_count += obj_result.passed_count
            combined.failed_count += obj_result.failed_count
            combined.warning_count += obj_result.warning_count
            combined.info_count += obj_result.info_count

        combined.status = ValidationStatus.FAILED if combined.has_errors() else ValidationStatus.PASSED
        return combined

    async def _check_rule(
        self,
        object_id: str,
        element_type: str,
        rule: ValidationRule,
        project_context: dict[str, Any] | None,
    ) -> list[ValidationIssue]:
        """Execute a single regulatory validation rule."""
        issues = []

        if rule.rule_id == "reg_ibc_occupancy_classification":
            issues.extend(await self._check_occupancy_classification(object_id, element_type, rule, project_context))
        elif rule.rule_id == "reg_ibc_construction_type":
            issues.extend(await self._check_construction_type(object_id, element_type, rule, project_context))
        elif rule.rule_id == "reg_ibc_fire_resistance":
            issues.extend(await self._check_fire_resistance(object_id, element_type, rule, project_context))
        elif rule.rule_id == "reg_ibc_means_of_egress":
            issues.extend(await self._check_means_of_egress(object_id, element_type, rule, project_context))
        elif rule.rule_id == "reg_ibc_accessibility":
            issues.extend(await self._check_accessibility(object_id, element_type, rule, project_context))
        elif rule.rule_id == "reg_ibc_structural_loads":
            issues.extend(await self._check_structural_loads(object_id, element_type, rule, project_context))
        elif rule.rule_id == "reg_ibc_energy_efficiency":
            issues.extend(await self._check_energy_efficiency(object_id, element_type, rule, project_context))
        elif rule.rule_id == "reg_ibc_material_standards":
            issues.extend(await self._check_material_standards(object_id, element_type, rule, project_context))
        elif rule.rule_id == "reg_ibc_interior_finish":
            issues.extend(await self._check_interior_finish(object_id, element_type, rule, project_context))
        elif rule.rule_id == "reg_ibc_plumbing_fixture_count":
            issues.extend(await self._check_plumbing_fixtures(object_id, element_type, rule, project_context))

        return issues

    async def _run_validation_script(self, script: str) -> dict[str, Any]:
        """Run a validation script and parse the result."""
        result = await self._adapter.call_tool("run_python", {"script": script})
        if "content" in result and result["content"]:
            text = result["content"][0].get("text", "{}")
            try:
                outer = json.loads(text)
                stdout = outer.get("stdout", text)
                return json.loads(stdout)
            except json.JSONDecodeError:
                try:
                    return json.loads(text)
                except json.JSONDecodeError:
                    return {}
        return {}

    async def _check_occupancy_classification(
        self,
        object_id: str,
        element_type: str,
        rule: ValidationRule,
        project_context: dict[str, Any] | None,
    ) -> list[ValidationIssue]:
        """Check occupancy classification (project-level)."""
        if not project_context or "occupancy" not in project_context:
            return [ValidationIssue(
                rule_id=rule.rule_id,
                category=rule.category,
                severity=ValidationSeverity.INFO,
                message="Occupancy classification not specified in project context",
                element_id=object_id,
                element_type=element_type,
            )]

        occupancy = project_context["occupancy"]
        allowed = rule.parameters.get("allowed_occupancies", [])

        if occupancy not in allowed:
            return [ValidationIssue(
                rule_id=rule.rule_id,
                category=rule.category,
                severity=rule.severity,
                message=f"Occupancy '{occupancy}' not in allowed list: {allowed}",
                element_id=object_id,
                element_type=element_type,
                expected=allowed,
                actual=occupancy,
            )]
        return []

    async def _check_construction_type(
        self,
        object_id: str,
        element_type: str,
        rule: ValidationRule,
        project_context: dict[str, Any] | None,
    ) -> list[ValidationIssue]:
        """Check construction type (project-level)."""
        if not project_context or "construction_type" not in project_context:
            return [ValidationIssue(
                rule_id=rule.rule_id,
                category=rule.category,
                severity=ValidationSeverity.INFO,
                message="Construction type not specified in project context",
                element_id=object_id,
                element_type=element_type,
            )]

        const_type = project_context["construction_type"]
        allowed = rule.parameters.get("allowed_types", [])

        if const_type not in allowed:
            return [ValidationIssue(
                rule_id=rule.rule_id,
                category=rule.category,
                severity=rule.severity,
                message=f"Construction type '{const_type}' not in allowed list: {allowed}",
                element_id=object_id,
                element_type=element_type,
                expected=allowed,
                actual=const_type,
            )]
        return []

    async def _check_fire_resistance(
        self,
        object_id: str,
        element_type: str,
        rule: ValidationRule,
        project_context: dict[str, Any] | None,
    ) -> list[ValidationIssue]:
        """Check fire resistance rating."""
        # This would require checking element's fire rating property
        # For now, return info that manual verification is needed
        return [ValidationIssue(
            rule_id=rule.rule_id,
            category=rule.category,
            severity=ValidationSeverity.INFO,
            message=f"Fire resistance rating check for {element_type} {object_id} requires material/fire rating data",
            element_id=object_id,
            element_type=element_type,
            metadata={"requires_manual_review": True},
        )]

    async def _check_means_of_egress(
        self,
        object_id: str,
        element_type: str,
        rule: ValidationRule,
        project_context: dict[str, Any] | None,
    ) -> list[ValidationIssue]:
        """Check means of egress compliance."""
        # This requires analyzing the full floor plan
        return [ValidationIssue(
            rule_id=rule.rule_id,
            category=rule.category,
            severity=ValidationSeverity.INFO,
            message=f"Means of egress check for {element_type} {object_id} requires full floor plan analysis",
            element_id=object_id,
            element_type=element_type,
            metadata={"requires_manual_review": True},
        )]

    async def _check_accessibility(
        self,
        object_id: str,
        element_type: str,
        rule: ValidationRule,
        project_context: dict[str, Any] | None,
    ) -> list[ValidationIssue]:
        """Check accessibility compliance."""
        # This would check door widths, hardware, ramp slopes, etc.
        return [ValidationIssue(
            rule_id=rule.rule_id,
            category=rule.category,
            severity=ValidationSeverity.INFO,
            message=f"Accessibility check for {element_type} {object_id} requires detailed geometry analysis",
            element_id=object_id,
            element_type=element_type,
            metadata={"requires_manual_review": True},
        )]

    async def _check_structural_loads(
        self,
        object_id: str,
        element_type: str,
        rule: ValidationRule,
        project_context: dict[str, Any] | None,
    ) -> list[ValidationIssue]:
        """Check structural load compliance."""
        return [ValidationIssue(
            rule_id=rule.rule_id,
            category=rule.category,
            severity=ValidationSeverity.INFO,
            message=f"Structural load check for {element_type} {object_id} requires structural analysis",
            element_id=object_id,
            element_type=element_type,
            metadata={"requires_manual_review": True},
        )]

    async def _check_energy_efficiency(
        self,
        object_id: str,
        element_type: str,
        rule: ValidationRule,
        project_context: dict[str, Any] | None,
    ) -> list[ValidationIssue]:
        """Check energy efficiency compliance."""
        return [ValidationIssue(
            rule_id=rule.rule_id,
            category=rule.category,
            severity=ValidationSeverity.INFO,
            message=f"Energy efficiency check for {element_type} {object_id} requires thermal analysis",
            element_id=object_id,
            element_type=element_type,
            metadata={"requires_manual_review": True},
        )]

    async def _check_material_standards(
        self,
        object_id: str,
        element_type: str,
        rule: ValidationRule,
        project_context: dict[str, Any] | None,
    ) -> list[ValidationIssue]:
        """Check material standards compliance."""
        return [ValidationIssue(
            rule_id=rule.rule_id,
            category=rule.category,
            severity=ValidationSeverity.INFO,
            message=f"Material standards check for {element_type} {object_id} requires material specifications",
            element_id=object_id,
            element_type=element_type,
            metadata={"requires_manual_review": True},
        )]

    async def _check_interior_finish(
        self,
        object_id: str,
        element_type: str,
        rule: ValidationRule,
        project_context: dict[str, Any] | None,
    ) -> list[ValidationIssue]:
        """Check interior finish requirements."""
        return [ValidationIssue(
            rule_id=rule.rule_id,
            category=rule.category,
            severity=ValidationSeverity.INFO,
            message=f"Interior finish check for {element_type} {object_id} requires finish specifications",
            element_id=object_id,
            element_type=element_type,
            metadata={"requires_manual_review": True},
        )]

    async def _check_plumbing_fixtures(
        self,
        object_id: str,
        element_type: str,
        rule: ValidationRule,
        project_context: dict[str, Any] | None,
    ) -> list[ValidationIssue]:
        """Check plumbing fixture count."""
        return [ValidationIssue(
            rule_id=rule.rule_id,
            category=rule.category,
            severity=ValidationSeverity.INFO,
            message=f"Plumbing fixture count check requires occupancy and fixture schedule",
            element_id=object_id,
            element_type=element_type,
            metadata={"requires_manual_review": True},
        )]

    async def apply_correction(
        self,
        strategy: CorrectionStrategy,
        issue: ValidationIssue,
    ) -> CorrectionResult:
        """Apply a regulatory correction strategy."""
        import time
        start = time.time()

        # Most regulatory fixes require manual intervention
        return CorrectionResult(
            strategy_id=strategy.strategy_id,
            issue=issue,
            success=False,
            message=f"Regulatory correction '{strategy.strategy_id}' requires manual design intervention",
            execution_time=time.time() - start,
        )