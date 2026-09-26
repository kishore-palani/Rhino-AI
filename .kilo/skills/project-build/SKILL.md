---
name: project-build
description: Use when setting up, building, validating, or running AI RHINO ARCHITECT, including selecting the correct Python environment, installing dependencies, starting the API, and choosing focused or CI tests.
---

# Project Build and Validation

## Project locations

- Workspace root contains the shared `.venv` and Kilo configuration.
- Python application root is `AI-RHINO-ARCHITECT/`.
- From the application root, use `..\.venv\Scripts\python.exe` on Windows.
- Follow `AGENTS.md`, `AI-RHINO-ARCHITECT/README.md`, and
  `AI-RHINO-ARCHITECT/.github/workflows/ci.yml` as the source of truth.

## Workflow

1. Inspect the existing environment and CI command before installing packages.
2. Run a targeted pytest selection for the changed behavior first.
3. Run the canonical CI suite only when the scope warrants it:
   `pytest --cov=. --cov-report=term-missing` from `AI-RHINO-ARCHITECT/`.
4. Start the local API with
   `uvicorn apps.api.main:app --reload --port 8000` from the application root.
5. Treat Rhino and network integration tests as environment-dependent; report
   skips or unavailable services separately from unit-test results.

Do not create a second virtual environment, copy real secrets into `.env`,
install optional tools without checking whether they are needed, or claim a
server/API is verified unless it was actually started and checked.