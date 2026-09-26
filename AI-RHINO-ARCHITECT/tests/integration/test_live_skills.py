"""Integration tests for skill executor against live Rhino MCP server.

These tests require a running Rhino MCP server on HTTP localhost:8765.
They are skipped automatically when no server is reachable.
"""

from __future__ import annotations

import os
import pytest
import pytest_asyncio

from ai.skills import SkillExecutor, SkillRegistry
from rhino.adapters.mcp import MCPRhinoAdapter
from apps.api.mcp.config import RhinoMCPConfig


def _http_server_available(url: str = "http://localhost:8765") -> bool:
    """Return True when an HTTP MCP server responds to initialize."""
    try:
        import httpx
        response = httpx.post(
            url,
            json={"jsonrpc": "2.0", "id": 0, "method": "initialize", "params": {}},
            timeout=1.0,
        )
        return response.status_code == 200
    except Exception:
        return False


# Skip all tests in this module if no live server
pytestmark = pytest.mark.integration
skip_no_live_server = pytest.mark.skipif(
    not _http_server_available(),
    reason="No live Rhino MCP server available on http://localhost:8765",
)


@pytest_asyncio.fixture
async def live_adapter():
    """Create a live MCPRhinoAdapter connected to the HTTP server."""
    config = RhinoMCPConfig(use_http=True, http_url="http://localhost:8765")
    adapter = MCPRhinoAdapter(config)
    try:
        await adapter._client.connect()
        await adapter._client.initialize()
        yield adapter
    finally:
        await adapter.close()


@pytest_asyncio.fixture
async def live_executor(live_adapter):
    """Create a SkillExecutor with live adapter."""
    registry = SkillRegistry()
    registry.discover_skills()
    return SkillExecutor(live_adapter, registry)


