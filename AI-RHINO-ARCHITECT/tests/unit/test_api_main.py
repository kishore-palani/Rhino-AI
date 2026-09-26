"""Tests for the FastAPI application routes."""

from __future__ import annotations

import asyncio
from typing import Any
from unittest.mock import Mock

from apps.api import main
from apps.api.mcp.exceptions import MCPError, MCPTimeoutError


def test_rhino_tool_connects_and_initializes_before_call(monkeypatch: Any) -> None:
    calls: list[str] = []

    class FakeResult:
        def model_dump(self, **kwargs: Any) -> dict[str, Any]:
            return {"content": []}

    class FakeRhinoClient:
        def __init__(self, config: Any) -> None:
            pass

        async def connect(self) -> None:
            calls.append("connect")

        async def initialize(self) -> None:
            calls.append("initialize")

        async def call_tool(self, name: str, arguments: dict[str, Any]) -> FakeResult:
            calls.append("call_tool")
            return FakeResult()

        async def close(self) -> None:
            calls.append("close")

    monkeypatch.setattr(main, "RhinoMCPClient", FakeRhinoClient)
    monkeypatch.setattr(main, "get_config", lambda: object())

    result = asyncio.run(
        main.call_rhino_tool(main.ToolCallRequest(name="list_objects"))
    )

    assert calls == ["connect", "initialize", "call_tool", "close"]
    assert result == {"content": []}


def test_retryable_mcp_failure_is_reported_as_retryable(monkeypatch: Any) -> None:
    failure = MCPTimeoutError("Rhino request timed out")

    class FakeRhinoClient:
        def __init__(self, config: Any) -> None:
            pass

        async def connect(self) -> None:
            pass

        async def initialize(self) -> None:
            pass

        async def call_tool(self, name: str, arguments: dict[str, Any]) -> Any:
            raise failure

        async def close(self) -> None:
            pass

    monkeypatch.setattr(main, "RhinoMCPClient", FakeRhinoClient)
    monkeypatch.setattr(main, "get_config", lambda: object())
    monkeypatch.setattr(main, "get_project_memory", lambda: Mock())

    result = asyncio.run(
        main.call_rhino_tool(main.ToolCallRequest(name="list_objects"))
    )

    assert result["retryable"] is True


def test_rhino_tool_failure_is_saved_to_project_memory(monkeypatch: Any) -> None:
    failure = MCPError("Rhino connection failed")

    class FakeRhinoClient:
        def __init__(self, config: Any) -> None:
            pass

        async def connect(self) -> None:
            pass

        async def initialize(self) -> None:
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
        "retryable": False,
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

        async def connect(self) -> None:
            pass

        async def initialize(self) -> None:
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

        async def connect(self) -> None:
            pass

        async def initialize(self) -> None:
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