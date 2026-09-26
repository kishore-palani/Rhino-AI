# Testing

## Test Layout

- `tests/unit/` contains deterministic unit tests for isolated behavior.
- `tests/integration/` contains cross-module and service integration tests.
- `tests/rhino/` contains tests that require Rhino or Rhino-compatible geometry support.
- `tests/evaluation/` contains evaluation and benchmark tests.

## Install Dependencies

Run commands from the `AI-RHINO-ARCHITECT` directory:

```powershell
python -m pip install -r requirements.txt
```

## Run Tests

Run the full test suite with coverage:

```powershell
pytest --cov=. --cov-report=term-missing
```

Run one test module while iterating:

```powershell
pytest tests/unit/test_provider_retry.py -q
```

Run a specific test:

```powershell
pytest tests/unit/test_provider_retry.py::test_retries_503_and_returns_result -q
```

## Quality Checks

The CI workflow runs Ruff and mypy against the current API, adapter, and Grasshopper tool modules:

```powershell
ruff check apps/api/main.py apps/api/mcp/client.py rhino/adapters/base.py rhino/adapters/mcp.py grasshopper/tools/definitions.py
mypy --explicit-package-bases apps/api/main.py apps/api/mcp/client.py rhino/adapters/base.py rhino/adapters/mcp.py grasshopper/tools/definitions.py
```

## Rhino and Grasshopper Tests

Tests that need a live Rhino or Grasshopper session are environment-dependent and should not be required for the deterministic CI suite. For CI-compatible coverage:

- Use `rhino3dm` for geometry operations that do not require Rhino.
- Mock MCP server responses and adapter connections.
- Validate geometry properties mathematically, including validity, closure, dimensions, and volume.
- Keep live Rhino tests isolated under `tests/rhino/`.

Grasshopper tests should create definitions through the adapter, assert successful execution, and validate the resulting baked geometry where the test environment supports it.

## Writing Tests

Prefer small, deterministic tests with explicit assertions. Async code should follow the existing repository pattern by using `pytest-asyncio` or `asyncio.run` in the test body. Avoid network calls, live Rhino dependencies, and shared mutable state in unit tests.