@skip_no_live_server
class TestLiveSkillExecutor:
    """Integration tests for SkillExecutor against live Rhino."""

    @pytest.mark.asyncio
    async def test_create_point_live(self, live_executor: SkillExecutor):
        """Test creating a point in live Rhino."""
        result = await live_executor.execute("create_point", {"point": (1000, 2000, 3000)})
        
        assert "point_guid" in result
        assert "point_ref" in result
        assert result["point_guid"] is not None
        assert len(result["point_guid"]) > 0

    @pytest.mark.asyncio
    async def test_create_line_live(self, live_executor: SkillExecutor):
        """Test creating a line in live Rhino."""
        result = await live_executor.execute("create_line", {
            "start": (0, 0, 0),
            "end": (5000, 5000, 0)
        })
        
        assert "line_guid" in result
        assert "line_ref" in result
        assert result["line_guid"] is not None

    @pytest.mark.asyncio
    async def test_create_rectangle_live(self, live_executor: SkillExecutor):
        """Test creating a rectangle in live Rhino."""
        plane = {"origin": [0, 0, 0], "x_axis": [1, 0, 0], "y_axis": [0, 1, 0]}
        result = await live_executor.execute("create_rectangle", {
            "plane": plane,
            "width": 3000,
            "height": 2000
        })
        
        assert "rectangle_guid" in result
        assert "rectangle_ref" in result
        assert result["rectangle_guid"] is not None

    @pytest.mark.asyncio
    async def test_create_wall_live(self, live_executor: SkillExecutor):
        """Test creating a wall in live Rhino."""
        # First create a baseline curve
        baseline_result = await live_executor.execute("create_line", {
            "start": (0, 0, 0),
            "end": (5000, 0, 0)
        })
        baseline_guid = baseline_result["line_guid"]
        
        result = await live_executor.execute("create_wall", {
            "curve": baseline_guid,
            "height": 3000,
            "thickness": 200
        })
        
        assert "wall_brep" in result
        assert "wall_guid" in result
        assert result["wall_guid"] is not None

    @pytest.mark.asyncio
    async def test_create_floor_live(self, live_executor: SkillExecutor):
        """Test creating a floor in live Rhino."""
        # First create a boundary rectangle
        plane = {"origin": [0, 0, 0], "x_axis": [1, 0, 0], "y_axis": [0, 1, 0]}
        rect_result = await live_executor.execute("create_rectangle", {
            "plane": plane,
            "width": 4000,
            "height": 3000
        })
        boundary_guid = rect_result["rectangle_guid"]
        
        result = await live_executor.execute("create_floor", {
            "boundary": boundary_guid,
            "thickness": 200
        })
        
        assert "floor_brep" in result
        assert "floor_guid" in result
        assert result["floor_guid"] is not None

    @pytest.mark.asyncio
    async def test_create_column_live(self, live_executor: SkillExecutor):
        """Test creating a column in live Rhino."""
        result = await live_executor.execute("create_column", {
            "base": (0, 0, 0),
            "top": (0, 0, 3000),
            "radius": 150
        })
        
        assert "column_brep" in result
        assert "column_guid" in result
        assert result["column_guid"] is not None

    @pytest.mark.asyncio
    async def test_create_beam_live(self, live_executor: SkillExecutor):
        """Test creating a beam in live Rhino."""
        result = await live_executor.execute("create_beam", {
            "start": (0, 0, 0),
            "end": (6000, 0, 0),
            "width": 300,
            "height": 500
        })
        
        assert "beam_brep" in result
        assert "beam_guid" in result
        assert result["beam_guid"] is not None

    @pytest.mark.asyncio
    async def test_create_surface_live(self, live_executor: SkillExecutor):
        """Test creating a surface via loft in live Rhino."""
        # Create two curves for lofting
        curve1 = await live_executor.execute("create_line", {
            "start": (0, 0, 0),
            "end": (0, 3000, 0)
        })
        curve2 = await live_executor.execute("create_line", {
            "start": (4000, 0, 0),
            "end": (4000, 3000, 0)
        })
        
        result = await live_executor.execute("create_surface", {
            "curves": [curve1["line_guid"], curve2["line_guid"]],
            "mode": "loft"
        })
        
        assert "surface_guid" in result
        assert "surface_ref" in result
        assert result["surface_guid"] is not None

    @pytest.mark.asyncio
    async def test_visual_regression_capture_viewport(self, live_executor: SkillExecutor, live_adapter):
        """Test capturing viewport image for visual regression."""
        # Create some geometry first
        await live_executor.execute("create_point", {"point": (1000, 1000, 1000)})
        await live_executor.execute("create_line", {"start": (0, 0, 0), "end": (5000, 5000, 0)})
        
        # Capture viewport
        result = await live_adapter.call_tool("get_viewport_image", {
            "width": 800,
            "height": 600,
            "view": "perspective",
            "displayMode": "Shaded"
        })
        
        assert "content" in result
        # Should have image data
        assert len(result["content"]) > 0

    @pytest.mark.asyncio
    async def test_transaction_rollback_on_error(self, live_executor: SkillExecutor, live_adapter):
        """Test that transaction rollback works on execution error."""
        # Get initial object count
        initial_result = await live_adapter.call_tool("run_python", {
            "script": """
import json
import rhinoscriptsyntax as rs
count = rs.ObjectCount()
print(json.dumps({"count": count}))
"""
        })
        import json
        initial_count = 0
        if "content" in initial_result and initial_result["content"]:
            data = json.loads(initial_result["content"][0]["text"])
            initial_count = data.get("count", 0)
        
        # Try to execute a skill with invalid inputs (should fail and rollback)
        try:
            await live_executor.execute("create_wall", {
                "curve": "invalid-guid",
                "height": 3000,
                "thickness": 200
            })
        except Exception:
            pass  # Expected to fail
        
        # Check object count after rollback
        final_result = await live_adapter.call_tool("run_python", {
            "script": """
import json
import rhinoscriptsyntax as rs
count = rs.ObjectCount()
print(json.dumps({"count": count}))
"""
        })
        final_count = 0
        if "content" in final_result and final_result["content"]:
            data = json.loads(final_result["content"][0]["text"])
            final_count = data.get("count", 0)
        
        # Count should be same (rollback worked)
        assert final_count == initial_count, f"Rollback failed: {initial_count} -> {final_count}"


@skip_no_live_server
class TestLiveMCPAdapter:
    """Direct tests of MCPRhinoAdapter against live server."""

    @pytest.mark.asyncio
    async def test_adapter_call_tool(self, live_adapter):
        """Test basic adapter tool call."""
        result = await live_adapter.call_tool("get_commands", {})
        assert "content" in result

    @pytest.mark.asyncio
    async def test_adapter_list_objects(self, live_adapter):
        """Test listing objects."""
        import json as json_module

        result = await live_adapter.call_tool("list_objects", {"limit": 10})
        assert "content" in result and result["content"]
        data = json_module.loads(result["content"][0]["text"])
        assert "objects" in data
        assert isinstance(data["objects"], list)