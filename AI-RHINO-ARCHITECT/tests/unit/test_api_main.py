"""Tests for the FastAPI application routes."""

from __future__ import annotations

import asyncio
from typing import Any
from unittest.mock import Mock

from apps.api import main
from apps.api.mcp.exceptions import MCPError


def test_rhino_tool_failure_is_saved_to_project_memory(monkeypatch: Any) -> None:
    failure = MCPError("Rhino connection failed")

    class FakeRhinoClient:
        def __init__(self, config: Any) -> None:
            pass

        async def call_tool(self, name: str, arguments: dict[str, Any]) -> Any:
            raise failure

        async def close(self) -> None:
            pass

    memory = Mock()
    monkeypatch.setattr(main, "RhinoMCPClient", FakeRhinoClient)
    monkeypatch.setattr(main, "get_config", lambda: object())
    monkeypatch.setattr(main, "get_project_memory", lambda: memory, raising=False)

    result = asyncio.run(
        main.call_rhino_tool(
            main.ToolCallRequest(name="rhino.create_wall", arguments={"length": 5})
        )
    )

    assert result == {
        "status": "error",
        "message": "Rhino connection failed",
        "retryable": True,
    }
    memory.save_failure.assert_called_once_with(
        task="Rhino tool call: rhino.create_wall",
        error="Rhino connection failed",
        failure_type="rhino_tool",
    )


def test_unexpected_rhino_tool_failure_is_saved_then_raised(monkeypatch: Any) -> None:
    failure = RuntimeError("unexpected tool failure")

    class FakeRhinoClient:
        def __init__(self, config: Any) -> None:
            pass

        async def call_tool(self, name: str, arguments: dict[str, Any]) -> Any:
            raise failure

        async def close(self) -> None:
            pass

    memory = Mock()
    monkeypatch.setattr(main, "RhinoMCPClient", FakeRhinoClient)
    monkeypatch.setattr(main, "get_config", lambda: object())
    monkeypatch.setattr(main, "get_project_memory", lambda: memory)

    try:
        asyncio.run(main.call_rhino_tool(main.ToolCallRequest(name="custom.tool")))
    except RuntimeError as error:
        assert error is failure
    else:
        raise AssertionError("Unexpected Rhino tool errors must remain visible")

    memory.save_failure.assert_called_once_with(
        task="Rhino tool call: custom.tool",
        error="unexpected tool failure",
        failure_type="rhino_tool",
    )


def test_memory_failure_does_not_mask_mcp_error(monkeypatch: Any) -> None:
    failure = MCPError("Rhino connection failed")

    class FakeRhinoClient:
        def __init__(self, config: Any) -> None:
            pass

        async def call_tool(self, name: str, arguments: dict[str, Any]) -> Any:
            raise failure

        async def close(self) -> None:
            pass

    memory = Mock()
    memory.save_failure.side_effect = RuntimeError("memory service unavailable")
    monkeypatch.setattr(main, "RhinoMCPClient", FakeRhinoClient)
    monkeypatch.setattr(main, "get_config", lambda: object())
    monkeypatch.setattr(main, "get_project_memory", lambda: memory)

    result = asyncio.run(main.call_rhino_tool(main.ToolCallRequest(name="custom.tool")))

    assert result["status"] == "error"
    assert result["message"] == "Rhino connection failed"