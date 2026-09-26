"""Integration tests for the Rhino MCP client.

These tests require a running Rhino MCP server on TCP port 8765 (the default)
or HTTP on localhost:8765. They are skipped automatically when no server is
reachable so the suite stays green in environments without Rhino installed.

To run them against a live server start ``rhinomcp`` (or your equivalent
TCP/HTTP server) on localhost:8765 and invoke pytest with the integration
marker selected::

    pytest tests/integration/test_mcp_client.py -m integration -v
"""

from __future__ import annotations

import asyncio
import os
import socket
from typing import Any, AsyncIterator

import pytest
import pytest_asyncio

from apps.api.mcp import RhinoMCPClient, get_config
from apps.api.mcp.config import RhinoMCPConfig
from apps.api.mcp.exceptions import (
    MCPConnectionError,
    MCPError,
    MCPTimeoutError,
)
from apps.api.mcp.models import JSONRPCRequest


def _port_is_open(host: str = "localhost", port: int = 8765) -> bool:
    """Return True when a TCP connection to host:port succeeds immediately."""
    try:
        with socket.create_connection((host, port), timeout=0.5):
            return True
    except OSError:
        return False


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


def _server_available() -> bool:
    """Check if MCP server is available via TCP or HTTP."""
    # Check environment for transport preference
    use_http = os.environ.get("RHINO_MCP_USE_HTTP", "").strip().lower() in {"1", "true", "yes", "on"}
    if use_http:
        return _http_server_available(os.environ.get("RHINO_MCP_HTTP_URL", "http://localhost:8765"))
    return _port_is_open()


# Skip the whole module when no MCP server is reachable.
pytestmark = pytest.mark.integration
skip_no_server = pytest.mark.skipif(
    not _server_available(),
    reason="No MCP server available on localhost:8765 (TCP or HTTP)",
)


@pytest_asyncio.fixture
async def mcp_client() -> AsyncIterator[RhinoMCPClient]:
    """Yield a connected and initialized MCP client, cleaning up afterwards."""
    client = RhinoMCPClient(get_config())
    try:
        await client.connect()
        await client.initialize()
    except MCPError:
        await client.disconnect()
        pytest.skip("MCP server not reachable during fixture setup")
    try:
        yield client
    finally:
        await client.disconnect()


@skip_no_server
async def test_connect_and_initialize(mcp_client: RhinoMCPClient) -> None:
    """The client should report connected and initialized state."""
    assert mcp_client.is_connected
    assert mcp_client.is_initialized


@skip_no_server
async def test_list_tools(mcp_client: RhinoMCPClient) -> None:
    """list_tools should return a ToolListResult with at least one tool."""
    result = await mcp_client.list_tools()
    assert hasattr(result, "tools")
    assert isinstance(result.tools, list)
    assert len(result.tools) >= 1
    assert all(hasattr(t, "name") for t in result.tools)


@skip_no_server
async def test_call_tool_unknown(mcp_client: RhinoMCPClient) -> None:
    """Calling a non-existent tool should raise an MCPError."""
    with pytest.raises(MCPError):
        await mcp_client.call_tool("this_tool_does_not_exist", {})


@skip_no_server
async def test_call_tool_known(mcp_client: RhinoMCPClient) -> None:
    """Calling a known tool should return a result with content."""
    tools = await mcp_client.list_tools()
    tool_name = tools.tools[0].name
    result = await mcp_client.call_tool(tool_name, {})
    assert hasattr(result, "content")
    assert isinstance(result.content, list)


@skip_no_server
async def test_double_connect_is_idempotent(mcp_client: RhinoMCPClient) -> None:
    """Connecting twice should not raise."""
    await mcp_client.connect()
    assert mcp_client.is_connected


@skip_no_server
@pytest.mark.asyncio
async def test_disconnect_clears_state() -> None:
    """After disconnect the client should report disconnected state."""
    client = RhinoMCPClient(get_config())
    try:
        await client.connect()
        await client.initialize()
    except MCPError:
        await client.disconnect()
        pytest.skip("MCP server not reachable during test setup")
    assert client.is_connected
    await client.disconnect()
    assert not client.is_connected
    assert not client.is_initialized


@skip_no_server
async def test_list_resources(mcp_client: RhinoMCPClient) -> None:
    """list_resources should return a ResourceListResult (possibly empty)."""
    result = await mcp_client.list_resources()
    assert hasattr(result, "resources")
    assert isinstance(result.resources, list)


@skip_no_server
async def test_list_prompts(mcp_client: RhinoMCPClient) -> None:
    """list_prompts should return a PromptListResult (possibly empty)."""
    result = await mcp_client.list_prompts()
    assert hasattr(result, "prompts")
    assert isinstance(result.prompts, list)


@skip_no_server
async def test_close_alias(mcp_client: RhinoMCPClient) -> None:
    """close() should behave like disconnect()."""
    await mcp_client.close()
    assert not mcp_client.is_connected


@skip_no_server
async def test_initialize_is_idempotent(mcp_client: RhinoMCPClient) -> None:
    """Calling initialize() twice should not raise."""
    result = await mcp_client.initialize()
    assert result.protocolVersion
    assert mcp_client.is_initialized


@pytest.mark.asyncio
async def test_connect_failure_raises_connection_error() -> None:
    """Connecting to an unreachable port must raise an MCP connection error."""
    config = RhinoMCPConfig(host="127.0.0.1", port=1, timeout=0.5)
    client = RhinoMCPClient(config)
    with pytest.raises((MCPConnectionError, MCPTimeoutError)):
        await client.connect()


@pytest.mark.asyncio
async def test_send_without_connect_raises() -> None:
    """Sending a request before connecting must raise MCPConnectionError."""
    client = RhinoMCPClient(get_config())
    with pytest.raises(MCPConnectionError):
        await client.list_tools()


@pytest.mark.asyncio
async def test_read_response_without_connect_raises() -> None:
    """Reading a response without an active connection must raise."""
    client = RhinoMCPClient(get_config())
    with pytest.raises(MCPConnectionError):
        await client._read_response()  # noqa: SLF001


@pytest.mark.asyncio
async def test_send_raw_without_connect_raises() -> None:
    """Sending a raw request without an active connection must raise."""
    client = RhinoMCPClient(get_config())
    request = JSONRPCRequest(id=1, method="ping")
    with pytest.raises(MCPConnectionError):
        await client._send_raw(request)  # noqa: SLF001


