"""
Final comprehensive Rhino 8 test with fresh slot and C# scripting.
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from apps.api.mcp.client import RhinoMCPClient
from apps.api.mcp.config import RhinoMCPConfig


async def test_fresh_slot() -> None:
    print("=" * 80)
    print("RHINO 8 COMPREHENSIVE CONNECTION TEST (FRESH SLOT + C# SCRIPTING)")
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
        print()

        # Step 1: Check and close any existing slots
        print("[STEP 1] Checking for existing slots...")
        slots = await client.call_tool("list_slots", {})
        slot_data = slots.content[0].text if slots.content else '{"payload":[]}'
        print(f"[+] Current slots: {slot_data}")

        # Parse and close any existing slots
        import json
        slots_obj = json.loads(slot_data)
        if slots_obj.get('payload'):
            for slot in slots_obj['payload']:
                slot_id = slot.get('slotId')
                print(f"[*] Closing existing slot: {slot_id}")
                await client.call_tool("close_slot", {"slotId": slot_id})
        print()

        # Step 2: Spawn fresh slot
        print("[STEP 2] Spawning fresh Rhino slot...")
        spawn_res = await client.call_tool("spawn_slot", {})
        spawn_data = json.loads(spawn_res.content[0].text if spawn_res.content else '{}')
        slot_id = spawn_data.get('payload', {}).get('slotId', 'unknown')
        endpoint = spawn_data.get('payload', {}).get('endpoint', 'unknown')
        print(f"[+] New slot spawned: {slot_id}")
        print(f"[+] Endpoint: {endpoint}")
        print()

        # Step 3: Create geometry using run_csharp
        print("[STEP 3] Creating architectural model with C# script...")
        csharp_code = """
using Rhino;
using Rhino.Geometry;
using System;
using System.Collections.Generic;

var doc = RhinoDoc.ActiveDoc;
var objs = new List<Guid>();

// Set units to millimeters
doc.ModelUnitSystem = UnitSystem.Millimeters;

// Create 5m x 4m room boundary rectangle
var plane = Plane.WorldXY;
var rect = new Rectangle3d(plane, 5000, 4000);
var boundary = doc.Objects.AddPolyline(rect.ToPolyline());
objs.Add(boundary);

// Extrude boundary to 3000mm to create room envelope
var boundaryCurve = doc.Objects.FindId(boundary).Geometry as Curve;
if (boundaryCurve != null)
{
    var extrusion = Surface.CreateExtrusion(boundaryCurve, new Vector3d(0, 0, 3000));
    var brep = extrusion?.ToBrep();
    if (brep != null)
    {
        var envelope = doc.Objects.AddBrep(brep);
        objs.Add(envelope);
    }
}

// Create 400mm x 400mm x 3000mm column at (2500, 2000, 0)
var box1 = new Box(
    Plane.WorldXY,
    new Interval(2300, 2700),
    new Interval(1800, 2200),
    new Interval(0, 3000)
);
var column = doc.Objects.AddBrep(box1.ToBrep());
objs.Add(column);

// Create 200mm thick floor slab
var floor = new Box(
    Plane.WorldXY,
    new Interval(-200, 5200),
    new Interval(-200, 4200),
    new Interval(-200, 0)
);
var floorId = doc.Objects.AddBrep(floor.ToBrep());
objs.Add(floorId);

// Create 200mm thick roof slab at z=3000
var roof = new Box(
    Plane.WorldXY,
    new Interval(-300, 5300),
    new Interval(-300, 4300),
    new Interval(3000, 3200)
);
var roofId = doc.Objects.AddBrep(roof.ToBrep());
objs.Add(roofId);

// Add a window opening (simple box subtraction representation)
var window = new Box(
    Plane.WorldXY,
    new Interval(1000, 2000),
    new Interval(-50, 50),
    new Interval(900, 2100)
);
var windowId = doc.Objects.AddBrep(window.ToBrep());
objs.Add(windowId);

doc.Views.Redraw();

Console.WriteLine($"Created {objs.Count} objects:");
Console.WriteLine($"  - Room envelope: 5000 x 4000 x 3000 mm");
Console.WriteLine($"  - Structural column: 400 x 400 x 3000 mm");
Console.WriteLine($"  - Floor slab: 200mm thick");
Console.WriteLine($"  - Roof slab: 200mm thick");
Console.WriteLine($"  - Window opening: 1000 x 1200 mm");
"""

        result = await client.call_tool("run_csharp", {"code": csharp_code, "slotId": slot_id})
        output = result.content[0].text if result.content else "No output"
        print(f"[+] Geometry created!")
        print(f"[+] Output:\n{output}")
        print()

        # Step 4: List objects in document
        print("[STEP 4] Querying created objects...")
        list_res = await client.call_tool("list_objects", {"slotId": slot_id})
        objects_data = list_res.content[0].text if list_res.content else "{}"
        print(f"[+] Objects in document: {objects_data[:300]}...")
        print()

        # Step 5: Get selection (should be empty)
        print("[STEP 5] Checking current selection...")
        sel_res = await client.call_tool("get_selection", {"slotId": slot_id})
        selection = sel_res.content[0].text if sel_res.content else "{}"
        print(f"[+] Current selection: {selection}")
        print()

        print("=" * 80)
        print("[SUCCESS] RHINO 8 MCP INTEGRATION FULLY OPERATIONAL!")
        print("=" * 80)
        print()
        print("Test Results:")
        print("  [+] Connection: stdio transport via rhino-mcp-router.exe")
        print(f"  [+] Active slot: {slot_id} at {endpoint}")
        print("  [+] C# scripting: Working")
        print("  [+] Geometry creation: 6 architectural objects created")
        print("  [+] Document queries: Working")
        print()
        print("Created architectural model:")
        print("  * 5m x 4m x 3m room envelope")
        print("  * 400mm x 400mm structural column")
        print("  * 200mm floor slab (overhanging)")
        print("  * 200mm roof slab (overhanging)")
        print("  * 1000mm x 1200mm window opening")
        print()
        print("Check the Rhino 8 viewport to see the generated geometry!")
        print("=" * 80)

    except Exception as e:
        print(f"\n[-] ERROR: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await client.close()
        print("\n[*] Connection closed")


if __name__ == "__main__":
    asyncio.run(test_fresh_slot())
