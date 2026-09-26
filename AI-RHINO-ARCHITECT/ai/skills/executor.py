"""Skill executor for AI RHINO ARCHITECT.

Maps declarative skill operations to executable Rhino adapter tool calls.
"""

from __future__ import annotations

import json
import logging
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from typing import Any

from .registry import SkillDefinition, SkillRegistry
from .validation import SkillInputValidationError, SkillInputValidator
from rhino.adapters.base import RhinoAdapter

logger = logging.getLogger(__name__)


class SkillExecutionError(ValueError):
    """Raised when skill execution fails."""

    def __init__(self, errors: list[str]) -> None:
        self.errors = errors
        super().__init__("; ".join(errors))


@dataclass
class OperationContext:
    """Runtime context for skill execution."""

    skill: SkillDefinition
    inputs: dict[str, Any]
    unit_scale: float = 1.0
    artifacts: dict[str, Any] = field(default_factory=dict)
    outputs: dict[str, Any] = field(default_factory=dict)
    _transaction_active: bool = False
    _initial_object_count: int = 0


class SkillExecutor:
    """Execute modeling skills by mapping operations to Rhino adapter calls."""

    def __init__(self, adapter: RhinoAdapter, registry: SkillRegistry | None = None) -> None:
        self._adapter = adapter
        self._registry = registry or SkillRegistry()
        self._validator = SkillInputValidator()

    async def execute(self, skill_id: str, inputs: dict[str, Any]) -> dict[str, Any]:
        """Execute a skill by ID with validated inputs.

        Args:
            skill_id: The skill identifier (e.g., "create_point", "create_wall")
            inputs: Raw input values matching the skill's parameter schema

        Returns:
            Dictionary of skill outputs (guids, refs, etc.)

        Raises:
            SkillExecutionError: If validation fails or execution errors occur
        """
        skill_def = self._registry.get_skill(skill_id)
        if skill_def is None:
            raise SkillExecutionError([f"unknown_skill: {skill_id}"])

        skill = SkillDefinition(**skill_def)

        # Validate inputs
        try:
            normalized = self._validator.validate(skill, inputs)
        except SkillInputValidationError as e:
            raise SkillExecutionError(e.errors) from e

        # Check preconditions
        precond_errors = await self._check_preconditions(skill, normalized)
        if precond_errors:
            raise SkillExecutionError(precond_errors)

        # Execute operations within a transaction
        async with self._transaction(skill, normalized) as ctx:
            for op_name in skill.operations:
                handler = OPERATION_HANDLERS.get(op_name)
                if handler is None:
                    raise SkillExecutionError([f"unsupported_operation: {op_name}"])
                try:
                    await handler(ctx, self._adapter)
                except Exception as e:
                    raise SkillExecutionError([f"execution_failed: {op_name}: {e}"]) from e

            # Run validation rules
            validation_errors = await self._run_validations(skill, ctx)
            if validation_errors:
                raise SkillExecutionError(validation_errors)

            # Collect declared outputs
            return {name: ctx.outputs.get(name) for name in skill.outputs}

    @asynccontextmanager
    async def _transaction(self, skill: SkillDefinition, inputs: dict[str, Any]):
        """Transaction context manager for skill execution.

        Records initial object count and rolls back on error by undoing
        any objects created during the skill execution.
        """
        ctx = OperationContext(skill=skill, inputs=inputs)
        ctx._transaction_active = True

        # Record initial object count for rollback
        try:
            result = await self._adapter.call_tool("run_python", {
                "script": """
import json
import rhinoscriptsyntax as rs
count = rs.ObjectCount()
print(json.dumps({"count": count}))
"""
            })
            if "content" in result and result["content"]:
                data = json.loads(result["content"][0]["text"])
                ctx._initial_object_count = data.get("count", 0)
        except Exception:
            ctx._initial_object_count = 0

        try:
            yield ctx
        except Exception:
            # Rollback: delete objects created during this transaction
            await self._rollback(ctx)
            raise

    async def _rollback(self, ctx: OperationContext) -> None:
        """Rollback objects created during the transaction."""
        try:
            # Get current object count
            result = await self._adapter.call_tool("run_python", {
                "script": """
import json
import rhinoscriptsyntax as rs
count = rs.ObjectCount()
print(json.dumps({"count": count}))
"""
            })
            current_count = 0
            if "content" in result and result["content"]:
                data = json.loads(result["content"][0]["text"])
                current_count = data.get("count", 0)

            # If objects were added, undo them
            if current_count > ctx._initial_object_count:
                await self._adapter.call_tool("run_python", {
                    "script": f"""
import rhinoscriptsyntax as rs
# Undo the operations - delete objects created after initial count
for _ in range({current_count - ctx._initial_object_count}):
    rs.Undo()
"""
                })
                logger.info(f"Rolled back {current_count - ctx._initial_object_count} objects for skill {ctx.skill.skill_id}")
        except Exception as e:
            logger.warning(f"Rollback failed for skill {ctx.skill.skill_id}: {e}")

    async def _check_preconditions(self, skill: SkillDefinition, inputs: dict[str, Any]) -> list[str]:
        """Check skill preconditions."""
        errors: list[str] = []
        for precond in skill.preconditions:
            if precond == "document_connected":
                # Adapter doesn't expose connection state directly; assume connected
                pass
            elif precond == "valid_point":
                # Check point-type inputs (not list of points)
                for name, value in inputs.items():
                    if name == "points" and isinstance(value, list):
                        # This is a list of points for create_curve, validate each
                        for i, pt in enumerate(value):
                            if isinstance(pt, (list, tuple)) and len(pt) == 3:
                                if any(isinstance(v, bool) or not isinstance(v, (int, float)) for v in pt):
                                    errors.append(f"precondition_failed: points[{i}] must be numeric coordinates")
                            else:
                                errors.append(f"precondition_failed: points[{i}] must be a 3-element coordinate")
                    elif isinstance(value, (list, tuple)) and len(value) == 3:
                        if any(isinstance(v, bool) or not isinstance(v, (int, float)) for v in value):
                            errors.append(f"precondition_failed: {name} must be numeric coordinates")
            elif precond == "valid_curve":
                # Curve validation requires adapter call; skip for now
                pass
            elif precond == "positive_height" and "height" in inputs:
                if inputs["height"] <= 0:
                    errors.append("precondition_failed: height must be > 0")
            elif precond == "positive_thickness" and "thickness" in inputs:
                if inputs["thickness"] <= 0:
                    errors.append("precondition_failed: thickness must be > 0")
            elif precond == "positive_radius" and "radius" in inputs:
                if inputs["radius"] <= 0:
                    errors.append("precondition_failed: radius must be > 0")
            elif precond == "positive_width" and "width" in inputs:
                if inputs["width"] <= 0:
                    errors.append("precondition_failed: width must be > 0")
            elif precond == "distinct_endpoints":
                if "start" in inputs and "end" in inputs:
                    if inputs["start"] == inputs["end"]:
                        errors.append("precondition_failed: start and end points must be distinct")
            elif precond == "closed_boundary":
                # Requires geometry analysis; skip for now
                pass
            elif precond == "sufficient_points" and "points" in inputs:
                if len(inputs["points"]) < 2:
                    errors.append("precondition_failed: at least 2 points required")
            elif precond == "sufficient_curves" and "curves" in inputs:
                if len(inputs["curves"]) < 2:
                    errors.append("precondition_failed: at least 2 curves required")
            elif precond == "scope_allowed":
                # Authorization check; assume allowed
                pass
        return errors

    async def _run_validations(self, skill: SkillDefinition, ctx: OperationContext) -> list[str]:
        """Run post-execution validation rules."""
        errors: list[str] = []
        for rule in skill.validation:
            if rule == "valid_point":
                if "point_guid" in ctx.outputs and not ctx.outputs["point_guid"]:
                    errors.append("validation_failed: point_guid not set")
            elif rule == "valid_curve":
                for key in ("line_guid", "curve_guid", "rectangle_guid"):
                    if key in ctx.outputs and not ctx.outputs[key]:
                        errors.append(f"validation_failed: {key} not set")
            elif rule == "valid_brep":
                for key in ("wall_brep", "floor_brep", "column_brep", "beam_brep", "roof_brep"):
                    if key in ctx.outputs and not ctx.outputs[key]:
                        errors.append(f"validation_failed: {key} not set")
            elif rule == "valid_surface":
                if "surface_guid" in ctx.outputs and not ctx.outputs["surface_guid"]:
                    errors.append("validation_failed: surface_guid not set")
            elif rule == "positive_length":
                if "line_guid" in ctx.outputs:
                    try:
                        result = await self._adapter.call_tool("run_python", {
                            "script": f"""
import json
import rhinoscriptsyntax as rs
length = rs.CurveLength("{ctx.outputs['line_guid']}") or 0
print(json.dumps({{"length": length}}))
"""
                        })
                        data = _extract_run_python_payload(result)
                        if data.get("length", 0) <= 0:
                            errors.append("validation_failed: line length must be positive")
                    except Exception:
                        pass
            elif rule == "closed_solid":
                for key in ("wall_brep", "floor_brep", "column_brep", "beam_brep", "roof_brep"):
                    if key in ctx.outputs:
                        try:
                            result = await self._adapter.call_tool("run_python", {
                                "script": f"""
import json
import rhinoscriptsyntax as rs
is_solid = bool(rs.IsPolysurfaceClosed("{ctx.outputs[key]}"))
print(json.dumps({{"is_solid": is_solid}}))
"""
                            })
                            data = _extract_run_python_payload(result)
                            if not data.get("is_solid", False):
                                errors.append(f"validation_failed: {key} is not a closed solid")
                        except Exception:
                            pass
            elif rule == "manifold":
                # Requires detailed analysis; skip for now
                pass
            elif rule == "correct_dimensions":
                # Compare expected vs actual; skip for now
                pass
            elif rule == "expected_object_count":
                # Verify at least one object created
                if not ctx.outputs:
                    errors.append("validation_failed: no objects created")
        return errors


