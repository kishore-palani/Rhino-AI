"""Ad-hoc raw TCP probe of the Rhino MCP server. Not part of the test suite."""
from __future__ import annotations

import asyncio
import json


async def main() -> None:
    reader, writer = await asyncio.open_connection("localhost", 8765)
    try:
        # Drain any unsolicited banner first.
        try:
            banner = await asyncio.wait_for(reader.readline(), timeout=3)
            print("BANNER:", banner[:400])
        except asyncio.TimeoutError:
            print("BANNER: (none)")

        for method, params in [
            ("initialize", {"protocolVersion": "2024-11-05",
                            "clientInfo": {"name": "probe", "version": "0.1.0"}}),
            ("tools/list", {}),
        ]:
            req = {"jsonrpc": "2.0", "id": 1 if method == "initialize" else 2,
                   "method": method, "params": params}
            writer.write((json.dumps(req) + "\n").encode())
            await writer.drain()
            line = await asyncio.wait_for(reader.readline(), timeout=10)
            print(f"\n=== {method} ===")
            print(line.decode("utf-8", "replace")[:200000])
    finally:
        writer.close()


asyncio.run(main())
