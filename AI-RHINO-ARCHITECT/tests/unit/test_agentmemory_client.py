"""Unit tests for the AgentMemory client and project memory helpers.

These tests use a mocked HTTP layer so they do not require the
agentmemory service to be running.
"""

from __future__ import annotations

import json
import urllib.request
from typing import Any, Dict
from unittest import mock

import pytest

from ai.memory.agentmemory_client import AgentMemoryClient
from ai.memory.project_memory import ProjectMemory


class _FakeResponse:
    def __init__(self, payload: Dict[str, Any]) -> None:
        self._payload = payload

    def read(self) -> bytes:
        return json.dumps(self._payload).encode("utf-8")

    def __enter__(self) -> "_FakeResponse":
        return self

    def __exit__(self, *args: Any) -> None:
        return None


def _patch_urlopen(payload: Dict[str, Any]):
    """Return a context manager that patches urllib.request.urlopen."""
    return mock.patch(
        "urllib.request.urlopen",
        return_value=_FakeResponse(payload),
    )


def test_client_health() -> None:
    client = AgentMemoryClient()
    with _patch_urlopen({"status": "ok", "service": "agentmemory"}):
        result = client.health()
    assert result["status"] == "ok"


def test_client_is_available_when_livez_ok() -> None:
    client = AgentMemoryClient()
    with _patch_urlopen({"status": "ok"}):
        assert client.is_available() is True


def test_client_is_available_returns_false_on_error() -> None:
    client = AgentMemoryClient()
    with mock.patch("urllib.request.urlopen", side_effect=Exception("boom")):
        assert client.is_available() is False


def test_client_remember_returns_memory() -> None:
    client = AgentMemoryClient()
    payload = {
        "memory": {"id": "mem_123", "content": "hello"},
        "success": True,
    }
    with _patch_urlopen(payload):
        result = client.remember(content="hello", project="test-project")
    assert result["success"] is True
    assert result["memory"]["id"] == "mem_123"


def test_client_recall_returns_results() -> None:
    client = AgentMemoryClient()
    payload = {"results": [{"observation": {"id": "mem_1"}}], "format": "full"}
    with _patch_urlopen(payload):
        result = client.recall(query="hello", limit=5)
    assert result["format"] == "full"
    assert result["results"][0]["observation"]["id"] == "mem_1"


def test_client_save_lesson() -> None:
    client = AgentMemoryClient()
    payload = {"success": True, "lesson": {"id": "less_1"}}
    with _patch_urlopen(payload):
        result = client.save_lesson(task="fix bug", lesson="always check units")
    assert result["success"] is True


def test_project_memory_save_state() -> None:
    pm = ProjectMemory(client=AgentMemoryClient())
    payload = {"success": True, "memory": {"id": "mem_state"}}
    with _patch_urlopen(payload):
        result = pm.save_project_state(phase="Phase 1", status="COMPLETE")
    assert result["success"] is True


def test_project_memory_save_failure() -> None:
    pm = ProjectMemory(client=AgentMemoryClient())
    payload = {"success": True, "memory": {"id": "mem_fail"}}
    with _patch_urlopen(payload):
        result = pm.save_failure(
            task="create_wall",
            error="timeout",
            failure_type="rhino",
            diagnosis="MCP server not reachable",
            correction="restart server",
        )
    assert result["success"] is True


def test_project_memory_save_feedback() -> None:
    pm = ProjectMemory(client=AgentMemoryClient())
    payload = {"success": True, "memory": {"id": "mem_fb"}}
    with _patch_urlopen(payload):
        result = pm.save_feedback(
            original_request="create a wall",
            feedback="wall too thick",
            action_taken="reduced thickness",
        )
    assert result["success"] is True


def test_project_memory_recall_relevant() -> None:
    pm = ProjectMemory(client=AgentMemoryClient())
    payload = {"results": []}
    with _patch_urlopen(payload):
        result = pm.recall_relevant("wall design")
    assert result["results"] == []


def test_project_memory_recall_failures() -> None:
    pm = ProjectMemory(client=AgentMemoryClient())
    payload = {"results": [{"observation": {"id": "mem_fail"}}]}
    with _patch_urlopen(payload):
        result = pm.recall_failures("create_wall")
    assert result["results"][0]["observation"]["id"] == "mem_fail"


def test_project_memory_recall_lessons() -> None:
    pm = ProjectMemory(client=AgentMemoryClient())
    payload = {"success": True, "lessons": [{"id": "less_1"}]}
    with _patch_urlopen(payload):
        result = pm.recall_lessons("rhino")
    assert result["success"] is True


def test_session_start_and_end() -> None:
    client = AgentMemoryClient()
    start_payload = {"session": {"id": "sess_1", "status": "active"}}
    end_payload = {"success": True}
    with _patch_urlopen(start_payload):
        start = client.start_session(
            session_id="sess_1",
            project="ai-rhino-architect",
            cwd="E:/Rhino AI_R1",
        )
    assert start["session"]["status"] == "active"

    with _patch_urlopen(end_payload):
        end = client.end_session(session_id="sess_1")
    assert end["success"] is True