"""Dimensional validation engine for AI RHINO ARCHITECT.

Implements dimensional constraint checks for architectural elements.
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


# Built-in dimensional validation rules
DIMENSIONAL_RULES = [
    ValidationRule(
        rule_id="dim_wall_height",
        name="Wall Height Range",
        description="Verify wall height is within acceptable range",
        category=ValidationCategory.DIMENSIONAL,
        severity=ValidationSeverity.ERROR,
        applies_to=["wall"],
        parameters={"min_height": 2000, "max_height": 6000},  # mm
        references=["IBC 2021 Section 1208"],
    ),
    ValidationRule(
        rule_id="dim_wall_thickness",
        name="Wall Thickness Range",
        description="Verify wall thickness is within acceptable range",
        category=ValidationCategory.DIMENSIONAL,
        severity=ValidationSeverity.ERROR,
        applies_to=["wall"],
        parameters={"min_thickness": 100, "max_thickness": 500},  # mm
        references=["IBC 2021 Section 1404"],
    ),
    ValidationRule(
        rule_id="dim_floor_thickness",
        name="Floor Slab Thickness",
        description="Verify floor slab thickness meets minimum",
        category=ValidationCategory.DIMENSIONAL,
        severity=ValidationSeverity.ERROR,
        applies_to=["floor"],
        parameters={"min_thickness": 100, "max_thickness": 500},  # mm
        references=["ACI 318"],
    ),
    ValidationRule(
        rule_id="dim_column_size",
        name="Column Cross-Section",
        description="Verify column cross-section meets minimum size",
        category=ValidationCategory.DIMENSIONAL,
        severity=ValidationSeverity.ERROR,
        applies_to=["column"],
        parameters={"min_width": 200, "min_depth": 200, "max_width": 1000, "max_depth": 1000},  # mm
        references=["IBC 2021 Section 1905"],
    ),
    ValidationRule(
        rule_id="dim_beam_depth",
        name="Beam Depth to Span Ratio",
        description="Verify beam depth is appropriate for span",
        category=ValidationCategory.DIMENSIONAL,
        severity=ValidationSeverity.WARNING,
        applies_to=["beam"],
        parameters={"min_depth_to_span_ratio": 0.05, "max_depth_to_span_ratio": 0.25},
        references=["ACI 318 Table 9.5(a)"],
    ),
    ValidationRule(
        rule_id="dim_door_clearance",
        name="Door Clear Opening",
        description="Verify door clear opening meets accessibility requirements",
        category=ValidationCategory.DIMENSIONAL,
        severity=ValidationSeverity.ERROR,
        applies_to=["door"],
        parameters={"min_clear_width": 800, "min_clear_height": 2000},  # mm
        references=["ADA 2010 Section 404", "IBC 2021 Section 1010"],
    ),
    ValidationRule(
        rule_id="dim_window_sill_height",
        name="Window Sill Height",
        description="Verify window sill height meets code requirements",
        category=ValidationCategory.DIMENSIONAL,
        severity=ValidationSeverity.WARNING,
        applies_to=["window"],
        parameters={"max_sill_height": 1100, "min_sill_height": 0},  # mm
        references=["IBC 2021 Section 1030"],
    ),
    ValidationRule(
        rule_id="dim_room_area",
        name="Minimum Room Area",
        description="Verify room meets minimum area requirements",
        category=ValidationCategory.DIMENSIONAL,
        severity=ValidationSeverity.WARNING,
        applies_to=["room", "space"],
        parameters={"min_area": 7000},  # mm^2 (7 m^2)
        references=["IBC 2021 Section 1208"],
    ),
    ValidationRule(
        rule_id="dim_ceiling_height",
        name="Minimum Ceiling Height",
        description="Verify ceiling height meets minimum",
        category=ValidationCategory.DIMENSIONAL,
        severity=ValidationSeverity.ERROR,
        applies_to=["floor", "room", "space"],
        parameters={"min_height": 2400},  # mm
        references=["IBC 2021 Section 1208"],
    ),
    ValidationRule(
        rule_id="dim_stair_dimensions",
        name="Stair Dimensions",
        description="Verify stair riser/tread dimensions meet code",
        category=ValidationCategory.DIMENSIONAL,
        severity=ValidationSeverity.ERROR,
        applies_to=["stair"],
        parameters={"max_riser": 190, "min_tread": 280},  # mm
        references=["IBC 2021 Section 1011"],
    ),
]


# Built-in correction strategies for dimensional issues
DIMENSIONAL_STRATEGIES = [
    CorrectionStrategy(
        strategy_id="fix_wall_height",
        rule_id="dim_wall_height",
        name="Adjust Wall Height",
        description="Scale wall height to meet minimum/maximum",
        auto_applicable=True,
        parameters={"method": "scale_to_bounds"},
        risk_level="low",
        side_effects=["Changes wall height", "May affect connected elements"],
    ),
    CorrectionStrategy(
        strategy_id="fix_wall_thickness",
        rule_id="dim_wall_thickness",
        name="Adjust Wall Thickness",
        description="Scale wall thickness to meet requirements",
        auto_applicable=True,
        parameters={"method": "scale_to_bounds"},
        risk_level="low",
        side_effects=["Changes wall thickness", "May affect floor area calculations"],
    ),
    CorrectionStrategy(
        strategy_id="fix_floor_thickness",
        rule_id="dim_floor_thickness",
        name="Adjust Floor Thickness",
        description="Scale floor slab thickness to meet minimum",
        auto_applicable=True,
        parameters={"method": "scale_to_bounds"},
        risk_level="low",
        side_effects=["Changes floor thickness", "May affect ceiling height"],
    ),
    CorrectionStrategy(
        strategy_id="fix_column_size",
        rule_id="dim_column_size",
        name="Adjust Column Size",
        description="Scale column cross-section to meet minimum",
        auto_applicable=True,
        parameters={"method": "scale_to_bounds"},
        risk_level="medium",
        side_effects=["Changes column size", "May affect structural capacity"],
    ),
    CorrectionStrategy(
        strategy_id="fix_door_clearance",
        rule_id="dim_door_clearance",
        name="Adjust Door Opening",
        description="Resize door opening to meet clear width/height",
        auto_applicable=True,
        parameters={"method": "scale_to_bounds"},
        risk_level="medium",
        side_effects=["Changes door size", "May affect frame and wall opening"],
    ),
]


class DimensionalValidator:
    """Validates dimensional properties of architectural elements."""

    def __init__(self, adapter: RhinoAdapter) -> None:
        """Initialize the dimensional validator.

        Args:
            adapter: Rhino adapter for executing validation scripts
        """
        self._adapter = adapter

    async def validate_object(
        self,
        object_id: str,
        element_type: str,
        rules: list[ValidationRule] | None = None,
    ) -> ValidationResult:
        """Validate a single object against dimensional rules.

        Args:
            object_id: GUID of the Rhino object
            element_type: Type of element
            rules: Optional custom rules

        Returns:
            ValidationResult with issues found
        """
        import uuid
        result = ValidationResult(
            validation_id=f"val_{uuid.uuid4().hex[:8]}",
            model_id=object_id,
        )

        if rules is None:
            rules = [r for r in DIMENSIONAL_RULES if r.matches_element(element_type)]

        for rule in rules:
            try:
                issues = await self._check_rule(object_id, element_type, rule)
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
    ) -> ValidationResult:
        """Validate multiple objects."""
        import uuid
        combined = ValidationResult(
            validation_id=f"val_{uuid.uuid4().hex[:8]}",
        )

        for obj_id in object_ids:
            elem_type = element_types.get(obj_id, "unknown")
            obj_result = await self.validate_object(obj_id, elem_type, rules)
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
    ) -> list[ValidationIssue]:
        """Execute a single dimensional validation rule."""
        issues = []

        if rule.rule_id == "dim_wall_height":
            issues.extend(await self._check_wall_height(object_id, element_type, rule))
        elif rule.rule_id == "dim_wall_thickness":
            issues.extend(await self._check_wall_thickness(object_id, element_type, rule))
        elif rule.rule_id == "dim_floor_thickness":
            issues.extend(await self._check_floor_thickness(object_id, element_type, rule))
        elif rule.rule_id == "dim_column_size":
            issues.extend(await self._check_column_size(object_id, element_type, rule))
        elif rule.rule_id == "dim_beam_depth":
            issues.extend(await self._check_beam_depth(object_id, element_type, rule))
        elif rule.rule_id == "dim_door_clearance":
            issues.extend(await self._check_door_clearance(object_id, element_type, rule))
        elif rule.rule_id == "dim_window_sill_height":
            issues.extend(await self._check_window_sill_height(object_id, element_type, rule))
        elif rule.rule_id == "dim_room_area":
            issues.extend(await self._check_room_area(object_id, element_type, rule))
        elif rule.rule_id == "dim_ceiling_height":
            issues.extend(await self._check_ceiling_height(object_id, element_type, rule))
        elif rule.rule_id == "dim_stair_dimensions":
            issues.extend(await self._check_stair_dimensions(object_id, element_type, rule))

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

    async def _get_bounding_box(self, object_id: str) -> dict[str, Any] | None:
        """Get bounding box of an object."""
        script = f"""
