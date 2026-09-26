"""Custom exception hierarchy for the Rhino MCP client.

Every error raised by the client derives from :class:`MCPError` so callers can
``except MCPError`` to catch every client-side or protocol-level failure while
still being able to handle specific cases individually.
"""

from __future__ import annotations

from typing import Any, Optional


class MCPError(Exception):
    """Base exception for all Rhino MCP client errors."""

    def __init__(self, message: str = "", **kwargs: Any) -> None:
        super().__init__(message)
        self.message = message
        for key, value in kwargs.items():
            setattr(self, key, value)

    def __str__(self) -> str:
        return self.message or self.__class__.__name__


class MCPConnectionError(MCPError):
    """The client could not establish or maintain a TCP connection."""

    def __init__(
        self,
        message: str = "",
        *,
        host: Optional[str] = None,
        port: Optional[int] = None,
    ) -> None:
        super().__init__(message, host=host, port=port)
        self.host = host
        self.port = port


class MCPTimeoutError(MCPError):
    """A request exceeded the configured timeout."""

    def __init__(
        self,
        message: str = "",
        *,
        elapsed: Optional[float] = None,
        request_id: Optional[int] = None,
    ) -> None:
        super().__init__(message, elapsed=elapsed, request_id=request_id)
        self.elapsed = elapsed
        self.request_id = request_id
        self.isRetryable = True


class MCPProtocolError(MCPError):
    """A JSON-RPC 2.0 or MCP framing violation was detected on the wire."""

    def __init__(
        self,
        message: str = "",
        *,
        raw: Optional[str] = None,
        code: Optional[int] = None,
    ) -> None:
        super().__init__(message, raw=raw, code=code)
        self.raw = raw
        self.code = code


class MCPAuthenticationError(MCPError):
    """Authentication or authorization failed against the MCP server."""


class MCPUnavailableError(MCPError):
    """The MCP server is temporarily unavailable (e.g. still initializing)."""


class MCPNotFoundError(MCPError):
    """The requested method, tool, or resource was not found."""


class MCPRateLimitError(MCPError):
    """The server rate-limited the request."""

    def __init__(self, message: str = "", *, retry_after: Optional[float] = None) -> None:
        super().__init__(message, retry_after=retry_after)
        self.retry_after = retry_after
        self.isRetryable = True


class MCPMethodNotAvailableError(MCPError):
    """The server does not implement the requested JSON-RPC method."""


class MCPRequestCancelledError(MCPError):
    """The in-flight request was cancelled by the caller."""


class MCPToolError(MCPError):
    """A tool invocation completed but reported an application-level error.

    The underlying MCP ``tools/call`` response carried ``isError: true`` or the
    server returned a JSON-RPC error object.  The structured ``data`` payload
    (when present) is preserved for inspection.
    """

    def __init__(
        self,
        message: str = "",
        *,
        tool_name: Optional[str] = None,
        data: Any = None,
    ) -> None:
        super().__init__(message, tool_name=tool_name, data=data)
        self.tool_name = tool_name
        self.data = data
        self.error_code: Optional[int] = None


class MCPInvalidParamsError(MCPError):
    """The arguments supplied to ``tools/call`` failed validation (-32602)."""


class MCPInternalError(MCPError):
    """The server hit an internal error (-32603)."""


def error_from_jsonrpc_error(
    code: int,
    message: str,
    data: Any = None,
) -> MCPError:
    """Map a JSON-RPC error response to the appropriate client exception."""
    if code == -32700:
        return MCPProtocolError(message, code=code, raw=data)
    if code == -32600:
        return MCPProtocolError(message, code=code, raw=data)
    if code == -32601:
        return MCPMethodNotAvailableError(message)
    if code == -32602:
        return MCPInvalidParamsError(message)
    if code == -32603:
        return MCPInternalError(message)
    if code == -32000:
        return MCPUnavailableError(message)
    if code == -32001:
        return MCPAuthenticationError(message)
    if code == -32003:
        return MCPNotFoundError(message)
    if code == -32004:
        return MCPRateLimitError(message, retry_after=data)
    return MCPError(message)