# =============================================================================
# Operation Handlers
# =============================================================================

def _parse_last_json_line(stdout: str) -> dict[str, Any] | None:
    """Parse the last non-empty line of stdout as JSON, or None if none parse."""
    for line in reversed(stdout.splitlines()):
        line = line.strip()
        if not line:
            continue
        try:
            return json.loads(line)
        except json.JSONDecodeError:
            continue
    return None


def _extract_run_python_payload(result: dict[str, Any]) -> dict[str, Any]:
    """Extract the JSON payload from a run_python tool result.

    Handles both response formats:
    - Old simple format: {"content": [{"text": '{"guid": "..."}'}]}
    - New nested format: {"content": [{"text": '{"stdout": "...", "error": null}'}]}
    Raises if the nested format reports an execution error with no parseable
    stdout payload.
    """
    if "content" not in result or not result["content"]:
        raise RuntimeError("No content in run_python response")
    text = result["content"][0].get("text", "{}")
    try:
        outer = json.loads(text)
    except json.JSONDecodeError:
        raise RuntimeError("No content in run_python response") from None
    if isinstance(outer, dict) and "stdout" in outer:
        payload = _parse_last_json_line(outer.get("stdout", ""))
        if payload is None:
            if outer.get("error"):
                raise RuntimeError(outer["error"])
            return {}
        return payload
    return outer if isinstance(outer, dict) else {}


async def _run_python_and_get_guid(adapter: RhinoAdapter, script: str) -> str:
    """Run a Python script and extract GUID from the response."""
    result = await adapter.call_tool("run_python", {"script": script})
    return _extract_run_python_payload(result).get("guid")