import json
import rhinoscriptsyntax as rs
obj = rs.coercegeometry("{object_id}")
if obj:
    bbox = obj.GetBoundingBox(True)
    min_pt = bbox.Min
    max_pt = bbox.Max
    print(json.dumps({{
        "min": [min_pt.X, min_pt.Y, min_pt.Z],
        "max": [max_pt.X, max_pt.Y, max_pt.Z],
        "width": max_pt.X - min_pt.X,
        "depth": max_pt.Y - min_pt.Y,
        "height": max_pt.Z - min_pt.Z
    }}))
else:
    print(json.dumps({{"error": "Object not found"}}))
"""
        return await self._run_validation_script(script)

    async def _check_wall_height(
        self,
        object_id: str,
        element_type: str,
        rule: ValidationRule,
    ) -> list[ValidationIssue]:
        """Check wall height."""
        bbox = await self._get_bounding_box(object_id)
        if not bbox or "error" in bbox:
            return [ValidationIssue(
                rule_id=rule.rule_id,
                category=rule.category,
                severity=rule.severity,
                message=f"Could not get bounding box for {object_id}",
                element_id=object_id,
                element_type=element_type,
            )]

        height = bbox.get("height", 0)
        min_h = rule.parameters.get("min_height", 2000)
        max_h = rule.parameters.get("max_height", 6000)

        issues = []
        if height < min_h:
            issues.append(ValidationIssue(
                rule_id=rule.rule_id,
                category=rule.category,
                severity=rule.severity,
                message=f"Wall height {height}mm below minimum {min_h}mm",
                element_id=object_id,
                element_type=element_type,
                expected=f">= {min_h}",
                actual=height,
            ))
        elif height > max_h:
            issues.append(ValidationIssue(
                rule_id=rule.rule_id,
                category=rule.category,
                severity=rule.severity,
                message=f"Wall height {height}mm exceeds maximum {max_h}mm",
                element_id=object_id,
                element_type=element_type,
                expected=f"<= {max_h}",
                actual=height,
            ))
        return issues

    async def _check_wall_thickness(
        self,
        object_id: str,
        element_type: str,
        rule: ValidationRule,
    ) -> list[ValidationIssue]:
        """Check wall thickness."""
        bbox = await self._get_bounding_box(object_id)
        if not bbox or "error" in bbox:
            return [ValidationIssue(
                rule_id=rule.rule_id,
                category=rule.category,
                severity=rule.severity,
                message=f"Could not get bounding box for {object_id}",
                element_id=object_id,
                element_type=element_type,
            )]

        # Thickness is the smaller of width/depth for a wall
        width = bbox.get("width", 0)
        depth = bbox.get("depth", 0)
        thickness = min(width, depth)

        min_t = rule.parameters.get("min_thickness", 100)
        max_t = rule.parameters.get("max_thickness", 500)

        issues = []
        if thickness < min_t:
            issues.append(ValidationIssue(
                rule_id=rule.rule_id,
                category=rule.category,
                severity=rule.severity,
                message=f"Wall thickness {thickness}mm below minimum {min_t}mm",
                element_id=object_id,
                element_type=element_type,
                expected=f">= {min_t}",
                actual=thickness,
            ))
        elif thickness > max_t:
            issues.append(ValidationIssue(
                rule_id=rule.rule_id,
                category=rule.category,
                severity=rule.severity,
                message=f"Wall thickness {thickness}mm exceeds maximum {max_t}mm",
                element_id=object_id,
                element_type=element_type,
                expected=f"<= {max_t}",
                actual=thickness,
            ))
        return issues

    async def _check_floor_thickness(
        self,
        object_id: str,
        element_type: str,
        rule: ValidationRule,
    ) -> list[ValidationIssue]:
        """Check floor slab thickness."""
        bbox = await self._get_bounding_box(object_id)
        if not bbox or "error" in bbox:
            return [ValidationIssue(
                rule_id=rule.rule_id,
                category=rule.category,
                severity=rule.severity,
                message=f"Could not get bounding box for {object_id}",
                element_id=object_id,
                element_type=element_type,
            )]

        thickness = bbox.get("height", 0)  # Height is thickness for horizontal slab
        min_t = rule.parameters.get("min_thickness", 100)
        max_t = rule.parameters.get("max_thickness", 500)

        issues = []
        if thickness < min_t:
            issues.append(ValidationIssue(
                rule_id=rule.rule_id,
                category=rule.category,
                severity=rule.severity,
                message=f"Floor thickness {thickness}mm below minimum {min_t}mm",
                element_id=object_id,
                element_type=element_type,
                expected=f">= {min_t}",
                actual=thickness,
            ))
        elif thickness > max_t:
            issues.append(ValidationIssue(
                rule_id=rule.rule_id,
                category=rule.category,
                severity=rule.severity,
                message=f"Floor thickness {thickness}mm exceeds maximum {max_t}mm",
                element_id=object_id,
                element_type=element_type,
                expected=f"<= {max_t}",
                actual=thickness,
            ))
        return issues

    async def _check_column_size(
        self,
        object_id: str,
        element_type: str,
        rule: ValidationRule,
    ) -> list[ValidationIssue]:
        """Check column cross-section size."""
        bbox = await self._get_bounding_box(object_id)
        if not bbox or "error" in bbox:
            return [ValidationIssue(
                rule_id=rule.rule_id,
                category=rule.category,
                severity=rule.severity,
                message=f"Could not get bounding box for {object_id}",
                element_id=object_id,
                element_type=element_type,
            )]

        width = bbox.get("width", 0)
        depth = bbox.get("depth", 0)

        min_w = rule.parameters.get("min_width", 200)
        min_d = rule.parameters.get("min_depth", 200)
        max_w = rule.parameters.get("max_width", 1000)
        max_d = rule.parameters.get("max_depth", 1000)

        issues = []
        if width < min_w:
            issues.append(ValidationIssue(
                rule_id=rule.rule_id,
                category=rule.category,
                severity=rule.severity,
                message=f"Column width {width}mm below minimum {min_w}mm",
                element_id=object_id,
                element_type=element_type,
                expected=f">= {min_w}",
                actual=width,
            ))
        if depth < min_d:
            issues.append(ValidationIssue(
                rule_id=rule.rule_id,
                category=rule.category,
                severity=rule.severity,
                message=f"Column depth {depth}mm below minimum {min_d}mm",
                element_id=object_id,
                element_type=element_type,
                expected=f">= {min_d}",
                actual=depth,
            ))
        if width > max_w:
            issues.append(ValidationIssue(
                rule_id=rule.rule_id,
                category=rule.category,
                severity=rule.severity,
                message=f"Column width {width}mm exceeds maximum {max_w}mm",
                element_id=object_id,
                element_type=element_type,
                expected=f"<= {max_w}",
                actual=width,
            ))
        if depth > max_d:
            issues.append(ValidationIssue(
                rule_id=rule.rule_id,
                category=rule.category,
                severity=rule.severity,
                message=f"Column depth {depth}mm exceeds maximum {max_d}mm",
                element_id=object_id,
                element_type=element_type,
                expected=f"<= {max_d}",
                actual=depth,
            ))
        return issues

    async def _check_beam_depth(
        self,
        object_id: str,
        element_type: str,
        rule: ValidationRule,
    ) -> list[ValidationIssue]:
        """Check beam depth to span ratio."""
        bbox = await self._get_bounding_box(object_id)
        if not bbox or "error" in bbox:
            return [ValidationIssue(
                rule_id=rule.rule_id,
                category=rule.category,
                severity=rule.severity,
                message=f"Could not get bounding box for {object_id}",
                element_id=object_id,
                element_type=element_type,
            )]

        # For beam: span is the longest dimension, depth is the vertical dimension
        width = bbox.get("width", 0)
        depth = bbox.get("depth", 0)
        height = bbox.get("height", 0)

        span = max(width, depth)  # Horizontal span
        beam_depth = height  # Vertical depth

        if span <= 0:
            return [ValidationIssue(
                rule_id=rule.rule_id,
                category=rule.category,
                severity=rule.severity,
                message=f"Beam {object_id} has zero span",
                element_id=object_id,
                element_type=element_type,
            )]

        ratio = beam_depth / span
        min_ratio = rule.parameters.get("min_depth_to_span_ratio", 0.05)
        max_ratio = rule.parameters.get("max_depth_to_span_ratio", 0.25)

        issues = []
        if ratio < min_ratio:
            issues.append(ValidationIssue(
                rule_id=rule.rule_id,
                category=rule.category,
                severity=rule.severity,
                message=f"Beam depth/span ratio {ratio:.3f} below minimum {min_ratio}",
                element_id=object_id,
                element_type=element_type,
                expected=f">= {min_ratio}",
                actual=ratio,
            ))
        elif ratio > max_ratio:
            issues.append(ValidationIssue(
                rule_id=rule.rule_id,
                category=rule.category,
                severity=rule.severity,
                message=f"Beam depth/span ratio {ratio:.3f} exceeds maximum {max_ratio}",
                element_id=object_id,
                element_type=element_type,
                expected=f"<= {max_ratio}",
                actual=ratio,
            ))
        return issues

    async def _check_door_clearance(
        self,
        object_id: str,
        element_type: str,
        rule: ValidationRule,
    ) -> list[ValidationIssue]:
        """Check door clear opening."""
        bbox = await self._get_bounding_box(object_id)
        if not bbox or "error" in bbox:
            return [ValidationIssue(
                rule_id=rule.rule_id,
                category=rule.category,
                severity=rule.severity,
                message=f"Could not get bounding box for {object_id}",
                element_id=object_id,
                element_type=element_type,
            )]

        width = bbox.get("width", 0)
        height = bbox.get("height", 0)

        min_w = rule.parameters.get("min_clear_width", 800)
        min_h = rule.parameters.get("min_clear_height", 2000)

        issues = []
        if width < min_w:
            issues.append(ValidationIssue(
                rule_id=rule.rule_id,
                category=rule.category,
                severity=rule.severity,
                message=f"Door clear width {width}mm below minimum {min_w}mm",
                element_id=object_id,
                element_type=element_type,
                expected=f">= {min_w}",
                actual=width,
            ))
        if height < min_h:
            issues.append(ValidationIssue(
                rule_id=rule.rule_id,
                category=rule.category,
                severity=rule.severity,
                message=f"Door clear height {height}mm below minimum {min_h}mm",
                element_id=object_id,
                element_type=element_type,
                expected=f">= {min_h}",
                actual=height,
            ))
        return issues

    async def _check_window_sill_height(
        self,
        object_id: str,
        element_type: str,
        rule: ValidationRule,
    ) -> list[ValidationIssue]:
        """Check window sill height."""
        bbox = await self._get_bounding_box(object_id)
        if not bbox or "error" in bbox:
            return [ValidationIssue(
                rule_id=rule.rule_id,
                category=rule.category,
                severity=rule.severity,
                message=f"Could not get bounding box for {object_id}",
                element_id=object_id,
                element_type=element_type,
            )]

        # Sill height is the Z coordinate of the bottom of the window
        min_z = bbox.get("min", [0, 0, 0])[2]
        max_sill = rule.parameters.get("max_sill_height", 1100)
        min_sill = rule.parameters.get("min_sill_height", 0)

        issues = []
        if min_z > max_sill:
            issues.append(ValidationIssue(
                rule_id=rule.rule_id,
                category=rule.category,
                severity=rule.severity,
                message=f"Window sill height {min_z}mm exceeds maximum {max_sill}mm",
                element_id=object_id,
                element_type=element_type,
                expected=f"<= {max_sill}",
                actual=min_z,
            ))
        if min_z < min_sill:
            issues.append(ValidationIssue(
                rule_id=rule.rule_id,
                category=rule.category,
                severity=rule.severity,
                message=f"Window sill height {min_z}mm below minimum {min_sill}mm",
                element_id=object_id,
                element_type=element_type,
                expected=f">= {min_sill}",
                actual=min_z,
            ))
        return issues

    async def _check_room_area(
        self,
        object_id: str,
        element_type: str,
        rule: ValidationRule,
    ) -> list[ValidationIssue]:
        """Check room floor area."""
        script = f"""
