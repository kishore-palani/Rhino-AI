# AI RHINO ARCHITECT — Quick Start Guide

**Last Updated:** 2026-09-26  
**Version:** 0.1.0

---

## What Is This?

AI RHINO ARCHITECT is an AI-powered architectural design agent that integrates with Rhino 3D. It converts natural language instructions into validated Rhino geometry while understanding architectural principles, spatial relationships, and building regulations.

**This is NOT a simple text-to-3D generator.**  
It's an architectural reasoning system that uses Rhino as its computational design environment.

---

## Current Status

✅ **Phases 0-4 Complete** (Solid foundation)  
🔄 **Phase 5 In Progress** (Memory system 60% complete)  
📋 **Phase 6 Planned** (Architectural knowledge layer)

**Test Status:** 100 passing tests, 83% coverage  
**Lines of Code:** ~3,500 Python across 25 modules

---

## What Works Right Now

### 1. Rhino Integration via MCP
- Connect to Rhino 8 via JSON-RPC 2.0 over TCP/stdio/HTTP
- Execute Python scripts in Rhino
- Query document state, units, objects
- Create and manipulate geometry

### 2. Modeling Skills (12 Implemented)
Safe, reusable operations that prevent arbitrary code execution:
- **Basic:** point, line, curve, rectangle, surface
- **Architectural:** wall, floor, column, beam, roof, door, window

### 3. LLM-Based Planning
- Convert natural language → structured modeling plan
- Dependency analysis and ordered execution
- Transaction rollback via Rhino undo on failure

### 4. 3-Tier Validation
- **Geometry:** Closed solids, manifold topology, valid BReps
- **Dimensional:** Wall heights, thicknesses, clearances (9 rules)
- **Regulatory:** IBC 2021 compliance checks (12 categories)
- **Auto-correction:** 14 strategies for common violations

### 5. Memory Integration
- AgentMemory REST client for experience storage
- Project state, failures, lessons, feedback recording
- Query interface for retrieving relevant experiences

---

## Quick Test

### Run Test Suite
```bash
cd AI-RHINO-ARCHITECT
..\.venv\Scripts\python.exe -m pytest tests/ -q
```

**Expected:** 100 passed, 22 skipped

### Start FastAPI Server
```bash
cd AI-RHINO-ARCHITECT
..\.venv\Scripts\python.exe -m uvicorn apps.api.main:app --reload
```

Visit: http://localhost:8000 (health check)

### Test Rhino Connection (Requires Rhino 8 with MCP server)
```bash
cd AI-RHINO-ARCHITECT
..\.venv\Scripts\python.exe scripts/probe_mcp_http.py
```

---

## Architecture Overview

```
USER REQUEST (Natural Language)
        ↓
LLM PLANNER (ai/planner/)
        ↓
STRUCTURED PLAN (JSON)
        ↓
VALIDATION (ai/validation/)
        ↓
SKILL EXECUTOR (ai/skills/)
        ↓
RHINO MCP CLIENT (apps/api/mcp/)
        ↓
RHINO 8 (RhinoCommon)
        ↓
GEOMETRY VALIDATION
        ↓
MEMORY RECORDING (ai/memory/)
        ↓
RESULT + EXPERIENCE
```

---

## Key Design Decisions

1. **Separation of Reasoning from Execution** (ADR-001)  
   LLM generates plans, structured skills execute safely

2. **Model-Agnostic LLM Interface** (ADR-002)  
   Swap providers (Anthropic, OpenAI, local) without code changes

3. **Authoritative Rhino Units** (ADR-003)  
   `RhinoDoc.ActiveDoc.ModelUnitSystem` is single source of truth

4. **Multi-Store Knowledge Architecture** (ADR-004)  
   PostgreSQL + pgvector + Knowledge Graph + Object Storage (planned)

5. **Project-Level Logging** (ADR-005)  
   `logs/` folder preserves full session history for AI continuity

---

## Directory Structure

```
AI-RHINO-ARCHITECT/
├── apps/api/              # FastAPI server, MCP client
├── ai/
│   ├── providers/         # LLM abstraction
│   ├── skills/            # Modeling skill registry & executor
│   ├── planner/           # LLM-based planner & execution engine
│   ├── validation/        # 3-tier validation system
│   └── memory/            # AgentMemory integration
├── rhino/adapters/        # Rhino adapter abstraction
├── grasshopper/tools/     # Grasshopper tool definitions
├── knowledge/             # (Phase 6) Architectural knowledge base
├── tests/                 # Unit + integration tests
├── logs/                  # Session logs & project state
└── config/                # Configuration files
```