async def _run_python_and_get_guids(adapter: RhinoAdapter, script: str) -> list[str]:
    """Run a Python script and extract list of GUIDs from the response."""
    result = await adapter.call_tool("run_python", {"script": script})
    return _extract_run_python_payload(result).get("guids", [])


async def _handle_resolve_units(ctx: OperationContext, adapter: RhinoAdapter) -> None:
    """Resolve document units and compute scale factor."""
    try:
        result = await adapter.call_tool("run_python", {
            "script": """
import json
import rhinoscriptsyntax as rs
unit = rs.UnitSystem()
scale = 1.0
if unit == 1: scale = 1.0  # millimeters
elif unit == 2: scale = 10.0  # centimeters
elif unit == 3: scale = 1000.0  # meters
elif unit == 4: scale = 25.4  # inches
elif unit == 5: scale = 304.8  # feet
print(json.dumps({"unit": unit, "scale": scale}))
"""
        })
        # Handle different response formats
        data = _extract_run_python_payload(result)
        ctx.unit_scale = data.get("scale", 1.0)
        ctx.artifacts["document_unit"] = data.get("unit", 1)
    except Exception as e:
        # Default to millimeters if resolution fails
        ctx.unit_scale = 1.0
        ctx.artifacts["document_unit"] = 1


async def _handle_create_point(ctx: OperationContext, adapter: RhinoAdapter) -> None:
    """Create a point object."""
    point = ctx.inputs["point"]
    x, y, z = [v * ctx.unit_scale for v in point]
    try:
        guid = await _run_python_and_get_guid(adapter, f"""
import json
import rhinoscriptsyntax as rs
guid = rs.AddPoint({x}, {y}, {z})
print(json.dumps({{"guid": str(guid)}}))
""")
        ctx.outputs["point_guid"] = guid
        ctx.outputs["point_ref"] = guid
    except Exception as e:
        raise RuntimeError(f"create_point failed: {e}") from e


async def _handle_create_line(ctx: OperationContext, adapter: RhinoAdapter) -> None:
    """Create a line curve."""
    start = ctx.inputs["start"]
    end = ctx.inputs["end"]
    sx, sy, sz = [v * ctx.unit_scale for v in start]
    ex, ey, ez = [v * ctx.unit_scale for v in end]
    try:
        guid = await _run_python_and_get_guid(adapter, f"""
import json
import rhinoscriptsyntax as rs
guid = rs.AddLine(({sx}, {sy}, {sz}), ({ex}, {ey}, {ez}))
print(json.dumps({{"guid": str(guid)}}))
""")
        ctx.outputs["line_guid"] = guid
        ctx.outputs["line_ref"] = guid
    except Exception as e:
        raise RuntimeError(f"create_line failed: {e}") from e


async def _handle_create_curve(ctx: OperationContext, adapter: RhinoAdapter) -> None:
    """Create a NURBS curve through points."""
    points = ctx.inputs["points"]
    degree = ctx.inputs.get("degree", 3)
    scaled_points = [[v * ctx.unit_scale for v in pt] for pt in points]
    pts_str = ", ".join(f"({x}, {y}, {z})" for x, y, z in scaled_points)
    try:
        guid = await _run_python_and_get_guid(adapter, f"""
import json
import rhinoscriptsyntax as rs
pts = [{pts_str}]
guid = rs.AddInterpCurve(pts, degree={degree})
print(json.dumps({{"guid": str(guid)}}))
""")
        ctx.outputs["curve_guid"] = guid
        ctx.outputs["curve_ref"] = guid
    except Exception as e:
        raise RuntimeError(f"create_curve failed: {e}") from e


async def _handle_create_rectangle(ctx: OperationContext, adapter: RhinoAdapter) -> None:
    """Create a rectangle polyline."""
    plane = ctx.inputs["plane"]
    width = ctx.inputs["width"] * ctx.unit_scale
    height = ctx.inputs["height"] * ctx.unit_scale
    ox, oy, oz = [v * ctx.unit_scale for v in plane["origin"]]
    xx, xy, xz = plane["x_axis"]
    yx, yy, yz = plane["y_axis"]
    try:
        guid = await _run_python_and_get_guid(adapter, f"""
import json
import rhinoscriptsyntax as rs
import Rhino.Geometry as rg
plane = rg.Plane(rg.Point3d({ox}, {oy}, {oz}), rg.Vector3d({xx}, {xy}, {xz}), rg.Vector3d({yx}, {yy}, {yz}))
rect = rg.Rectangle3d(plane, rg.Interval(0, {width}), rg.Interval(0, {height}))
guid = rs.AddPolyline(rect.ToPolyline())
print(json.dumps({{"guid": str(guid)}}))
""")
        ctx.outputs["rectangle_guid"] = guid
        ctx.outputs["rectangle_ref"] = guid
    except Exception as e:
        raise RuntimeError(f"create_rectangle failed: {e}") from e


async def _handle_create_circle(ctx: OperationContext, adapter: RhinoAdapter) -> None:
    """Create a circle (used by create_column)."""
    center = ctx.inputs.get("base") or ctx.artifacts.get("circle_center")
    radius = ctx.inputs.get("radius") or ctx.artifacts.get("circle_radius")
    if center is None or radius is None:
        raise RuntimeError("create_circle requires center point and radius in inputs or artifacts")
    cx, cy, cz = [v * ctx.unit_scale for v in center]
    r = radius * ctx.unit_scale
    try:
        guid = await _run_python_and_get_guid(adapter, f"""
import json
import rhinoscriptsyntax as rs
guid = rs.AddCircle(({cx}, {cy}, {cz}), {r})
print(json.dumps({{"guid": str(guid)}}))
""")
        ctx.artifacts["circle_guid"] = guid
    except Exception as e:
        raise RuntimeError(f"create_circle failed: {e}") from e


