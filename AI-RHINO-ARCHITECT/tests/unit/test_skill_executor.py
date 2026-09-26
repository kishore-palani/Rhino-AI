"""Unit tests for the skill executor."""

from __future__ import annotations

import json
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

from ai.skills import SkillDefinition, SkillExecutor, SkillRegistry
from rhino.adapters.base import RhinoAdapter


class FakeAdapter(RhinoAdapter):
    """Fake adapter that records calls for testing."""

    def __init__(self) -> None:
        self.calls: list[tuple[str, dict[str, Any]]] = []
        self._responses: dict[str, Any] = {}
        self._object_count = 0

    def set_response(self, tool_name: str, response: Any) -> None:
        self._responses[tool_name] = response

    async def call_tool(self, name: str, arguments: dict[str, Any]) -> Any:
        self.calls.append((name, arguments))
        if name in self._responses:
            return self._responses[name]
        # Default responses for common tools. The real Rhino MCP router only
        # exposes run_python/run_csharp/run_command, so every geometry
        # operation is implemented as a run_python script; responses mirror
        # the router's nested {"stdout": ..., "error": ...} envelope.
        if name == "run_python":
            script = arguments.get("script", "")
            if "UnitSystem" in script:
                payload = {"unit": 1, "scale": 1.0}
            elif "ObjectCount" in script:
                self._object_count += 1
                payload = {"count": self._object_count}
            elif "AddPoint" in script:
                payload = {"guid": "fake-guid-123"}
            elif "AddLine" in script:
                payload = {"guid": "fake-guid-123"}
            elif "AddInterpCurve" in script:
                payload = {"guid": "fake-guid-123"}
            elif "AddCircle" in script:
                payload = {"guid": "circle-guid-456"}
            elif "CreateExtrusion" in script:
                payload = {"guid": "extrusion-guid-456"}
            elif "CapPlanarHoles" in script:
                payload = {"guid": "capped-guid-789"}
            elif "AddLoftSrf" in script:
                payload = {"guids": ["surface-guid-999"]}
            elif "AddSweep1" in script:
                payload = {"guids": ["surface-guid-999"]}
            elif "CurveLength" in script:
                payload = {"length": 100.0}
            elif "IsPolysurfaceClosed" in script:
                payload = {"is_solid": True}
            elif "BoundingBox" in script:
                payload = {"min": [0, 0, 0], "max": [10000, 8000, 0]}
            elif "Rectangle3d" in script or "AddPolyline" in script:
                payload = {"guid": "fake-guid-123"}
            elif "Undo" in script:
                payload = {"success": True}
            else:
                payload = {"guid": "fake-guid-123"}
            return {"content": [{"text": json.dumps({"stdout": json.dumps(payload), "error": None})}]}
        return {"content": []}

    async def close(self) -> None:
        pass


@pytest.fixture
def fake_adapter() -> FakeAdapter:
    return FakeAdapter()


@pytest.fixture
def registry() -> SkillRegistry:
    reg = SkillRegistry()
    reg.discover_skills()
    return reg


@pytest.fixture
def executor(fake_adapter: FakeAdapter, registry: SkillRegistry) -> SkillExecutor:
    return SkillExecutor(fake_adapter, registry)


