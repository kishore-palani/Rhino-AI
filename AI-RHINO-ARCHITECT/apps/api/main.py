"""FastAPI application entry point."""

from __future__ import annotations

import asyncio
import logging
from datetime import UTC, datetime
from typing import Any

from fastapi import FastAPI
from pydantic import BaseModel, Field

from apps.api.mcp.client import RhinoMCPClient
from apps.api.mcp.config import get_config
from apps.api.mcp.exceptions import MCPError
from ai.memory.project_memory import get_project_memory

logger = logging.getLogger(__name__)


class HealthResponse(BaseModel):
    status: str
    service: str
    timestamp: datetime


class ToolCallRequest(BaseModel):
    name: str = Field(min_length=1)
    arguments: dict[str, Any] = Field(default_factory=dict)


app = FastAPI(
    title="AI Rhino Architect API",
    version="0.1.0",
    description="API for architectural reasoning and Rhino automation.",
)


async def _record_tool_failure(tool_name: str, error: Exception) -> None:
    """Persist a Rhino tool failure without blocking the API event loop."""
    try:
        await asyncio.to_thread(
            get_project_memory().save_failure,
            task=f"Rhino tool call: {tool_name}",
            error=str(error),
            failure_type="rhino_tool",
        )
    except Exception:
        logger.exception("Could not persist failure for Rhino tool %s", tool_name)


@app.get("/", response_model=HealthResponse)
def root() -> HealthResponse:
    return HealthResponse(
        status="ok", service="ai-rhino-architect", timestamp=datetime.now(UTC)
    )


@app.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return root()


@app.get("/ready")
def ready() -> dict[str, Any]:
    config = get_config()
    return {
        "status": "ready",
        "rhino": {
            "transport": "stdio" if config.use_stdio else "tcp",
            "address": None if config.use_stdio else config.tcp_address,
        },
    }


@app.post("/rhino/tools/call")
async def call_rhino_tool(request: ToolCallRequest) -> dict[str, Any]:
    """Forward one tool call to Rhino MCP when a server is available."""
    client = RhinoMCPClient(get_config())
    try:
        await client.connect()
        await client.initialize()
        result = await client.call_tool(request.name, request.arguments)
        return result.model_dump(by_alias=True, exclude_none=True)
    except MCPError as error:
        await _record_tool_failure(request.name, error)
        return {
            "status": "error",
            "message": str(error),
            "retryable": bool(getattr(error, "isRetryable", False)),
        }
    except Exception as error:
        await _record_tool_failure(request.name, error)
        raise
    finally:
        await client.close()