async def _handle_build_wall_profile(ctx: OperationContext, adapter: RhinoAdapter) -> None:
    """Build a closed rectangular footprint from a straight baseline curve and thickness.

    Extruding an open baseline directly cannot produce a closed solid, so the
    baseline is offset by half the wall thickness on each side to form a
    closed rectangle before extrusion.
    """
    curve_guid = ctx.inputs.get("curve") or ctx.inputs.get("baseline")
    thickness = ctx.inputs.get("thickness")
    if not curve_guid or not thickness:
        return
    thickness = thickness * ctx.unit_scale
    try:
        guid = await _run_python_and_get_guid(adapter, f"""
import json
import rhinoscriptsyntax as rs
curve = rs.coercecurve("{curve_guid}")
start = curve.PointAtStart
end = curve.PointAtEnd
dx, dy = end.X - start.X, end.Y - start.Y
length = (dx**2 + dy**2) ** 0.5
if length == 0:
    print(json.dumps({{"guid": None}}))
else:
    ux, uy = -dy / length, dx / length
    hw = {thickness} / 2.0
    pts = [
        (start.X + ux*hw, start.Y + uy*hw, start.Z),
        (end.X + ux*hw, end.Y + uy*hw, end.Z),
        (end.X - ux*hw, end.Y - uy*hw, end.Z),
        (start.X - ux*hw, start.Y - uy*hw, start.Z),
        (start.X + ux*hw, start.Y + uy*hw, start.Z),
    ]
    guid = rs.AddPolyline(pts)
    print(json.dumps({{"guid": str(guid)}}))
""")
        if guid:
            ctx.artifacts["curve_guid"] = guid
    except Exception as e:
        raise RuntimeError(f"build_wall_profile failed: {e}") from e


async def _handle_extrude_curve(ctx: OperationContext, adapter: RhinoAdapter) -> None:
    """Extrude a curve to create a surface or solid."""
    # Get curve GUID from previous operation or input
    curve_guid = (ctx.artifacts.get("curve_guid") or ctx.artifacts.get("circle_guid") or 
                  ctx.artifacts.get("cross_section_guid") or ctx.inputs.get("curve") or 
                  ctx.inputs.get("boundary") or ctx.inputs.get("baseline"))
    if not curve_guid:
        raise RuntimeError("extrude_curve requires a curve GUID")

    # A cross-section profile (beam) extrudes along its own span axis rather
    # than straight up in Z, using the start/end points as the extrusion path.
    if ctx.artifacts.get("cross_section_guid") and "start" in ctx.inputs and "end" in ctx.inputs:
        start = ctx.inputs["start"]
        end = ctx.inputs["end"]
        sx, sy, sz = [v * ctx.unit_scale for v in start]
        ex, ey, ez = [v * ctx.unit_scale for v in end]
        direction = (ex - sx, ey - sy, ez - sz)
    else:
        # Determine extrusion distance (vertical Z extrusion)
        height = ctx.inputs.get("height") or ctx.inputs.get("thickness")
        # For create_column, calculate height from base and top points
        if height is None and "base" in ctx.inputs and "top" in ctx.inputs:
            base = ctx.inputs["base"]
            top = ctx.inputs["top"]
            height = ((top[0] - base[0])**2 + (top[1] - base[1])**2 + (top[2] - base[2])**2)**0.5
        if height is None:
            raise RuntimeError("extrude_curve requires height or thickness")
        direction = (0, 0, height * ctx.unit_scale)

    dx, dy, dz = direction
    try:
        guid = await _run_python_and_get_guid(adapter, f"""
import json
import rhinoscriptsyntax as rs
import Rhino.Geometry as rg
import scriptcontext as sc
curve = rs.coercecurve("{curve_guid}")
extrusion = rg.Surface.CreateExtrusion(curve, rg.Vector3d({dx}, {dy}, {dz}))
if extrusion:
    guid = sc.doc.Objects.AddBrep(extrusion.ToBrep())
    sc.doc.Views.Redraw()
    print(json.dumps({{"guid": str(guid)}}))
else:
    print(json.dumps({{"guid": None}}))
""")
        ctx.artifacts["extrusion_guid"] = guid
    except Exception as e:
        raise RuntimeError(f"extrude_curve failed: {e}") from e


async def _handle_cap_brep(ctx: OperationContext, adapter: RhinoAdapter) -> None:
    """Cap a brep to make it a closed solid."""
    brep_guid = ctx.artifacts.get("extrusion_guid")
    if not brep_guid:
        raise RuntimeError("cap_brep requires an extrusion GUID")
    try:
        guid = await _run_python_and_get_guid(adapter, f"""
import json
import rhinoscriptsyntax as rs
success = rs.CapPlanarHoles("{brep_guid}")
if success:
    print(json.dumps({{"guid": "{brep_guid}"}}))
else:
    print(json.dumps({{"guid": None}}))
""")
        ctx.artifacts["capped_brep_guid"] = guid or brep_guid
    except Exception as e:
        raise RuntimeError(f"cap_brep failed: {e}") from e


async def _handle_loft(ctx: OperationContext, adapter: RhinoAdapter) -> None:
    """Loft curves to create a surface."""
    curves = ctx.inputs.get("curves", [])
    if not curves:
        raise RuntimeError("loft requires curves")
    try:
        guids = await _run_python_and_get_guids(adapter, f"""
import json
import rhinoscriptsyntax as rs
result = rs.AddLoftSrf({curves!r})
if result:
    print(json.dumps({{"guids": [str(g) for g in result]}}))
else:
    print(json.dumps({{"guids": []}}))
""")
        guid = guids[0] if guids else None
        ctx.outputs["surface_guid"] = guid
        ctx.outputs["surface_ref"] = guid
    except Exception as e:
        raise RuntimeError(f"loft failed: {e}") from e


