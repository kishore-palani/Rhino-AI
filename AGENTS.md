# Agent Execution Rules

- This workspace runs on Windows PowerShell.
- Do not call a generic `write` tool; it is not available in this workspace. Use the repository edit tools for file changes and use the Rhino MCP tools only for Rhino operations.
- For text-file edits, use `apply_patch` with both `input` and `explanation` arguments. Do not substitute a `write` call or retry a malformed tool payload.
- Bash is enabled for this workspace. Use `bash` for shell commands when the agent exposes it; use PowerShell when Bash is unavailable. Never invent an unavailable tool call.
- Terminal command arguments must be a single plain command string, not an object or array.
- Prefer repository tools for file reads, searches, and edits.
- Before retrying a failed tool call, correct the argument shape instead of repeating the same payload.

## Testing conventions

- The active Python project for this workspace is [AI-RHINO-ARCHITECT/README.md](AI-RHINO-ARCHITECT/README.md).
- Use pytest as the project test runner; the canonical CI command is defined in [AI-RHINO-ARCHITECT/.github/workflows/ci.yml](AI-RHINO-ARCHITECT/.github/workflows/ci.yml): `pytest --cov=. --cov-report=term-missing`.
- Run tests from the project directory: `Set-Location AI-RHINO-ARCHITECT` before invoking pytest. Use the workspace interpreter at `..\.venv\Scripts\python.exe`.
- Prefer targeted validation first for a single file or test selection, for example: `pytest tests/unit/test_provider_retry.py -q`.
- Keep tests deterministic and isolated from Rhino or network dependencies unless they are explicitly integration tests.
- New or changed behavior should be backed by a narrow regression test in the nearest existing suite under [AI-RHINO-ARCHITECT/tests](AI-RHINO-ARCHITECT/tests).
- Async code should follow the repo's pytest pattern and use `pytest-asyncio` or `asyncio.run` within the test body when needed.
- Do not invent alternate test commands or frameworks when the repo already defines pytest-based workflows.

## Documentation links

- [AI-RHINO-ARCHITECT/README.md](AI-RHINO-ARCHITECT/README.md)
- [AI-RHINO-ARCHITECT/.github/workflows/ci.yml](AI-RHINO-ARCHITECT/.github/workflows/ci.yml)
- [AI-RHINO-ARCHITECT/tests/unit/test_provider_retry.py](AI-RHINO-ARCHITECT/tests/unit/test_provider_retry.py)

## Kilo Agents, Skills, and MCP

- Kilo project agents live in `.kilo/agents/`; delegate focused work with Kilo's
	`task` tool. Use the orchestrator for roadmap work, and the Python, test,
	security, Rhino, and documentation specialists for owned areas.
- Kilo project skills live in `.kilo/skills/`. These are agent guidance modules;
	they are distinct from executable modeling-skill contracts in
	`AI-RHINO-ARCHITECT/knowledge/skills/*.json`.
- Kilo connects to agentmemory at `http://localhost:3111` with the `core` tools.
	Start the local agentmemory service when it is not already running.
- Use `powershell -ExecutionPolicy Bypass -File .\scripts\start-agentmemory.ps1`
	to start it idempotently. The launcher repairs partial engine-only starts,
	prevents duplicate-engine conflicts, and writes logs under `logs/`.
- Kilo starts the Rhino MCP server over stdio with
	`.vscode/mcp.json`; its Kilo command uses the installed router path based on
	`{env:APPDATA}`. Open Rhino with the MCP plugin available before modeling.
	Rhino tools are namespaced under `rhino_*` and require approval.
- The application API's `RhinoMCPClient` is a separate runtime integration; do
	not confuse its TCP/stdio settings with Kilo's MCP server process.
- For RhinoCommon and Grasshopper API work, use current Rhino 8 references:
	`https://developer.rhino3d.com/api/rhinocommon/`,
	`https://developer.rhino3d.com/en/api/`,
	`https://developer.rhino3d.com/guides/`, and
	`https://developer.rhino3d.com/samples/`. Verify signatures against the
	version used by the project instead of trusting copied snippets.
- The external `E:\Github\agency-agents` catalog is reference material only;
	Kilo subagents must be defined in `.kilo/agents/` to be discoverable.

## Fast Routing Rules

- Start from the named file, symbol, failing test, or command output.
- State one falsifiable local hypothesis before editing.
- Run the cheapest focused check immediately after the first edit.
- Prefer a narrow regression test and the existing project interpreter before
	broad scans or speculative refactors.
- Do not enable unrelated MCP servers or copy the full external agent catalog
	into the repository; add integrations only when the project needs them.
