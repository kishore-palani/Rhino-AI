"""
Diagnose Rhino MCP connection and test alternative tools.
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from apps.api.mcp.client import RhinoMCPClient
from apps.api.mcp.config import RhinoMCPConfig


async def diagnose() -> None:
    print("=" * 80)
    print("RHINO MCP DIAGNOSTIC TEST")
    print("=" * 80)
    print()

    config = RhinoMCPConfig()
    config.use_stdio = True
    config.use_http = False

    client = RhinoMCPClient(config)

    try:
        await client.connect()
        await client.initialize()
        print("[+] Connected and initialized")
        print()

        # Test 1: List slots (Rhino documents)
        print("[TEST 1] List active Rhino slots/documents...")
        try:
            result = await client.call_tool("list_slots", {})
            print(f"[+] Slots found: {result.content[0].text if result.content else 'No slots'}")
        except Exception as e:
            print(f"[-] Error: {e}")
        print()

        # Test 2: Try spawning a slot
        print("[TEST 2] Spawn a new Rhino document slot...")
        try:
            result = await client.call_tool("spawn_slot", {})
            print(f"[+] Result: {result.content[0].text if result.content else 'No response'}")
        except Exception as e:
            print(f"[-] Error: {e}")
        print()

        # Test 3: Try run_command (safer than run_python)
        print("[TEST 3] Run a simple Rhino command (Point at origin)...")
        try:
            result = await client.call_tool("run_command", {"command": "_Point 0,0,0"})
            print(f"[+] Command result: {result.content[0].text if result.content else 'Executed'}")
        except Exception as e:
            print(f"[-] Error: {e}")
        print()

        # Test 4: Try to get viewport image
        print("[TEST 4] Get viewport screenshot...")
        try:
            result = await client.call_tool("get_viewport_image", {"format": "png"})
            if result.content:
                print(f"[+] Got image data: {len(result.content[0].text)} bytes")
            else:
                print("[-] No image returned")
        except Exception as e:
            print(f"[-] Error: {e}")
        print()

        # Test 5: Check what run_python actually returns
        print("[TEST 5] Debug run_python error detail...")
        try:
            result = await client.call_tool("run_python", {"code": "print('Hello from Rhino')"})
            print(f"[+] Success: {result.content[0].text if result.content else 'No output'}")
        except Exception as e:
            print(f"[-] Exception type: {type(e).__name__}")
            print(f"[-] Exception message: {e}")
            import traceback
            traceback.print_exc()
        print()

        # Test 6: List available commands
        print("[TEST 6] Get available Rhino commands...")
        try:
            result = await client.call_tool("get_commands", {})
            commands = result.content[0].text if result.content else "None"
            print(f"[+] Commands available: {commands[:200]}...")
        except Exception as e:
            print(f"[-] Error: {e}")
        print()

    finally:
        await client.close()
        print()
        print("[*] Diagnostic complete")


if __name__ == "__main__":
    asyncio.run(diagnose())