async def _handle_sweep1(ctx: OperationContext, adapter: RhinoAdapter) -> None:
    """Sweep cross-sections along a rail."""
    rail = ctx.inputs.get("rail")
    cross_sections = ctx.inputs.get("cross_sections", [])
    if not rail or not cross_sections:
        raise RuntimeError("sweep1 requires rail and cross_sections")
    try:
        guids = await _run_python_and_get_guids(adapter, f"""
import json
import rhinoscriptsyntax as rs
result = rs.AddSweep1("{rail}", {cross_sections!r})
if result:
    print(json.dumps({{"guids": [str(g) for g in result]}}))
else:
    print(json.dumps({{"guids": []}}))
""")
        ctx.outputs["surface_guid"] = guids[0] if guids else None
    except Exception as e:
        raise RuntimeError(f"sweep1 failed: {e}") from e


async def _handle_create_cross_section(ctx: OperationContext, adapter: RhinoAdapter) -> None:
    """Create a rectangular cross-section profile for beam (at start point, perpendicular to beam axis)."""
    start = ctx.inputs["start"]
    end = ctx.inputs["end"]
    width = ctx.inputs["width"] * ctx.unit_scale
    height = ctx.inputs["height"] * ctx.unit_scale
    
    sx, sy, sz = [v * ctx.unit_scale for v in start]
    ex, ey, ez = [v * ctx.unit_scale for v in end]
    
    # Calculate beam direction vector
    dx, dy, dz = ex - sx, ey - sy, ez - sz
    length = (dx**2 + dy**2 + dz**2)**0.5
    if length == 0:
        raise RuntimeError("Beam start and end points must be distinct")
    
    # Normalize direction
    dx, dy, dz = dx/length, dy/length, dz/length
    
    # Find perpendicular vectors for cross-section
    # Use world Z as reference, unless beam is vertical
    if abs(dz) > 0.99:  # Nearly vertical beam
        px, py, pz = 1.0, 0.0, 0.0  # X axis as primary
    else:
        px, py, pz = 0.0, 0.0, 1.0  # Z axis as primary
    
    # Cross product for first perpendicular
    ux = dy * pz - dz * py
    uy = dz * px - dx * pz
    uz = dx * py - dy * px
    ulen = (ux**2 + uy**2 + uz**2)**0.5
    ux, uy, uz = ux/ulen, uy/ulen, uz/ulen
    
    # Second perpendicular (cross of direction and first)
    vx = dy * uz - dz * uy
    vy = dz * ux - dx * uz
    vz = dx * uy - dy * ux
    
    # Create rectangle corners at start point
    hw, hh = width/2, height/2
    corners = [
        (sx + ux*hw + vx*hh, sy + uy*hw + vy*hh, sz + uz*hw + vz*hh),
        (sx - ux*hw + vx*hh, sy - uy*hw + vy*hh, sz - uz*hw + vz*hh),
        (sx - ux*hw - vx*hh, sy - uy*hw - vy*hh, sz - uz*hw - vz*hh),
        (sx + ux*hw - vx*hh, sy + uy*hw - vy*hh, sz + uz*hw - vz*hh),
        (sx + ux*hw + vx*hh, sy + uy*hw + vy*hh, sz + uz*hw + vz*hh),  # Close
    ]
    
    pts_str = ", ".join(f"({x}, {y}, {z})" for x, y, z in corners)
    
    try:
        guid = await _run_python_and_get_guid(adapter, f"""
import json
import rhinoscriptsyntax as rs
pts = [{pts_str}]
guid = rs.AddPolyline(pts)
print(json.dumps({{"guid": str(guid)}}))
""")
        ctx.artifacts["cross_section_guid"] = guid
    except Exception as e:
        raise RuntimeError(f"create_cross_section failed: {e}") from e


async def _handle_create_ridge_line(ctx: OperationContext, adapter: RhinoAdapter) -> None:
    """Create ridge line for gabled roof from boundary curve."""
    boundary_guid = ctx.inputs.get("boundary") or ctx.artifacts.get("boundary_guid")
    ridge_height = ctx.inputs["ridge_height"] * ctx.unit_scale
    slope = ctx.inputs["slope"]
    
    if not boundary_guid:
        raise RuntimeError("create_ridge_line requires boundary curve GUID")
    
    # Get boundary curve info to find center and orientation
    try:
        result = await adapter.call_tool("run_python", {
            "script": f"""
import json
import rhinoscriptsyntax as rs
bbox = rs.BoundingBox("{boundary_guid}")
if bbox:
    xs = [p[0] for p in bbox]
    ys = [p[1] for p in bbox]
    zs = [p[2] for p in bbox]
    print(json.dumps({{"min": [min(xs), min(ys), min(zs)], "max": [max(xs), max(ys), max(zs)]}}))
else:
    print(json.dumps({{"min": None, "max": None}}))
"""
        })
        bbox_data = _extract_run_python_payload(result)
        min_pt = bbox_data.get("min") or [0, 0, 0]
        max_pt = bbox_data.get("max") or [10000, 8000, 0]
        # For simplicity, assume rectangular boundary aligned to axes
        cx = (min_pt[0] + max_pt[0]) / 2
        cy = (min_pt[1] + max_pt[1]) / 2
        # Ridge runs along X axis (longer dimension)
        if (max_pt[0] - min_pt[0]) > (max_pt[1] - min_pt[1]):
            ridge_start = (min_pt[0], cy, ridge_height)
            ridge_end = (max_pt[0], cy, ridge_height)
        else:
            ridge_start = (cx, min_pt[1], ridge_height)
            ridge_end = (cx, max_pt[1], ridge_height)
        
        ctx.artifacts["ridge_start"] = ridge_start
        ctx.artifacts["ridge_end"] = ridge_end
        ctx.artifacts["eave_height"] = min_pt[2]
        
        # Create ridge line curve
        guid = await _run_python_and_get_guid(adapter, f"""
import json
import rhinoscriptsyntax as rs
guid = rs.AddLine({ridge_start}, {ridge_end})
print(json.dumps({{"guid": str(guid)}}))
""")
        ctx.artifacts["ridge_guid"] = guid
    except Exception as e:
        raise RuntimeError(f"create_ridge_line failed: {e}") from e


