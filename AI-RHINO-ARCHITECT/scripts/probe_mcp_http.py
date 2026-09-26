"""Ad-hoc HTTP probe of the Rhino MCP server. Not part of the test suite."""
from __future__ import annotations

import json
import urllib.request


def call(method: str, params: dict, ident: int) -> dict:
    body = json.dumps({"jsonrpc": "2.0", "id": ident, "method": method,
                       "params": params}).encode()
    req = urllib.request.Request(
        "http://localhost:8765/",
        data=body,
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode())


init = call("initialize", {"protocolVersion": "2024-11-05",
                           "clientInfo": {"name": "probe", "version": "0.1.0"}}, 1)
print("=== initialize ===")
print(json.dumps(init, indent=2)[:2000])

tools = call("tools/list", {}, 2)
names = [t["name"] for t in tools.get("result", {}).get("tools", [])]
print("\n=== tool count:", len(names), "===")
print(json.dumps(names, indent=2))

wanted = ["run_python", "run_csharp", "create_object", "create_objects",
          "extrude_curve", "loft", "sweep1", "cap_brep", "analyze_objects",
          "list_objects", "get_selection", "set_selection",
          "get_viewport_image", "zoom_to_object"]
print("\n=== wanted missing:", sorted(set(wanted) - set(names)))
print("\n=== schemas for wanted tools ===")
for t in tools.get("result", {}).get("tools", []):
    if t["name"] in wanted:
        print(f"\n--- {t['name']} ---")
        print(json.dumps(t.get("inputSchema", {}), indent=2)[:4000])