---

## Next Steps

### For Developers
1. **Complete Phase 5 Memory:**
   - Implement skill execution memory
   - Add failure pattern recognition
   - Build feedback analysis system
   
2. **Start Phase 6 Knowledge:**
   - Create spatial relationship model
   - Build component ontology
   - Add architectural reasoning rules

See [NEXT_PHASE_PLAN.md](NEXT_PHASE_PLAN.md) for detailed roadmap.

### For Stakeholders
The current system proves the core loop:
- Natural language → reasoning → Rhino execution → validation → memory

Next phases add:
- Experience-based learning (Phase 5)
- Architectural intelligence (Phase 6)
- Grasshopper integration (Phase 7)
- Vision capabilities (Phase 8)

---

## Configuration

### Environment Variables (.env)
```bash
# LLM Provider
ANTHROPIC_API_KEY=your_key
OPENAI_API_KEY=your_key

# Rhino MCP
RHINO_MCP_TRANSPORT=http  # or tcp, stdio
RHINO_MCP_HOST=localhost
RHINO_MCP_PORT=8765

# AgentMemory
AGENTMEMORY_URL=http://localhost:3111
```

### Model Configuration (config/models.yaml)
```yaml
provider:
  name: anthropic  # or openai

models:
  reasoning:
    name: claude-sonnet-5
  temperature: 0.2
```

---

## Testing Requirements

### Unit Tests (No External Dependencies)
```bash
pytest tests/unit/ -v
```

### Integration Tests (Requires Services)
```bash
# Requires Rhino 8 with MCP server on localhost:8765
pytest tests/integration/test_live_skills.py -v

# Requires AgentMemory service on localhost:3111
pytest tests/unit/test_agentmemory_client.py -v
```

---

## Common Issues

### Issue: Tests fail with "Could not find platform independent libraries"
**Solution:** This is a Python warning, not an error. Tests still run.

### Issue: Integration tests skip
**Solution:** Normal when Rhino MCP server is not running. Unit tests prove the logic.

### Issue: AgentMemory tests fail
**Solution:** Start the service with `scripts\start-agentmemory.ps1`

### Issue: MCP connection refused
**Solution:** Start Rhino 8 and enable MCP server plugin on port 8765

---

## Documentation

- **[Roadmap.txt](../Roadmap.txt)** — Complete project vision (2229 lines, 56 sections)
- **[PROJECT_STATE.md](PROJECT_STATE.md)** — Current implementation status
- **[DECISIONS.md](DECISIONS.md)** — Architectural Decision Records
- **[ISSUES.md](ISSUES.md)** — Known bugs and blockers
- **[NEXT_PHASE_PLAN.md](NEXT_PHASE_PLAN.md)** — Detailed implementation plan
- **[SESSION_INDEX.md](SESSION_INDEX.md)** — All development sessions

---

## Example Usage (Planned API)

```python
from ai.planner import KnowledgeEnhancedPlanner
from rhino.adapters.mcp import MCPRhinoAdapter

# Initialize
adapter = MCPRhinoAdapter()
planner = KnowledgeEnhancedPlanner(adapter=adapter)

# Natural language request
request = """
Create a 6m × 4m room with 200mm thick walls, 
3m height, one 900mm door on the south wall, 
and a 1500mm window on the east wall.
"""

# Generate and execute plan
plan = planner.plan_from_requirements(request)
result = planner.execute(plan)

# Validate
validation_result = validator.validate(result)

# Record experience
memory.record_execution(plan, result, validation_result)
```

---

## Long-Term Vision

**V1.0 Target Capabilities:**
- Natural language understanding
- Architectural spatial reasoning
- Rhino + Grasshopper parametric generation
- Vision (image → geometry)
- Video learning (process extraction from tutorials)
- Continuous learning (feedback incorporation)

**The Goal:**
> A multimodal AI architectural computational designer that understands intent, reasons spatially, learns from processes, generates accurate parametric geometry, validates constraints, and continuously expands design knowledge.

---

## Contributing

This is currently a research/development project. Future phases will define contribution guidelines.

---

## License

[To be determined]

---

## Contact

[To be determined]

---

**Project Status:** ✅ Operational foundation with 100 passing tests and clear roadmap for next 6 phases.