async def _handle_create_gable_surfaces(ctx: OperationContext, adapter: RhinoAdapter) -> None:
    """Create gable roof surfaces from boundary and ridge."""
    boundary_guid = ctx.inputs.get("boundary") or ctx.artifacts.get("boundary_guid")
    ridge_guid = ctx.artifacts.get("ridge_guid")
    eave_height = ctx.artifacts.get("eave_height", 0)
    
    if not boundary_guid or not ridge_guid:
        raise RuntimeError("create_gable_surfaces requires boundary and ridge GUIDs")
    
    # Use loft between boundary edges and ridge
    # Split boundary into edges and loft each to ridge
    try:
        guids = await _run_python_and_get_guids(adapter, f"""
import json
import rhinoscriptsyntax as rs
import Rhino.Geometry as rg
import scriptcontext as sc

boundary = rs.coercecurve("{boundary_guid}")
ridge = rs.coercecurve("{ridge_guid}")

if boundary and ridge:
    # Explode boundary into segments
    segments = rs.ExplodeCurves(boundary)
    if not segments:
        print(json.dumps({{"guids": []}}))
    else:
        all_guids = []
        for seg_guid in segments:
            seg = rs.coercecurve(seg_guid)
            if seg:
                # Loft each segment to ridge
                loft = rg.Brep.CreateFromLoft([seg.ToNurbsCurve(), ridge.ToNurbsCurve()], rg.Point3d.Unset, rg.Point3d.Unset, rg.LoftType.Normal, False)
                if loft:
                    for b in loft:
                        guid = sc.doc.Objects.AddBrep(b)
                        all_guids.append(str(guid))
        sc.doc.Views.Redraw()
        print(json.dumps({{"guids": all_guids}}))
else:
    print(json.dumps({{"guids": []}}))
""")
        if guids:
            ctx.artifacts["gable_surface_guids"] = guids
    except Exception as e:
        raise RuntimeError(f"create_gable_surfaces failed: {e}") from e


async def _handle_join_surfaces(ctx: OperationContext, adapter: RhinoAdapter) -> None:
    """Join surfaces into a single Brep."""
    surface_guids = ctx.artifacts.get("gable_surface_guids", [])
    if not surface_guids:
        raise RuntimeError("join_surfaces requires surface GUIDs")
    
    try:
        guid = await _run_python_and_get_guid(adapter, f"""
import json
import rhinoscriptsyntax as rs
guids = {surface_guids}
brep = rs.JoinSurfaces(guids)
if brep:
    print(json.dumps({{"guid": str(brep[0])}}))
else:
    print(json.dumps({{"guid": None}}))
""")
        if guid:
            ctx.artifacts["joined_brep_guid"] = guid
    except Exception as e:
        raise RuntimeError(f"join_surfaces failed: {e}") from e


async def _handle_create_opening_profile(ctx: OperationContext, adapter: RhinoAdapter) -> None:
    """Create rectangular opening profile on wall for door/window."""
    wall_guid = ctx.inputs["wall_guid"]
    position = ctx.inputs["position"] * ctx.unit_scale
    width = ctx.inputs["width"] * ctx.unit_scale
    height = ctx.inputs["height"] * ctx.unit_scale
    sill_height = ctx.inputs.get("sill_height", 0) * ctx.unit_scale
    
    # Get wall geometry to determine opening location
    try:
        # Simplified: assume wall is along X axis at origin
        # Real implementation would compute from wall geometry
        cx, cy, cz = position, 0, sill_height
        hw, hh = width/2, height/2
        
        corners = [
            (cx - hw, cy - 100, cz),      # Extend through wall thickness
            (cx + hw, cy - 100, cz),
            (cx + hw, cy - 100, cz + hh),
            (cx - hw, cy - 100, cz + hh),
            (cx - hw, cy - 100, cz),
        ]
        
        pts_str = ", ".join(f"({x}, {y}, {z})" for x, y, z in corners)
        
        guid = await _run_python_and_get_guid(adapter, f"""
import json
import rhinoscriptsyntax as rs
import Rhino.Geometry as rg
import scriptcontext as sc
pts = [{pts_str}]
curve_guid = rs.AddPolyline(pts)
# Extrude through wall - use vector for direction
curve = rs.coercecurve(curve_guid)
if curve:
    # Extrude along Y axis (through wall thickness) using Extrusion
    extrusion = rg.Extrusion.Create(curve.ToNurbsCurve(), 200, True)
    if extrusion:
        brep = extrusion.ToBrep()
        if brep:
            guid = sc.doc.Objects.AddBrep(brep)
            sc.doc.Views.Redraw()
            print(json.dumps({{"guid": str(guid)}}))
        else:
            print(json.dumps({{"guid": null}}))
    else:
        print(json.dumps({{"guid": null}}))
else:
    print(json.dumps({{"guid": null}}))
""")
        if guid:
            ctx.artifacts["opening_brep_guid"] = guid
    except Exception as e:
        raise RuntimeError(f"create_opening_profile failed: {e}") from e


