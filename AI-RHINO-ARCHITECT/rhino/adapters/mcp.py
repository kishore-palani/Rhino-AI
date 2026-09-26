"""Rhino adapter backed by the API project's MCP client."""

from __future__ import annotations

from typing import Any

from apps.api.mcp.client import RhinoMCPClient
from apps.api.mcp.config import RhinoMCPConfig
from apps.api.mcp.exceptions import MCPToolError
from rhino.adapters.base import RhinoAdapter


class MCPRhinoAdapter(RhinoAdapter):
    """Execute Rhino tools through an MCP server."""

    def __init__(self, config: RhinoMCPConfig) -> None:
        self._client = RhinoMCPClient(config)

    async def call_tool(self, name: str, arguments: dict[str, Any]) -> Any:
        result = await self._client.call_tool(name, arguments)
        if getattr(result, "isError", False):
            raise MCPToolError(
                f"Tool '{name}' returned an error",
                tool_name=name,
                data=result.model_dump(by_alias=True, exclude_none=True),
            )
        return result.model_dump(by_alias=True, exclude_none=True)

    async def close(self) -> None:
        await self._client.close()