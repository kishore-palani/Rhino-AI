# AI RHINO ARCHITECT — Issues & Blockers

Current known bugs, technical debt, and blocker issues.

---

## Open Issues

| ID | Severity | Area | Description | Status |
|---|---|---|---|---|

---

## Resolved Issues

| ID | Area | Description | Resolution | Date |
|---|---|---|---|---|
| `ISSUE-004` | Kilo Config | Session model `nvidia/llama-3.3-70b-instruct` failed with HTTP 400 — NVIDIA NIM removed that model from its live catalog (82 live models, no `llama-3.3-70b-instruct`) | Pinned project defaults in `.kilo/kilo.jsonc` to the live Free LLM API entries `freellmapi/llama-3.3-70b-instruct` and `freellmapi/llama-3.2-3b`; both verified with a live chat-completions call. Verified-live NVIDIA fallbacks: `nvidia/nemotron-3-super-120b-a12b`, `nvidia/nemotron-3-ultra-550b-a55b` | 2026-09-26 |
| `ISSUE-003` | Git | Repository had no initial commit and project files were untracked | Created the initial commit with project files; local secrets, state, caches, and session notes are excluded | 2026-09-26 |
| `ISSUE-002` | Memory | AgentMemory local service (http://localhost:3111) must be running via `start-agentmemory.ps1` for memory integration tests | Launcher now waits for health; AgentMemory was started and `/agentmemory/health` returned HTTP 200 | 2026-09-26 |
| `ISSUE-001` | MCP Integration | Live Rhino MCP server connection is pending validation against a real running Rhino 8 instance | Validated live Rhino 8 via stdio transport (rhino-mcp-router.exe) and spawned slot with real 3D geometry creation (7 objects) | 2026-09-26 |
| `FIX-001` | Units | Dimensional unit mismatch between user input and Rhino document units | `RhinoDoc.ActiveDoc.ModelUnitSystem` made authoritative; explicit unit conversion pipeline added | Historical (V0.9.3.1) |
| `FIX-002` | Retry | Provider retry failing on JSON-shaped API errors | Added recognition for structured error shapes in retry logic | Historical (Phase 1) |