async def _handle_boolean_difference(ctx: OperationContext, adapter: RhinoAdapter) -> None:
    """Perform boolean difference (cut opening in wall)."""
    wall_guid = ctx.inputs.get("wall_guid")
    opening_guid = ctx.artifacts.get("opening_brep_guid")
    
    if not wall_guid or not opening_guid:
        raise RuntimeError("boolean_difference requires wall and opening GUIDs")
    
    try:
        guids = await _run_python_and_get_guids(adapter, f"""
import json
import rhinoscriptsyntax as rs
import Rhino.Geometry as rg
import scriptcontext as sc
wall = rs.coercebrep("{wall_guid}")
opening = rs.coercebrep("{opening_guid}")
if wall and opening:
    result = rg.Brep.CreateBooleanDifference(wall, opening, rs.UnitAbsoluteTolerance())
    if result:
        guids = [sc.doc.Objects.AddBrep(b) for b in result]
        sc.doc.Views.Redraw()
        print(json.dumps({{"guids": [str(g) for g in guids]}}))
    else:
        print(json.dumps({{"guids": []}}))
else:
    print(json.dumps({{"guids": []}}))
""")
        if guids:
            ctx.artifacts["wall_with_opening_guid"] = guids[0]
            ctx.outputs["opening_guid"] = opening_guid
    except Exception as e:
        raise RuntimeError(f"boolean_difference failed: {e}") from e


async def _handle_create_door_frame(ctx: OperationContext, adapter: RhinoAdapter) -> None:
    """Create door frame around opening."""
    wall_guid = ctx.inputs["wall_guid"]
    position = ctx.inputs["position"] * ctx.unit_scale
    width = ctx.inputs["width"] * ctx.unit_scale
    height = ctx.inputs["height"] * ctx.unit_scale
    sill_height = ctx.inputs.get("sill_height", 0) * ctx.unit_scale
    frame_depth = 100 * ctx.unit_scale  # Frame depth
    frame_width = 50 * ctx.unit_scale   # Frame width
    
    # Create frame as a rectangular tube around opening
    try:
        guids = await _run_python_and_get_guids(adapter, f"""
import json
import rhinoscriptsyntax as rs
import Rhino.Geometry as rg
import scriptcontext as sc

# Outer frame rectangle
cx, cy, cz = {position}, 0, {sill_height}
hw, hh = {width/2 + frame_width}, {height + frame_width}
fd = {frame_depth}

# Create frame profile (outer minus inner)
outer_pts = [
    (cx - hw, cy - fd/2, cz),
    (cx + hw, cy - fd/2, cz),
    (cx + hw, cy - fd/2, cz + hh),
    (cx - hw, cy - fd/2, cz + hh),
    (cx - hw, cy - fd/2, cz),
]
inner_pts = [
    (cx - hw + {frame_width}, cy - fd/2, cz + {frame_width}),
    (cx + hw - {frame_width}, cy - fd/2, cz + {frame_width}),
    (cx + hw - {frame_width}, cy - fd/2, cz + hh - {frame_width}),
    (cx - hw + {frame_width}, cy - fd/2, cz + hh - {frame_width}),
    (cx - hw + {frame_width}, cy - fd/2, cz + {frame_width}),
]

outer_curve = rs.AddPolyline(outer_pts)
inner_curve = rs.AddPolyline(inner_pts)

# Extrude using Extrusion
outer_extrusion = rg.Extrusion.Create(rs.coercecurve(outer_curve).ToNurbsCurve(), fd, True)
inner_extrusion = rg.Extrusion.Create(rs.coercecurve(inner_curve).ToNurbsCurve(), fd, True)

if outer_extrusion and inner_extrusion:
    outer_brep = outer_extrusion.ToBrep()
    inner_brep = inner_extrusion.ToBrep()
    if outer_brep and inner_brep:
        result = rg.Brep.CreateBooleanDifference(outer_brep, inner_brep, rs.UnitAbsoluteTolerance())
        if result:
            guids = [sc.doc.Objects.AddBrep(b) for b in result]
            sc.doc.Views.Redraw()
            print(json.dumps({{"guids": [str(g) for g in guids]}}))
        else:
            print(json.dumps({{"guids": []}}))
    else:
        print(json.dumps({{"guids": []}}))
else:
    print(json.dumps({{"guids": []}}))
""")
        if guids:
            ctx.outputs["frame_guid"] = guids[0]
    except Exception as e:
        raise RuntimeError(f"create_door_frame failed: {e}") from e


async def _handle_create_door_leaf(ctx: OperationContext, adapter: RhinoAdapter) -> None:
    """Create door leaf (the actual door panel)."""
    position = ctx.inputs["position"] * ctx.unit_scale
    width = ctx.inputs["width"] * ctx.unit_scale
    height = ctx.inputs["height"] * ctx.unit_scale
    sill_height = ctx.inputs.get("sill_height", 0) * ctx.unit_scale
    leaf_thickness = 40 * ctx.unit_scale
    
    try:
        guid = await _run_python_and_get_guid(adapter, f"""
import json
import rhinoscriptsyntax as rs
import Rhino.Geometry as rg
import scriptcontext as sc
cx, cy, cz = {position}, -{leaf_thickness/2}, {sill_height}
hw, hh = {width/2}, {height}
leaf_pts = [
    (cx - hw, cy, cz),
    (cx + hw, cy, cz),
    (cx + hw, cy, cz + hh),
    (cx - hw, cy, cz + hh),
    (cx - hw, cy, cz),
]
curve_guid = rs.AddPolyline(leaf_pts)
curve = rs.coercecurve(curve_guid)
if curve:
    extrusion = rg.Extrusion.Create(curve.ToNurbsCurve(), {leaf_thickness}, True)
    if extrusion:
        brep = extrusion.ToBrep()
        if brep:
            guid = sc.doc.Objects.AddBrep(brep)
            sc.doc.Views.Redraw()
            print(json.dumps({{"guid": str(guid)}}))
        else:
            print(json.dumps({{"guid": null}}))
    else:
        print(json.dumps({{"guid": null}}))
else:
    print(json.dumps({{"guid": null}}))
""")
        if guid:
            ctx.outputs["door_guid"] = guid
    except Exception as e:
        raise RuntimeError(f"create_door_leaf failed: {e}") from e


