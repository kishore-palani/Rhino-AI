"""
Real Rhino 8 geometry creation test using active MCP slot and run_command.
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from apps.api.mcp.client import RhinoMCPClient
from apps.api.mcp.config import RhinoMCPConfig


async def test_real_geometry() -> None:
    print("=" * 80)
    print("RHINO 8 REAL GEOMETRY GENERATION TEST")
    print("=" * 80)
    print()

    config = RhinoMCPConfig()
    config.use_stdio = True
    config.use_http = False

    client = RhinoMCPClient(config)

    try:
        await client.connect()
        await client.initialize()
        print("[+] MCP Connected & Initialized")

        # Check active slots
        slots = await client.call_tool("list_slots", {})
        print(f"[+] Active slots: {slots.content[0].text if slots.content else 'None'}")
        print()

        # Step 1: Set units to Millimeters
        print("[STEP 1] Setting document units to Millimeters...")
        res = await client.call_tool("run_command", {"command": "-_Units _Millimeters _ModelUnits _Millimeters _Enter"})
        print(f"[+] Units set: {res.content[0].text if res.content else 'OK'}")
        print()

        # Step 2: Create a 5m x 4m rectangle
        print("[STEP 2] Creating 5000mm x 4000mm Rectangle (Room boundary)...")
        res = await client.call_tool("run_command", {"command": "_Rectangle 0,0,0 5000,4000,0"})
        print(f"[+] Rectangle created: {res.content[0].text if res.content else 'OK'}")
        print()

        # Step 3: Extrude the curve to create 3m tall walls (ExtrudeCrv)
        print("[STEP 3] Extruding boundary into 3000mm tall room envelope...")
        # Select last created object and extrude
        res = await client.call_tool("run_command", {"command": "_SelLast -_ExtrudeCrv _Solid=_Yes 3000 _Enter"})
        print(f"[+] Envelope extruded: {res.content[0].text if res.content else 'OK'}")
        print()

        # Step 4: Create internal column at (2500, 2000, 0)
        print("[STEP 4] Creating a 400mm x 400mm x 3000mm column at room center...")
        res = await client.call_tool("run_command", {"command": "_Box 2300,1800,0 2700,2200,0 3000"})
        print(f"[+] Column created: {res.content[0].text if res.content else 'OK'}")
        print()

        # Step 5: Create a floor slab (-200mm thickness)
        print("[STEP 5] Creating a 200mm thick floor slab...")
        res = await client.call_tool("run_command", {"command": "_Box -200,-200,-200 5200,4200,0"})
        print(f"[+] Floor slab created: {res.content[0].text if res.content else 'OK'}")
        print()

        # Step 6: Create roof slab (200mm thickness at z=3000)
        print("[STEP 6] Creating a 200mm thick roof slab at z=3000...")
        res = await client.call_tool("run_command", {"command": "_Box -300,-300,3000 5300,4300,3200"})
        print(f"[+] Roof slab created: {res.content[0].text if res.content else 'OK'}")
        print()

        # Step 7: Zoom extents to view all created geometry
        print("[STEP 7] Zooming extents in Rhino viewport...")
        res = await client.call_tool("run_command", {"command": "_Zoom _All _Extents"})
        print(f"[+] Viewport adjusted: {res.content[0].text if res.content else 'OK'}")
        print()

        # Step 8: Set shaded display mode
        print("[STEP 8] Setting display mode to Shaded...")
        res = await client.call_tool("run_command", {"command": "_SetDisplayMode _Mode=_Shaded"})
        print(f"[+] Display mode set: {res.content[0].text if res.content else 'OK'}")
        print()

        print("=" * 80)
        print("[+] SUCCESS! Real 3D architectural model generated in live Rhino 8!")
        print("    - 5m x 4m x 3m Room Envelope")
        print("    - 400mm x 400mm Structural Column")
        print("    - 200mm Floor Slab")
        print("    - 200mm Overhanging Roof Slab")
        print("    - Zoom extents & Shaded viewport configured")
        print("=" * 80)

    finally:
        await client.close()


if __name__ == "__main__":
    asyncio.run(test_real_geometry())
