---
name: rhino8-api-development
description: Use when researching or implementing Rhino 8 or Grasshopper integrations, RhinoCommon C# plugin code, Rhino MCP operations, geometry generation, or API compatibility.
---

# Rhino 8 and Grasshopper API Work

## Choose the correct integration surface

- For live document operations, use the connected Kilo Rhino MCP tools and
  inspect their current tool descriptions and schemas before calling them.
- For the application's service layer, use `AI-RHINO-ARCHITECT/apps/api/mcp/`
  and its existing `RhinoMCPClient`; this is separate from Kilo's MCP process.
- For plugin implementation, use RhinoCommon or Grasshopper APIs in the owning
  plugin project. Do not substitute arbitrary Rhino command strings for typed
  geometry operations without a specific reason.
- Reuse modeling contracts in `AI-RHINO-ARCHITECT/knowledge/skills/*.json`;
  these runtime contracts are not Kilo instruction skills.

## Verify current APIs

Use Kilo's `websearch` and `webfetch` tools to check the official documentation
for the Rhino version targeted by the owning project. Start with:

- RhinoCommon: https://developer.rhino3d.com/api/rhinocommon/
- Rhino API index: https://developer.rhino3d.com/en/api/
- Developer guides: https://developer.rhino3d.com/guides/
- Official samples: https://developer.rhino3d.com/samples/

Inspect the relevant project file and plugin source to confirm target framework,
assembly references, namespaces, method overloads, and supported Rhino version.
Prefer current API reference pages and official samples over copied snippets or
unverified model memory. Check units and document tolerances when they affect
geometry.

## Safe execution and validation

- Validate modeling-skill inputs before mutation and validate created geometry
  afterward.
- Keep document clearing, deletion, saving, and arbitrary script execution
  approval-gated; never perform them unless the user requested the action.
- Add deterministic tests around pure geometry conversion and validation logic.
- Run live Rhino checks only when Rhino and its MCP plugin are available, and
  report them separately from ordinary pytest results.