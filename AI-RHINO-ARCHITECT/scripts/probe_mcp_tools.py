"""Ad-hoc probe: list live MCP tool schemas. Not part of the test suite."""
from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[0]))

from apps.api.mcp.client import RhinoMCPClient
from apps.api.mcp.config import RhinoMCPConfig


async def main() -> None:
    client = RhinoMCPClient(RhinoMCPConfig())
    await client.connect()
    await client.initialize()
    result = await client.list_tools()
    wanted = {
        "run_python", "run_csharp", "create_object", "create_objects",
        "extrude_curve", "loft", "sweep1", "cap_brep", "analyze_objects",
        "list_objects", "get_selection", "set_selection",
        "get_viewport_image", "zoom_to_object",
    }
    for tool in result.tools:
        mark = "*" if tool.name in wanted else " "
        print(f"{mark} {tool.name}: {json.dumps(tool.inputSchema)}")
    print("\n--- present:", sorted(t.name for t in result.tools))
    print("--- wanted missing:", sorted(wanted - {t.name for t in result.tools}))
    await client.close()


asyncio.run(main())