import json
import rhinoscriptsyntax as rs
import Rhino.Geometry as rg
obj = rs.coercebrep("{object_id}")
if obj:
    # Get floor area from bottom face
    area = 0
    for face in obj.Faces:
        if face.Normal.Z < -0.9:  # Horizontal downward face
            area += face.GetArea()
    print(json.dumps({{"area": area}}))
else:
    print(json.dumps({{"area": 0, "error": "Not a Brep"}}))
"""
        data = await self._run_validation_script(script)
        area = data.get("area", 0)
        min_area = rule.parameters.get("min_area", 7000)

        issues = []
        if area < min_area:
            issues.append(ValidationIssue(
                rule_id=rule.rule_id,
                category=rule.category,
                severity=rule.severity,
                message=f"Room area {area:.0f}mm² below minimum {min_area}mm²",
                element_id=object_id,
                element_type=element_type,
                expected=f">= {min_area}",
                actual=area,
            ))
        return issues

    async def _check_ceiling_height(
        self,
        object_id: str,
        element_type: str,
        rule: ValidationRule,
    ) -> list[ValidationIssue]:
        """Check ceiling height (floor to ceiling)."""
        bbox = await self._get_bounding_box(object_id)
        if not bbox or "error" in bbox:
            return [ValidationIssue(
                rule_id=rule.rule_id,
                category=rule.category,
                severity=rule.severity,
                message=f"Could not get bounding box for {object_id}",
                element_id=object_id,
                element_type=element_type,
            )]

        height = bbox.get("height", 0)
        min_h = rule.parameters.get("min_height", 2400)

        issues = []
        if height < min_h:
            issues.append(ValidationIssue(
                rule_id=rule.rule_id,
                category=rule.category,
                severity=rule.severity,
                message=f"Ceiling height {height}mm below minimum {min_h}mm",
                element_id=object_id,
                element_type=element_type,
                expected=f">= {min_h}",
                actual=height,
            ))
        return issues

    async def _check_stair_dimensions(
        self,
        object_id: str,
        element_type: str,
        rule: ValidationRule,
    ) -> list[ValidationIssue]:
        """Check stair riser/tread dimensions."""
        # This would require analyzing stair geometry specifically
        # For now, return a warning that manual check is needed
        return [ValidationIssue(
            rule_id=rule.rule_id,
            category=rule.category,
            severity=ValidationSeverity.INFO,
            message=f"Stair dimension check requires detailed geometry analysis for {object_id}",
            element_id=object_id,
            element_type=element_type,
        )]

    async def apply_correction(
        self,
        strategy: CorrectionStrategy,
        issue: ValidationIssue,
    ) -> CorrectionResult:
        """Apply a dimensional correction strategy."""
        import time
        start = time.time()

        if strategy.strategy_id in ["fix_wall_height", "fix_wall_thickness", "fix_floor_thickness",
                                     "fix_column_size", "fix_door_clearance"]:
            return await self._apply_scale_to_bounds(strategy, issue)

        return CorrectionResult(
            strategy_id=strategy.strategy_id,
            issue=issue,
            success=False,
            message=f"Unknown strategy: {strategy.strategy_id}",
            execution_time=time.time() - start,
        )

    async def _apply_scale_to_bounds(
        self,
        strategy: CorrectionStrategy,
        issue: ValidationIssue,
    ) -> CorrectionResult:
        """Scale element to meet dimensional bounds."""
        import time
        start = time.time()

        # Get the rule to know bounds
        rule_id = strategy.rule_id
        rule = next((r for r in DIMENSIONAL_RULES if r.rule_id == rule_id), None)
        if not rule:
            return CorrectionResult(
                strategy_id=strategy.strategy_id,
                issue=issue,
                success=False,
                message=f"Rule {rule_id} not found",
                execution_time=time.time() - start,
            )

        # Determine target value
        target = None
        if "min_" in str(issue.expected):
            target = float(str(issue.expected).replace(">= ", ""))
        elif "max_" in str(issue.expected) or "<=" in str(issue.expected):
            target = float(str(issue.expected).replace("<= ", ""))

        if target is None:
            return CorrectionResult(
                strategy_id=strategy.strategy_id,
                issue=issue,
                success=False,
                message="Could not determine target value",
                execution_time=time.time() - start,
            )

        # Scale the object
        script = f"""
import json
import rhinoscriptsyntax as rs
obj = rs.coercegeometry("{issue.element_id}")
if obj:
    # Get current bounding box
    bbox = obj.GetBoundingBox(True)
    # Scale factor would need to be computed based on which dimension to change
    # This is simplified - in production would need more sophisticated logic
    print(json.dumps({{"success": false, "error": "Scale to bounds requires specific dimension targeting"}}))
else:
    print(json.dumps({{"success": false, "error": "Object not found"}}))
"""
        data = await self._run_validation_script(script)
        success = data.get("success", False)

        return CorrectionResult(
            strategy_id=strategy.strategy_id,
            issue=issue,
            success=success,
            message="Scaled to bounds" if success else data.get("error", "Scaling not implemented"),
            execution_time=time.time() - start,
        )