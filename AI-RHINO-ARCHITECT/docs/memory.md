# Project Memory Integration

AI RHINO ARCHITECT uses the local AgentMemory REST service for project state,
failures, lessons, and user feedback. This service is separate from the
application's Rhino MCP connection.

## Service

The Python client defaults to `http://localhost:3111/agentmemory`. Construct an
`AgentMemoryClient(base_url=...)` to use another base URL. The client uses
synchronous `urllib` requests with a 30-second timeout. HTTP and transport
errors are logged and returned as `{"success": false, "error": ...}` rather
than raised. The API currently has no authentication configuration in this
wrapper.

## Client API

`ai.memory.agentmemory_client.AgentMemoryClient` exposes these operations:

| Method | AgentMemory endpoint | Purpose |
|---|---|---|
| `start_session` / `end_session` | `POST /session/start`, `POST /session/end` | Track an agent session. |
| `remember` | `POST /remember` | Save typed project memory with concepts, files, and optional TTL. |
| `recall` | `POST /search` | Search project memories. |
| `smart_search` | `POST /smart-search` | Hybrid memory search. |
| `forget` | `POST /forget` | Remove a memory or session. |
| `save_lesson` / `search_lessons` | `POST /lessons`, `POST /lessons/search` | Save and retrieve reusable lessons. |
| `health` / `is_available` | `GET /health`, `GET /livez` | Check service health or liveness. |

`get_client()` returns a process-wide client singleton. Module-level
`remember()` and `recall()` are convenience wrappers around that singleton.

## Project Memory Helpers

`ai.memory.project_memory.ProjectMemory` wraps an `AgentMemoryClient` with
project-specific operations. Pass a client to its constructor for tests or
custom configuration; `get_project_memory()` returns the process-wide default.

- `save_project_state(phase, status, details)` stores a `state` memory.
- `save_failure(task, error, failure_type, diagnosis, correction)` stores a
  `failure` memory.
- `save_lesson(task, lesson, category)` stores a lesson.
- `save_feedback(original_request, feedback, action_taken)` stores a
  `feedback` memory.
- `recall_relevant(query)`, `recall_failures(task)`, and
  `recall_lessons(topic)` retrieve related memories.

The package `ai.memory` re-exports the client, helper class, singleton accessors,
and module-level `remember` / `recall` helpers.

## Rhino Tool Failure Recording

`POST /rhino/tools/call` records exceptions raised while executing the MCP tool
through `get_project_memory().save_failure()`. The recorded task identifies the
tool name; the record contains the exception text and uses failure type
`rhino_tool`. Tool arguments are intentionally not stored, since they may
contain project-sensitive input.

Persistence runs in a worker thread because the AgentMemory wrapper is
synchronous. Recording is best effort: an unavailable memory service is logged
and does not replace the original MCP error response or unexpected exception.
MCP errors retain the route's structured error response; unexpected exceptions
are re-raised after the recording attempt. Successful tool calls are not stored
as failures. Feedback capture is available through `ProjectMemory` but does not
yet have a dedicated HTTP route.

## Local Verification

The memory client and helpers are covered by mocked-HTTP unit tests, so those
tests do not require the service to be running. Run them from
`AI-RHINO-ARCHITECT` with:

```powershell
..\.venv\Scripts\python.exe -m pytest tests/unit/test_agentmemory_client.py tests/unit/test_api_main.py -q
```

The proxy failure-recording test also runs without Rhino or AgentMemory; it
replaces those dependencies with test doubles.