"""MCP client for Rhino - JSON-RPC 2.0 over TCP, stdio, and HTTP."""

from __future__ import annotations

import asyncio
import json
import logging
import shlex
from typing import Any

import httpx

from ai.providers.retry import with_provider_retries

from .config import RhinoMCPConfig, get_config
from .exceptions import (
    MCPConnectionError,
    MCPError,
    MCPMethodNotAvailableError,
    MCPProtocolError,
    MCPTimeoutError,
    error_from_jsonrpc_error,
)
from .models import (
    CallToolRequestParams,
    CallToolResult,
    InitializeRequestParams,
    InitializeResult,
    JSONRPCErrorResponse,
    JSONRPCRequest,
    JSONRPCResponse,
    JSONRPCSuccessResponse,
    ListToolsRequestParams,
    PromptListResult,
    ReadResourceResult,
    ResourceListResult,
    ToolListResult,
)

logger = logging.getLogger(__name__)


class RhinoMCPClient:
    """Async MCP client for Rhino MCP server.

    Supports TCP (default localhost:8765), stdio, and HTTP transports.
    Implements JSON-RPC 2.0 and MCP protocol methods.
    """

    def __init__(self, config: RhinoMCPConfig | None = None) -> None:
        self._config = config or get_config()
        self._reader: asyncio.StreamReader | None = None
        self._writer: asyncio.StreamWriter | None = None
        self._process: asyncio.subprocess.Process | None = None
        self._http_client: httpx.AsyncClient | None = None
        self._request_id: int = 0
        self._initialized: bool = False
        self._connected: bool = False
        self._receive_lock = asyncio.Lock()

    @property
    def is_connected(self) -> bool:
        return self._connected

    @property
    def is_initialized(self) -> bool:
        return self._initialized

    def _next_request_id(self) -> int:
        self._request_id += 1
        return self._request_id

    def _make_request(self, method: str, params: dict[str, Any] | None = None) -> JSONRPCRequest:
        """Create a JSON-RPC 2.0 request with unique ID."""
        return JSONRPCRequest(
            id=self._next_request_id(),
            method=method,
            params=params,
        )

    async def connect(self) -> None:
        """Establish connection to Rhino MCP server via TCP, stdio, or HTTP."""
        if self._connected:
            logger.debug("Already connected")
            return

        if self._config.use_stdio:
            await self._connect_stdio()
        elif self._config.use_http:
            await self._connect_http()
        else:
            await self._connect_tcp()

        self._connected = True
        if self._config.use_stdio:
            transport = "stdio"
        elif self._config.use_http:
            transport = self._config.http_url
        else:
            transport = f"tcp://{self._config.tcp_address}"
        logger.info("Connected to Rhino MCP server (%s)", transport)

    async def _connect_tcp(self) -> None:
        """Connect via TCP socket."""
        try:
            self._reader, self._writer = await asyncio.wait_for(
                asyncio.open_connection(self._config.host, self._config.port),
                timeout=self._config.timeout,
            )
        except asyncio.TimeoutError as exc:
            raise MCPTimeoutError(f"TCP connection timeout to {self._config.tcp_address}", elapsed=self._config.timeout) from exc
        except OSError as exc:
            raise MCPConnectionError(
                f"Failed to connect to {self._config.tcp_address}: {exc}",
                host=self._config.host,
                port=self._config.port,
            ) from exc

    async def _connect_http(self) -> None:
        """Connect via HTTP."""
        try:
            self._http_client = httpx.AsyncClient(
                base_url=self._config.http_url,
                timeout=httpx.Timeout(self._config.timeout),
            )
            # Test connection with a simple request
            response = await self._http_client.post(
                "/",
                json={"jsonrpc": "2.0", "id": 0, "method": "initialize", "params": {}},
            )
            response.raise_for_status()
        except httpx.TimeoutException as exc:
            raise MCPTimeoutError(f"HTTP connection timeout to {self._config.http_url}", elapsed=self._config.timeout) from exc
        except httpx.RequestError as exc:
            raise MCPConnectionError(
                f"Failed to connect to {self._config.http_url}: {exc}",
            ) from exc

    async def _connect_stdio(self) -> None:
        """Connect via stdio subprocess."""
        try:
            self._process = await asyncio.create_subprocess_exec(
                *shlex.split(self._config.stdio_command, posix=False),
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            self._reader = self._process.stdout
            self._writer = self._process.stdin
        except OSError as exc:
            raise MCPConnectionError(
                f"Failed to start MCP server via stdio: {exc}",
            ) from exc

    async def disconnect(self) -> None:
        """Close connection and cleanup resources."""
        if not self._connected:
            return

        try:
            if self._writer and not self._writer.is_closing():
                self._writer.close()
                await asyncio.wait_for(self._writer.wait_closed(), timeout=2.0)
        except Exception as exc:
            logger.warning("Error closing writer: %s", exc)

        if self._process:
            try:
                self._process.terminate()
                await asyncio.wait_for(self._process.wait(), timeout=3.0)
            except asyncio.TimeoutError:
                self._process.kill()
                await self._process.wait()
            except Exception as exc:
                logger.warning("Error terminating process: %s", exc)

        if self._http_client:
            try:
                await self._http_client.aclose()
            except Exception as exc:
                logger.warning("Error closing HTTP client: %s", exc)

        self._reader = None
        self._writer = None
        self._process = None
        self._http_client = None
        self._connected = False
        self._initialized = False
        logger.info("Disconnected from Rhino MCP server")

    async def close(self) -> None:
        """Alias for disconnect."""
        await self.disconnect()

    async def _send_raw(self, request: JSONRPCRequest) -> None:
        """Send raw JSON-RPC request over the transport."""
        if not self._connected:
            raise MCPConnectionError("Not connected to MCP server")

        if self._config.use_http:
            await self._send_http(request)
        else:
            await self._send_tcp_stdio(request)

    async def _send_tcp_stdio(self, request: JSONRPCRequest) -> None:
        """Send request over TCP or stdio."""
        if not self._writer:
            raise MCPConnectionError("Not connected to MCP server")

        data = request.model_dump_json(exclude_none=True, by_alias=True) + "\n"
        try:
            self._writer.write(data.encode("utf-8"))
            await self._writer.drain()
        except OSError as exc:
            self._connected = False
            raise MCPConnectionError(f"Failed to send request: {exc}") from exc

    async def _send_http(self, request: JSONRPCRequest) -> None:
        """Send request over HTTP."""
        if not self._http_client:
            raise MCPConnectionError("HTTP client not initialized")

        data = request.model_dump(exclude_none=True, by_alias=True)
        try:
            response = await self._http_client.post("/", json=data)
            response.raise_for_status()
            # Store response for reading
            self._last_http_response = response
        except httpx.TimeoutException as exc:
            self._connected = False
            raise MCPTimeoutError(f"HTTP request timeout: {exc}", elapsed=self._config.timeout) from exc
        except httpx.RequestError as exc:
            self._connected = False
            raise MCPConnectionError(f"Failed to send HTTP request: {exc}") from exc

    async def _read_response(self) -> JSONRPCResponse:
        """Read and parse a JSON-RPC response."""
        if not self._connected:
            raise MCPConnectionError("Not connected to MCP server")

        if self._config.use_http:
            return await self._read_http_response()
        else:
            return await self._read_tcp_stdio_response()

    async def _read_tcp_stdio_response(self) -> JSONRPCResponse:
        """Read response from TCP or stdio."""
        async with self._receive_lock:
            try:
                line = await asyncio.wait_for(self._reader.readline(), timeout=self._config.timeout)
            except asyncio.TimeoutError as exc:
                raise MCPTimeoutError("Response timeout", elapsed=self._config.timeout) from exc

        if not line:
            raise MCPConnectionError("Connection closed by server")

        try:
            data = json.loads(line.decode("utf-8"))
        except json.JSONDecodeError as exc:
            raise MCPProtocolError(f"Invalid JSON response: {exc}", raw=line.decode("utf-8")) from exc

        if "error" in data:
            return JSONRPCErrorResponse.model_validate(data)
        return JSONRPCSuccessResponse.model_validate(data)

    async def _read_http_response(self) -> JSONRPCResponse:
        """Read response from HTTP."""
        if not hasattr(self, "_last_http_response") or self._last_http_response is None:
            raise MCPProtocolError("No HTTP response available")

        response = self._last_http_response
        self._last_http_response = None

        try:
            data = response.json()
        except json.JSONDecodeError as exc:
            raise MCPProtocolError(f"Invalid JSON response: {exc}", raw=response.text) from exc

        if "error" in data:
            return JSONRPCErrorResponse.model_validate(data)
        return JSONRPCSuccessResponse.model_validate(data)

    async def _send_request(self, method: str, params: dict[str, Any] | None = None) -> JSONRPCResponse:
        """Send a request and wait for response with retry logic."""

        async def _operation() -> JSONRPCResponse:
            request = self._make_request(method, params)
            await self._send_raw(request)
            return await self._read_response()

        try:
            return await with_provider_retries(
                _operation,
                max_retries=self._config.max_retries,
                retry_backoff=self._config.retry_backoff,
            )
        except MCPError:
            raise
        except Exception as exc:
            raise MCPError(f"Request failed: {exc}") from exc

    def _handle_response(self, response: JSONRPCResponse) -> Any:
        """Process response, raise on error."""
        if isinstance(response, JSONRPCErrorResponse):
            error = response.error
            raise error_from_jsonrpc_error(error.code, error.message, error.data)
        return response.result

    async def initialize(self) -> InitializeResult:
        """Initialize MCP protocol handshake."""
        if self._initialized:
            logger.debug("Already initialized")
            return InitializeResult(
                protocolVersion="2024-11-05",
                capabilities={},
                serverInfo={"name": "RhinoMCP", "version": "0.1.0"},
            )

        params = InitializeRequestParams(
            protocolVersion="2024-11-05",
            clientInfo={"name": "RhinoMCPClient", "version": "0.1.0"},
        ).model_dump(exclude_none=True, by_alias=True)

        response = await self._send_request("initialize", params)
        result = self._handle_response(response)

        self._initialized = True
        return InitializeResult.model_validate(result)

    async def list_tools(self, cursor: str | None = None) -> ToolListResult:
        """List available tools from MCP server."""
        params = ListToolsRequestParams(cursor=cursor).model_dump(exclude_none=True, by_alias=True)
        response = await self._send_request("tools/list", params)
        result = self._handle_response(response)
        return ToolListResult.model_validate(result)

    async def call_tool(self, name: str, arguments: dict[str, Any] | None = None) -> CallToolResult:
        """Call a tool on the MCP server."""
        params = CallToolRequestParams(name=name, arguments=arguments or {}).model_dump(exclude_none=True, by_alias=True)
        response = await self._send_request("tools/call", params)
        result = self._handle_response(response)
        return CallToolResult.model_validate(result)

    async def list_resources(self, cursor: str | None = None) -> ResourceListResult:
        """List available resources.

        ``resources`` is an optional MCP capability; servers that don't
        implement it respond with "method not found", treated as empty.
        """
        params = {"cursor": cursor} if cursor else None
        response = await self._send_request("resources/list", params)
        try:
            result = self._handle_response(response)
        except MCPMethodNotAvailableError:
            return ResourceListResult(resources=[])
        return ResourceListResult.model_validate(result)

    async def read_resource(self, uri: str) -> ReadResourceResult:
        """Read a resource by URI."""
        params = {"uri": uri}
        response = await self._send_request("resources/read", params)
        result = self._handle_response(response)
        return ReadResourceResult.model_validate(result)

    async def list_prompts(self, cursor: str | None = None) -> PromptListResult:
        """List available prompts.

        ``prompts`` is an optional MCP capability. Servers that do not
        implement it respond with a JSON-RPC "method not found" error, which
        is treated here as "no prompts available" rather than a hard failure.
        """
        params = {"cursor": cursor} if cursor else None
        response = await self._send_request("prompts/list", params)
        try:
            result = self._handle_response(response)
        except MCPMethodNotAvailableError:
            return PromptListResult(prompts=[])
        return PromptListResult.model_validate(result)

    async def get_prompt(self, name: str, arguments: dict[str, Any] | None = None) -> dict[str, Any]:
        """Get a prompt by name."""
        params = {"name": name, "arguments": arguments or {}}
        response = await self._send_request("prompts/get", params)
        return self._handle_response(response)