class TestSkillExecutor:
    """Tests for SkillExecutor."""

    @pytest.mark.asyncio
    async def test_execute_create_point(self, executor: SkillExecutor, fake_adapter: FakeAdapter) -> None:
        """Test executing create_point skill."""
        result = await executor.execute("create_point", {"point": (10, 20, 30)})

        assert "point_guid" in result
        assert "point_ref" in result
        assert result["point_guid"] == "fake-guid-123"

        # Verify run_python was called for geometry creation (third call after resolve_units and ObjectCount)
        run_python_calls = [c for c in fake_adapter.calls if c[0] == "run_python"]
        assert len(run_python_calls) >= 3
        script = run_python_calls[2][1]["script"]
        assert "AddPoint" in script
        assert "10" in script and "20" in script and "30" in script

    @pytest.mark.asyncio
    async def test_execute_create_line(self, executor: SkillExecutor, fake_adapter: FakeAdapter) -> None:
        """Test executing create_line skill."""
        result = await executor.execute("create_line", {"start": (0, 0, 0), "end": (100, 100, 0)})

        assert "line_guid" in result
        assert "line_ref" in result
        assert result["line_guid"] == "fake-guid-123"

        run_python_calls = [c for c in fake_adapter.calls if c[0] == "run_python"]
        assert len(run_python_calls) >= 3
        script = run_python_calls[2][1]["script"]
        assert "AddLine" in script

    @pytest.mark.asyncio
    async def test_execute_create_curve(self, executor: SkillExecutor, fake_adapter: FakeAdapter) -> None:
        """Test executing create_curve skill."""
        result = await executor.execute("create_curve", {"points": [(0, 0, 0), (10, 10, 0), (20, 0, 0)], "degree": 3})

        assert "curve_guid" in result
        assert "curve_ref" in result

        run_python_calls = [c for c in fake_adapter.calls if c[0] == "run_python"]
        assert len(run_python_calls) >= 3
        script = run_python_calls[2][1]["script"]
        assert "AddInterpCurve" in script

    @pytest.mark.asyncio
    async def test_execute_create_rectangle(self, executor: SkillExecutor, fake_adapter: FakeAdapter) -> None:
        """Test executing create_rectangle skill."""
        plane = {"origin": [0, 0, 0], "x_axis": [1, 0, 0], "y_axis": [0, 1, 0]}
        result = await executor.execute("create_rectangle", {"plane": plane, "width": 100, "height": 50})

        assert "rectangle_guid" in result
        assert "rectangle_ref" in result

        run_python_calls = [c for c in fake_adapter.calls if c[0] == "run_python"]
        assert len(run_python_calls) >= 3
        script = run_python_calls[2][1]["script"]
        assert "Rectangle3d" in script or "AddPolyline" in script

    @pytest.mark.asyncio
    async def test_execute_create_wall(self, executor: SkillExecutor, fake_adapter: FakeAdapter) -> None:
        """Test executing create_wall skill."""
        result = await executor.execute("create_wall", {
            "curve": "baseline-guid",
            "height": 3000,
            "thickness": 200
        })

        assert "wall_brep" in result
        assert "wall_guid" in result

        # Should have extruded and capped via run_python
        scripts = [c[1]["script"] for c in fake_adapter.calls if c[0] == "run_python"]
        assert any("CreateExtrusion" in s for s in scripts)
        assert any("CapPlanarHoles" in s for s in scripts)

    @pytest.mark.asyncio
    async def test_execute_create_floor(self, executor: SkillExecutor, fake_adapter: FakeAdapter) -> None:
        """Test executing create_floor skill."""
        result = await executor.execute("create_floor", {
            "boundary": "boundary-guid",
            "thickness": 200
        })

        assert "floor_brep" in result
        assert "floor_guid" in result

        scripts = [c[1]["script"] for c in fake_adapter.calls if c[0] == "run_python"]
        assert any("CreateExtrusion" in s for s in scripts)
        assert any("CapPlanarHoles" in s for s in scripts)

    @pytest.mark.asyncio
    async def test_execute_create_column(self, executor: SkillExecutor, fake_adapter: FakeAdapter) -> None:
        """Test executing create_column skill."""
        result = await executor.execute("create_column", {
            "base": (0, 0, 0),
            "top": (0, 0, 3000),
            "radius": 150
        })

        assert "column_brep" in result
        assert "column_guid" in result

        scripts = [c[1]["script"] for c in fake_adapter.calls if c[0] == "run_python"]
        assert any("CreateExtrusion" in s for s in scripts)
        assert any("CapPlanarHoles" in s for s in scripts)

    @pytest.mark.asyncio
    async def test_execute_unknown_skill_raises(self, executor: SkillExecutor) -> None:
        """Test that unknown skill raises SkillExecutionError."""
        with pytest.raises(Exception) as exc_info:
            await executor.execute("nonexistent_skill", {})
        assert "unknown_skill" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_execute_invalid_inputs_raises(self, executor: SkillExecutor) -> None:
        """Test that invalid inputs raise SkillExecutionError."""
        with pytest.raises(Exception) as exc_info:
            await executor.execute("create_wall", {"curve": "baseline"})  # missing height, thickness
        assert "missing_input" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_execute_negative_dimension_raises(self, executor: SkillExecutor) -> None:
        """Test that negative dimensions raise validation error."""
        with pytest.raises(Exception) as exc_info:
            await executor.execute("create_wall", {
                "curve": "baseline",
                "height": -100,
                "thickness": 200
            })
        # Validator catches this before preconditions
        assert "invalid_parameter" in str(exc_info.value) or "precondition_failed" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_resolve_units_called_first(self, executor: SkillExecutor, fake_adapter: FakeAdapter) -> None:
        """Test that resolve_units is called before geometry operations."""
        await executor.execute("create_point", {"point": (1, 2, 3)})

        run_python_calls = [c for c in fake_adapter.calls if c[0] == "run_python"]
        # resolve_units should be second (first is ObjectCount for transaction)
        assert len(run_python_calls) >= 2
        script = run_python_calls[1][1]["script"]
        assert "UnitSystem" in script

    @pytest.mark.asyncio
    async def test_analyze_objects_called_for_validation(self, executor: SkillExecutor, fake_adapter: FakeAdapter) -> None:
        """Test that curve length is checked via run_python for validation rules."""
        await executor.execute("create_line", {"start": (0, 0, 0), "end": (10, 0, 0)})

        scripts = [c[1]["script"] for c in fake_adapter.calls if c[0] == "run_python"]
        assert any("CurveLength" in s for s in scripts)

    @pytest.mark.asyncio
    async def test_execute_create_beam(self, executor: SkillExecutor, fake_adapter: FakeAdapter) -> None:
        """Test executing create_beam skill."""
        result = await executor.execute("create_beam", {
            "start": (0, 0, 0),
            "end": (5000, 0, 0),
            "width": 300,
            "height": 500
        })

        assert "beam_brep" in result
        assert "beam_guid" in result

        scripts = [c[1]["script"] for c in fake_adapter.calls if c[0] == "run_python"]
        assert any("CreateExtrusion" in s for s in scripts)
        assert any("CapPlanarHoles" in s for s in scripts)

    @pytest.mark.asyncio
    async def test_execute_create_surface(self, executor: SkillExecutor, fake_adapter: FakeAdapter) -> None:
        """Test executing create_surface skill."""
        result = await executor.execute("create_surface", {
            "curves": ["curve-1", "curve-2"],
            "mode": "loft"
        })

        assert "surface_guid" in result
        assert "surface_ref" in result

        scripts = [c[1]["script"] for c in fake_adapter.calls if c[0] == "run_python"]
        assert any("AddLoftSrf" in s for s in scripts)