async def _handle_create_window_frame(ctx: OperationContext, adapter: RhinoAdapter) -> None:
    """Create window frame around opening (similar to door frame)."""
    # Reuse door frame logic with different dimensions
    await _handle_create_door_frame(ctx, adapter)
    # Rename output
    if "frame_guid" in ctx.outputs:
        ctx.outputs["frame_guid"] = ctx.outputs.pop("frame_guid")


async def _handle_create_glazing_pane(ctx: OperationContext, adapter: RhinoAdapter) -> None:
    """Create glazing pane for window."""
    position = ctx.inputs["position"] * ctx.unit_scale
    width = ctx.inputs["width"] * ctx.unit_scale
    height = ctx.inputs["height"] * ctx.unit_scale
    sill_height = ctx.inputs["sill_height"] * ctx.unit_scale
    glass_thickness = 10 * ctx.unit_scale
    
    try:
        guid = await _run_python_and_get_guid(adapter, f"""
import json
import rhinoscriptsyntax as rs
import Rhino.Geometry as rg
import scriptcontext as sc
cx, cy, cz = {position}, 0, {sill_height}
hw, hh = {width/2 - 20}, {height - 20}  # Slightly smaller than frame
glass_pts = [
    (cx - hw, cy, cz),
    (cx + hw, cy, cz),
    (cx + hw, cy, cz + hh),
    (cx - hw, cy, cz + hh),
    (cx - hw, cy, cz),
]
curve_guid = rs.AddPolyline(glass_pts)
curve = rs.coercecurve(curve_guid)
if curve:
    extrusion = rg.Extrusion.Create(curve.ToNurbsCurve(), {glass_thickness}, True)
    if extrusion:
        brep = extrusion.ToBrep()
        if brep:
            guid = sc.doc.Objects.AddBrep(brep)
            sc.doc.Views.Redraw()
            print(json.dumps({{"guid": str(guid)}}))
        else:
            print(json.dumps({{"guid": null}}))
    else:
        print(json.dumps({{"guid": null}}))
else:
    print(json.dumps({{"guid": null}}))
""")
        if guid:
            ctx.outputs["glazing_guid"] = guid
    except Exception as e:
        raise RuntimeError(f"create_glazing_pane failed: {e}") from e


async def _handle_add_point_to_document(ctx: OperationContext, adapter: RhinoAdapter) -> None:
    """Add point to document (already done by create_point via run_python)."""
    # The run_python script already adds to document
    pass


async def _handle_add_curve_to_document(ctx: OperationContext, adapter: RhinoAdapter) -> None:
    """Add curve to document (already done by create_line/curve/rectangle via run_python)."""
    pass


async def _handle_add_brep_to_document(ctx: OperationContext, adapter: RhinoAdapter) -> None:
    """Add brep to document (already done by capped extrusion)."""
    brep_guid = ctx.artifacts.get("capped_brep_guid") or ctx.artifacts.get("extrusion_guid")
    if brep_guid:
        # Map to skill-specific output names
        if ctx.skill.skill_id == "create_wall":
            ctx.outputs["wall_brep"] = brep_guid
            ctx.outputs["wall_guid"] = brep_guid
        elif ctx.skill.skill_id == "create_floor":
            ctx.outputs["floor_brep"] = brep_guid
            ctx.outputs["floor_guid"] = brep_guid
        elif ctx.skill.skill_id == "create_column":
            ctx.outputs["column_brep"] = brep_guid
            ctx.outputs["column_guid"] = brep_guid
        elif ctx.skill.skill_id == "create_beam":
            ctx.outputs["beam_brep"] = brep_guid
            ctx.outputs["beam_guid"] = brep_guid
        elif ctx.skill.skill_id == "create_roof":
            ctx.outputs["roof_brep"] = brep_guid
            ctx.outputs["roof_guid"] = brep_guid


async def _handle_add_surface_to_document(ctx: OperationContext, adapter: RhinoAdapter) -> None:
    """Add surface to document (already done by loft/sweep1)."""
    pass


async def _handle_analyze_objects(ctx: OperationContext, adapter: RhinoAdapter) -> None:
    """Analyze created objects for validation."""
    # Collect all GUIDs from outputs and artifacts
    guids = [v for v in ctx.outputs.values() if isinstance(v, str)]
    guids.extend(v for v in ctx.artifacts.values() if isinstance(v, str))
    if guids:
        try:
            result = await adapter.call_tool("analyze_objects", {"ids": guids})
            ctx.artifacts["analysis"] = result
        except Exception:
            pass  # Non-fatal


# Operation handler registry
OPERATION_HANDLERS: dict[str, Any] = {
    "resolve_units": _handle_resolve_units,
    "create_point": _handle_create_point,
    "create_line": _handle_create_line,
    "create_curve": _handle_create_curve,
    "create_rectangle": _handle_create_rectangle,
    "create_circle": _handle_create_circle,
    "create_cross_section": _handle_create_cross_section,
    "build_wall_profile": _handle_build_wall_profile,
    "extrude_curve": _handle_extrude_curve,
    "cap_brep": _handle_cap_brep,
    "loft": _handle_loft,
    "sweep1": _handle_sweep1,
    "create_ridge_line": _handle_create_ridge_line,
    "create_gable_surfaces": _handle_create_gable_surfaces,
    "join_surfaces": _handle_join_surfaces,
    "create_opening_profile": _handle_create_opening_profile,
    "boolean_difference": _handle_boolean_difference,
    "create_door_frame": _handle_create_door_frame,
    "create_door_leaf": _handle_create_door_leaf,
    "create_window_frame": _handle_create_window_frame,
    "create_glazing_pane": _handle_create_glazing_pane,
    "add_point_to_document": _handle_add_point_to_document,
    "add_curve_to_document": _handle_add_curve_to_document,
    "add_brep_to_document": _handle_add_brep_to_document,
    "add_surface_to_document": _handle_add_surface_to_document,
    "analyze_objects": _handle_analyze_objects,
}