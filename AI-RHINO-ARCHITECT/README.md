# AI RHINO ARCHITECT

AI-powered architectural design agent for Rhino 8 and Grasshopper.

## Vision

Build an AI agent capable of understanding architectural intent and transforming it into accurate, editable, parametric Rhino/Grasshopper models. The system learns from:
- Architectural knowledge and spatial planning
- CAD operations and Grasshopper workflows
- Construction knowledge and regulations
- Images, videos, and design precedents
- User feedback and modeling failures
- New architectural trends

## Architecture

```
USER → CHAT/UI → AI ORCHESTRATOR → MODELING SKILLS → TOOL EXECUTOR → RHINO/GRASSHOPPER → VALIDATION → FEEDBACK → EXPERIENCE DB
```

## Project Structure

```
AI-RHINO-ARCHITECT/
├── apps/           # Applications (agent, API, UI)
├── rhino/          # Rhino plugin, adapters, tools, validation
├── grasshopper/    # Grasshopper components, generators, tools
├── ai/             # Orchestrator, planners, providers, memory, evaluation
├── knowledge/      # Documents, rules, skills, concepts, precedents, failures
├── data/           # Raw, processed, metadata, datasets
├── database/       # Migrations, schemas, seeds
├── tests/          # Unit, integration, Rhino, evaluation tests
├── scripts/        # Ingestion, processing, evaluation scripts
├── docs/           # Documentation
└── config/         # Configuration files
```

## Development Phases

| Phase | Focus | Status |
|-------|-------|--------|
| Phase 0 | Research (Rhino API, Grasshopper API, MCP, AI models) | 🔄 In Progress |
| Phase 1 | Rhino Connection (AI ↔ Rhino bridge) | ⏳ Pending |
| Phase 2 | Basic Modeling Skills (Point, Line, Rectangle, Wall, Floor) | ⏳ Pending |
| Phase 3 | Agent Planner (Prompt → Plan → Tools → Rhino) | ⏳ Pending |
| Phase 4 | Validation (Geometry, dimensions, recovery) | ⏳ Pending |
| Phase 5 | Memory (Project, Skill, Failure, Feedback) | ⏳ Pending |
| Phase 6 | Architecture Knowledge (Spatial, components, regulations) | ⏳ Pending |
| Phase 7 | Grasshopper (Parametric generation) | ⏳ Pending |
| Phase 8 | Vision (Image → Understanding → Geometry) | ⏳ Pending |
| Phase 9 | Video Learning (Process understanding) | ⏳ Pending |
| Phase 10 | Continuous Learning (Trends, feedback, failures) | ⏳ Pending |

## Getting Started

1. Copy `.env.example` to `.env` and configure API keys
2. Install dependencies: `pip install -r requirements.txt`
3. Start the API: `uvicorn apps.api.main:app --reload --port 8000`
4. Open `http://localhost:8000/docs` for the interactive API documentation

The API starts without a Rhino connection. Use `RHINO_MCP_USE_STDIO=true` or
the TCP settings in `.env` when a Rhino MCP server is available.

## Database

The initial PostgreSQL schema is in `database/migrations/001_initial_schema.sql`.
Apply it with your normal migration runner after enabling the `vector` extension.

## Configuration

- `config/models.yaml` - LLM provider and model configuration
- `.env` - API keys and environment variables

## Documentation

- [Architecture](docs/architecture.md)
- [Roadmap](docs/roadmap.md)
- [Rhino Integration](docs/rhino_integration.md)
- [Grasshopper Integration](docs/grasshopper_integration.md)
- [Testing](docs/testing.md)

## License

Proprietary - All rights reserved.