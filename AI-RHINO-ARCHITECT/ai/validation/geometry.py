"""Geometry validation engine for AI RHINO ARCHITECT.

Implements geometric validity checks using RhinoCommon via run_python.
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


# Built-in geometry validation rules
GEOMETRY_RULES = [
    ValidationRule(
        rule_id="geom_closed_solid",
        name="Closed Solid Check",
        description="Verify that Breps are closed solids (watertight)",
        category=ValidationCategory.GEOMETRY,
        severity=ValidationSeverity.ERROR,
        applies_to=["wall", "floor", "column", "beam", "roof", "door", "window"],
        parameters={"tolerance": 0.001},
        references=["RhinoCommon Brep.IsSolid"],
    ),
    ValidationRule(
        rule_id="geom_manifold",
        name="Manifold Geometry Check",
        description="Verify that Breps are manifold (each edge has exactly 2 faces)",
        category=ValidationCategory.GEOMETRY,
        severity=ValidationSeverity.ERROR,
        applies_to=["wall", "floor", "column", "beam", "roof", "door", "window"],
        parameters={},
        references=["RhinoCommon Brep.IsManifold"],
    ),
    ValidationRule(
        rule_id="geom_valid_brep",
        name="Valid Brep Check",
        description="Verify that Breps are valid (no self-intersections, proper orientation)",
        category=ValidationCategory.GEOMETRY,
        severity=ValidationSeverity.ERROR,
        applies_to=["wall", "floor", "column", "beam", "roof", "door", "window", "surface"],
        parameters={},
        references=["RhinoCommon Brep.IsValid"],
    ),
    ValidationRule(
        rule_id="geom_positive_volume",
        name="Positive Volume Check",
        description="Verify that solid elements have positive volume",
        category=ValidationCategory.GEOMETRY,
        severity=ValidationSeverity.ERROR,
        applies_to=["wall", "floor", "column", "beam", "roof"],
        parameters={"min_volume": 1.0},
        references=[],
    ),
    ValidationRule(
        rule_id="geom_no_naked_edges",
        name="No Naked Edges Check",
        description="Verify that solid Breps have no naked edges (for closed solids)",
        category=ValidationCategory.GEOMETRY,
        severity=ValidationSeverity.WARNING,
        applies_to=["wall", "floor", "column", "beam", "roof"],
        parameters={},
        references=["RhinoCommon Brep.NakedEdges"],
    ),
    ValidationRule(
        rule_id="geom_no_non_manifold_edges",
        name="No Non-Manifold Edges Check",
        description="Verify that Breps have no non-manifold edges",
        category=ValidationCategory.GEOMETRY,
        severity=ValidationSeverity.ERROR,
        applies_to=["wall", "floor", "column", "beam", "roof"],
        parameters={},
        references=["RhinoCommon Brep.NonManifoldEdges"],
    ),
]


# Built-in correction strategies for geometry issues
GEOMETRY_STRATEGIES = [
    CorrectionStrategy(
        strategy_id="fix_cap_brep",
        rule_id="geom_closed_solid",
        name="Cap Open Brep",
        description="Attempt to cap open Brep to make it a closed solid",
        auto_applicable=True,
        parameters={"tolerance": 0.01},
        risk_level="low",
        side_effects=["May change geometry slightly", "May not work for complex openings"],
    ),
    CorrectionStrategy(
        strategy_id="fix_join_surfaces",
        rule_id="geom_closed_solid",
        name="Join Surfaces to Form Solid",
        description="Join adjacent surfaces to create a closed Brep",
        auto_applicable=True,
        parameters={"tolerance": 0.01},
        risk_level="low",
        side_effects=["Requires surfaces to share edges"],
    ),
    CorrectionStrategy(
        strategy_id="fix_boolean_union",
        rule_id="geom_closed_solid",
        name="Boolean Union Components",
        description="Perform boolean union on overlapping components",
        auto_applicable=True,
        parameters={},
        risk_level="medium",
        side_effects=["May merge separate elements", "Can fail on complex geometry"],
    ),
    CorrectionStrategy(
        strategy_id="fix_rebuild_edges",
        rule_id="geom_manifold",
        name="Rebuild Problematic Edges",
        description="Rebuild edges that cause non-manifold conditions",
        auto_applicable=False,
        parameters={},
        risk_level="high",
        side_effects=["Significant geometry modification", "May change design intent"],
    ),
]


class GeometryValidator:
    """Validates geometric properties of Rhino objects."""

    def __init__(self, adapter: RhinoAdapter) -> None:
        """Initialize the geometry validator.

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
        """Validate a single Rhino object against geometry rules.

        Args:
            object_id: GUID of the Rhino object to validate
            element_type: Type of element (wall, floor, etc.)
            rules: Optional custom rules (uses built-in if not provided)

        Returns:
            ValidationResult with issues found
        """
        import uuid
        result = ValidationResult(
            validation_id=f"val_{uuid.uuid4().hex[:8]}",
            model_id=object_id,
        )

        if rules is None:
            rules = [r for r in GEOMETRY_RULES if r.matches_element(element_type)]

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
        """Validate multiple Rhino objects.

        Args:
            object_ids: List of GUIDs to validate
            element_types: Mapping of object_id -> element_type
            rules: Optional custom rules

        Returns:
            Combined ValidationResult
        """
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
        """Execute a single validation rule."""
        issues = []

        if rule.rule_id == "geom_closed_solid":
            issues.extend(await self._check_closed_solid(object_id, element_type, rule))
        elif rule.rule_id == "geom_manifold":
            issues.extend(await self._check_manifold(object_id, element_type, rule))
        elif rule.rule_id == "geom_valid_brep":
            issues.extend(await self._check_valid_brep(object_id, element_type, rule))
        elif rule.rule_id == "geom_positive_volume":
            issues.extend(await self._check_positive_volume(object_id, element_type, rule))
        elif rule.rule_id == "geom_no_naked_edges":
            issues.extend(await self._check_naked_edges(object_id, element_type, rule))
        elif rule.rule_id == "geom_no_non_manifold_edges":
            issues.extend(await self._check_non_manifold_edges(object_id, element_type, rule))

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

    async def _check_closed_solid(
        self,
        object_id: str,
        element_type: str,
        rule: ValidationRule,
    ) -> list[ValidationIssue]:
        """Check if Brep is a closed solid."""
        script = f"""
import json
import rhinoscriptsyntax as rs
obj = rs.coercebrep("{object_id}")
if obj:
    is_solid = obj.IsSolid
    print(json.dumps({{"is_solid": is_solid}}))
else:
    print(json.dumps({{"is_solid": false, "error": "Not a Brep"}}))
"""
        data = await self._run_validation_script(script)
        is_solid = data.get("is_solid", False)

        if not is_solid:
            return [ValidationIssue(
                rule_id=rule.rule_id,
                category=rule.category,
                severity=rule.severity,
                message=f"{element_type} {object_id} is not a closed solid",
                element_id=object_id,
                element_type=element_type,
                expected=True,
                actual=False,
            )]
        return []

    async def _check_manifold(
        self,
        object_id: str,
        element_type: str,
        rule: ValidationRule,
    ) -> list[ValidationIssue]:
        """Check if Brep is manifold."""
        script = f"""
import json
import rhinoscriptsyntax as rs
obj = rs.coercebrep("{object_id}")
if obj:
    is_manifold = obj.IsManifold
    print(json.dumps({{"is_manifold": is_manifold}}))
else:
    print(json.dumps({{"is_manifold": false, "error": "Not a Brep"}}))
"""
        data = await self._run_validation_script(script)
        is_manifold = data.get("is_manifold", False)

        if not is_manifold:
            return [ValidationIssue(
                rule_id=rule.rule_id,
                category=rule.category,
                severity=rule.severity,
                message=f"{element_type} {object_id} is not manifold",
                element_id=object_id,
                element_type=element_type,
                expected=True,
                actual=False,
            )]
        return []

    async def _check_valid_brep(
        self,
        object_id: str,
        element_type: str,
        rule: ValidationRule,
    ) -> list[ValidationIssue]:
        """Check if Brep is valid."""
        script = f"""
import json
import rhinoscriptsyntax as rs
obj = rs.coercebrep("{object_id}")
if obj:
    is_valid = obj.IsValid
    print(json.dumps({{"is_valid": is_valid}}))
else:
    print(json.dumps({{"is_valid": false, "error": "Not a Brep"}}))
"""
        data = await self._run_validation_script(script)
        is_valid = data.get("is_valid", False)

        if not is_valid:
            return [ValidationIssue(
                rule_id=rule.rule_id,
                category=rule.category,
                severity=rule.severity,
                message=f"{element_type} {object_id} is not a valid Brep",
                element_id=object_id,
                element_type=element_type,
                expected=True,
                actual=False,
            )]
        return []

    async def _check_positive_volume(
        self,
        object_id: str,
        element_type: str,
        rule: ValidationRule,
    ) -> list[ValidationIssue]:
        """Check if solid has positive volume."""
        min_volume = rule.parameters.get("min_volume", 1.0)
        script = f"""
import json
import rhinoscriptsyntax as rs
obj = rs.coercebrep("{object_id}")
if obj and obj.IsSolid:
    props = obj.GetVolume()
    volume = props[1] if props[0] else 0
    print(json.dumps({{"volume": volume}}))
else:
    print(json.dumps({{"volume": 0, "error": "Not a solid Brep"}}))
"""
        data = await self._run_validation_script(script)
        volume = data.get("volume", 0)

        if volume < min_volume:
            return [ValidationIssue(
                rule_id=rule.rule_id,
                category=rule.category,
                severity=rule.severity,
                message=f"{element_type} {object_id} has insufficient volume: {volume} < {min_volume}",
                element_id=object_id,
                element_type=element_type,
                expected=f">= {min_volume}",
                actual=volume,
            )]
        return []

    async def _check_naked_edges(
        self,
        object_id: str,
        element_type: str,
        rule: ValidationRule,
    ) -> list[ValidationIssue]:
        """Check for naked edges."""
        script = f"""
import json
import rhinoscriptsyntax as rs
obj = rs.coercebrep("{object_id}")
if obj:
    naked = obj.NakedEdges
    count = len(naked) if naked else 0
    print(json.dumps({{"naked_edge_count": count}}))
else:
    print(json.dumps({{"naked_edge_count": 0, "error": "Not a Brep"}}))
"""
        data = await self._run_validation_script(script)
        count = data.get("naked_edge_count", 0)

        if count > 0:
            return [ValidationIssue(
                rule_id=rule.rule_id,
                category=rule.category,
                severity=rule.severity,
                message=f"{element_type} {object_id} has {count} naked edges",
                element_id=object_id,
                element_type=element_type,
                expected=0,
                actual=count,
            )]
        return []

    async def _check_non_manifold_edges(
        self,
        object_id: str,
        element_type: str,
        rule: ValidationRule,
    ) -> list[ValidationIssue]:
        """Check for non-manifold edges."""
        script = f"""
import json
import rhinoscriptsyntax as rs
obj = rs.coercebrep("{object_id}")
if obj:
    non_manifold = obj.NonManifoldEdges
    count = len(non_manifold) if non_manifold else 0
    print(json.dumps({{"non_manifold_edge_count": count}}))
else:
    print(json.dumps({{"non_manifold_edge_count": 0, "error": "Not a Brep"}}))
"""
        data = await self._run_validation_script(script)
        count = data.get("non_manifold_edge_count", 0)

        if count > 0:
            return [ValidationIssue(
                rule_id=rule.rule_id,
                category=rule.category,
                severity=rule.severity,
                message=f"{element_type} {object_id} has {count} non-manifold edges",
                element_id=object_id,
                element_type=element_type,
                expected=0,
                actual=count,
            )]
        return []

    async def apply_correction(
        self,
        strategy: CorrectionStrategy,
        issue: ValidationIssue,
    ) -> CorrectionResult:
        """Apply a correction strategy to fix an issue."""
        import time
        start = time.time()

        if strategy.strategy_id == "fix_cap_brep":
            return await self._apply_cap_brep(strategy, issue)
        elif strategy.strategy_id == "fix_join_surfaces":
            return await self._apply_join_surfaces(strategy, issue)
        elif strategy.strategy_id == "fix_boolean_union":
            return await self._apply_boolean_union(strategy, issue)
        elif strategy.strategy_id == "fix_rebuild_edges":
            return await self._apply_rebuild_edges(strategy, issue)

        return CorrectionResult(
            strategy_id=strategy.strategy_id,
            issue=issue,
            success=False,
            message=f"Unknown strategy: {strategy.strategy_id}",
            execution_time=time.time() - start,
        )

    async def _apply_cap_brep(
        self,
        strategy: CorrectionStrategy,
        issue: ValidationIssue,
    ) -> CorrectionResult:
        """Cap an open Brep to make it solid."""
        import time
        start = time.time()
        tolerance = strategy.parameters.get("tolerance", 0.01)

        script = f"""
import json
import rhinoscriptsyntax as rs
import Rhino.Geometry as rg
obj = rs.coercebrep("{issue.element_id}")
if obj:
    capped = rg.Brep.CapPlanarHoles(obj, {tolerance})
    if capped:
        guids = [rs.AddBrep(b) for b in capped]
        print(json.dumps({{"success": true, "guids": [str(g) for g in guids]}}))
    else:
        print(json.dumps({{"success": false, "error": "Cap failed"}}))
else:
    print(json.dumps({{"success": false, "error": "Not a Brep"}}))
"""
        data = await self._run_validation_script(script)
        success = data.get("success", False)
        guids = data.get("guids", [])

        return CorrectionResult(
            strategy_id=strategy.strategy_id,
            issue=issue,
            success=success,
            message="Capped Brep successfully" if success else data.get("error", "Cap failed"),
            modified_elements=guids,
            execution_time=time.time() - start,
        )

    async def _apply_join_surfaces(
        self,
        strategy: CorrectionStrategy,
        issue: ValidationIssue,
    ) -> CorrectionResult:
        """Join surfaces to form a solid."""
        import time
        start = time.time()
        tolerance = strategy.parameters.get("tolerance", 0.01)

        script = f"""
import json
import rhinoscriptsyntax as rs
# Get all surfaces in document that might be related
# For now, try to join the object with nearby surfaces
obj = rs.coercebrep("{issue.element_id}")
if obj:
    # Get adjacent surfaces (simplified)
    joined = rs.JoinSurfaces([obj], {tolerance})
    if joined:
        guids = [rs.AddBrep(b) for b in joined]
        print(json.dumps({{"success": true, "guids": [str(g) for g in guids]}}))
    else:
        print(json.dumps({{"success": false, "error": "Join failed"}}))
else:
    print(json.dumps({{"success": false, "error": "Not a Brep"}}))
"""
        data = await self._run_validation_script(script)
        success = data.get("success", False)
        guids = data.get("guids", [])

        return CorrectionResult(
            strategy_id=strategy.strategy_id,
            issue=issue,
            success=success,
            message="Joined surfaces successfully" if success else data.get("error", "Join failed"),
            modified_elements=guids,
            execution_time=time.time() - start,
        )

    async def _apply_boolean_union(
        self,
        strategy: CorrectionStrategy,
        issue: ValidationIssue,
    ) -> CorrectionResult:
        """Boolean union overlapping components."""
        import time
        start = time.time()

        script = f"""
import json
import rhinoscriptsyntax as rs
import Rhino.Geometry as rg
obj = rs.coercebrep("{issue.element_id}")
if obj:
    # Find overlapping breps (simplified - would need spatial query in production)
    all_breps = rs.ObjectsByType(16)  # Brep type
    overlapping = []
    for b_id in all_breps:
        if str(b_id) == "{issue.element_id}":
            continue
        other = rs.coercebrep(str(b_id))
        if other:
            # Check bounding box intersection
            if obj.GetBoundingBox(True).Intersects(other.GetBoundingBox(True)):
                overlapping.append(other)
    
    if overlapping:
        result = rg.Brep.CreateBooleanUnion([obj] + overlapping)
        if result:
            guids = [rs.AddBrep(b) for b in result]
            print(json.dumps({{"success": true, "guids": [str(g) for g in guids]}}))
        else:
            print(json.dumps({{"success": false, "error": "Boolean union failed"}}))
    else:
        print(json.dumps({{"success": false, "error": "No overlapping breps found"}}))
else:
    print(json.dumps({{"success": false, "error": "Not a Brep"}}))
"""
        data = await self._run_validation_script(script)
        success = data.get("success", False)
        guids = data.get("guids", [])

        return CorrectionResult(
            strategy_id=strategy.strategy_id,
            issue=issue,
            success=success,
            message="Boolean union successful" if success else data.get("error", "Union failed"),
            modified_elements=guids,
            execution_time=time.time() - start,
        )

    async def _apply_rebuild_edges(
        self,
        strategy: CorrectionStrategy,
        issue: ValidationIssue,
    ) -> CorrectionResult:
        """Rebuild problematic edges (manual intervention needed)."""
        import time
        return CorrectionResult(
            strategy_id=strategy.strategy_id,
            issue=issue,
            success=False,
            message="Non-manifold edge repair requires manual intervention",
            execution_time=time.time() - start,
        )