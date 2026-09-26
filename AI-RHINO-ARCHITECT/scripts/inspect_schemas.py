"""
Check exact tool parameter schemas from Rhino MCP server.
"""

from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from apps.api.mcp.client import RhinoMCPClient
from apps.api.mcp.config import RhinoMCPConfig


async def inspect_schemas() -> None:
    config = RhinoMCPConfig()
    config.use_stdio = True
    config.use_http = False

    client = RhinoMCPClient(config)
    try:
        await client.connect()
        await client.initialize()
        tools_result = await client.list_tools()
        for tool in tools_result.tools:
            if tool.name in ["run_csharp", "run_python", "run_command", "open_doc", "spawn_slot", "list_objects"]:
                print(f"Tool: {tool.name}")
                print(f"Description: {tool.description}")
                print(f"InputSchema: {json.dumps(tool.inputSchema, indent=2)}")
                print("-" * 60)
    finally:
        await client.close()


if __name__ == "__main__":
    asyncio.run(inspect_schemas())
