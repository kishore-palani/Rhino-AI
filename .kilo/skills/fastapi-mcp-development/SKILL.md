---
name: fastapi-mcp-development
description: Use when changing AI RHINO ARCHITECT's FastAPI routes, Pydantic schemas, provider integrations, JSON-RPC/MCP client, SSE behavior, or API tests.
---

# FastAPI and MCP Development

## Follow the project boundary

- Routes and application lifecycle are under `AI-RHINO-ARCHITECT/apps/api/`.
- Rhino MCP client, configuration, models, and errors are under
  `AI-RHINO-ARCHITECT/apps/api/mcp/`.
- Rhino adapter interfaces and implementations are under
  `AI-RHINO-ARCHITECT/rhino/adapters/`.
- Use the existing Pydantic models, async patterns, and exception mapping.
  Avoid creating a second client or a competing transport abstraction.
- Kilo's `rhino` MCP server is direct tooling for the coding agent; it is not
  the application's API client and must not be represented as an API route.

## Implementation

1. Trace the request from route or tool entrypoint to the owning service/client.
2. Validate untrusted values at the boundary and preserve stable response/error
   contracts.
3. Keep network operations asynchronous and bounded by existing timeout/retry
   configuration.
4. Do not expose arbitrary shell, Rhino command, Rhinoscript, or C# execution to
   untrusted API callers. Keep secret values out of logs and responses.
5. Prefer dependency injection or existing app state over hidden global
   connections when writing tests.

## Validation

Add a narrow unit regression test under `AI-RHINO-ARCHITECT/tests/unit/` for
normal, invalid, and failure-path behavior as applicable. Keep integration tests
under `tests/integration/` isolated from live Rhino/network services. Run the
focused pytest test first, then follow `AGENTS.md` and the CI workflow for wider
checks. Use current official FastAPI and MCP documentation when an API behavior
or protocol version is uncertain.