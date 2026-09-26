# Quick Reference — AI RHINO ARCHITECT

**For AI Agents Starting New Sessions**

## 🚀 Getting Started (First 3 Steps)

1. **Read:** `logs/PROJECT_STATE.md` — Know current status
2. **Read:** Latest session in `logs/SESSION_INDEX.md` — Understand last work
3. **Check:** `logs/ISSUES.md` — Know active blockers

## 📁 Key Files to Know

| File | Purpose |
|------|---------|
| `logs/PROJECT_STATE.md` | Current project snapshot (phases, tests, files) |
| `logs/SESSION_INDEX.md` | All sessions indexed (newest first) |
| `logs/CHANGELOG.md` | Every file change recorded |
| `logs/DECISIONS.md` | Architectural decisions with rationale |
| `logs/ISSUES.md` | Open bugs and blockers |
| `Roadmap.txt` | Complete vision (2229 lines, 56 sections) |
| `STATUS_REPORT.txt` | Latest comprehensive implementation report |
| `AGENTS.md` | Agent execution rules for this workspace |

## 🧪 Running Tests

```bash
cd AI-RHINO-ARCHITECT
..\.venv\Scripts\python.exe -m pytest --cov=. --cov-report=term-missing
```

**Expected:** 93 passed, 10 skipped (103 total), 83% coverage

## 🔧 Starting Services

### FastAPI Server
```bash
cd AI-RHINO-ARCHITECT
..\.venv\Scripts\python.exe -m uvicorn apps.api.main:app --reload --port 8000
```

### AgentMemory Service
```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\start-agentmemory.ps1
```

### Rhino MCP Server
- Launch Rhino 8 Desktop
- MCP server should be available at `http://localhost:8765`

## 📊 Current Phase Status

| Phase | Status | Next Action |
|-------|--------|-------------|
| 0 — Research | ✅ DONE | — |
| 1 — Rhino Connection | ✅ DONE | — |
| 2 — Basic Modeling Skills | ✅ DONE | — |
| 3 — Agent Planner | ✅ DONE | — |
| 4 — Validation | ✅ DONE | — |
| 5 — Memory | 🔄 IN PROGRESS | Expand beyond AgentMemory client |
| 6 — Architecture Knowledge | ⏳ NEXT | Start spatial reasoning design |
| 7 — Grasshopper | ⏳ PENDING | Tool definitions exist, need execution |
| 8 — Vision | ⏳ PENDING | Image understanding pipeline |
| 9 — Video Learning | ⏳ PENDING | Tutorial extraction system |
| 10 — Continuous Learning | ⏳ PENDING | Trend monitoring & feedback loop |

## 🎯 Current Architecture (Simplified)

```
USER INTENT
    ↓
PLANNER (LLM)
    ↓
VALIDATION
    ↓
SKILL EXECUTOR
    ↓
MCP CLIENT
    ↓
RHINO 8
    ↓
OBSERVATION
    ↓
MEMORY
```

## 🔐 Architectural Principles (Non-Negotiable)

1. **Reasoning ≠ Execution** — AI reasons freely but executes only through controlled tools
2. **Model Units are Authoritative** — `RhinoDoc.ActiveDoc.ModelUnitSystem` is ground truth
3. **Model-Agnostic** — LLM provider is configurable, not hardcoded
4. **Skills Over Scripts** — Use modeling skills, not arbitrary code generation
5. **Multi-Store Knowledge** — PostgreSQL + pgvector + Graph + Object Storage

## 📝 Logging Contract (When You Make Changes)

1. **During session:** Record in your session file (`logs/sessions/YYYY-MM-DD_NNN.md`)
2. **File changes:** Update `logs/CHANGELOG.md`
3. **Decisions:** Add to `logs/DECISIONS.md` with ADR format
4. **Issues:** Update `logs/ISSUES.md` (open/resolve)
5. **End of session:** 
   - Update `logs/PROJECT_STATE.md`
   - Append to `logs/SESSION_INDEX.md`

## 🐛 Known Issues (Quick List)

- `ISSUE-001` — Live Rhino MCP validation pending
- `ISSUE-002` — AgentMemory service dependency
- `ISSUE-003` — No initial git commit yet

## 📞 Important URLs

- FastAPI Docs: http://localhost:8000/docs
- AgentMemory: http://localhost:3111/agentmemory
- Rhino MCP: http://localhost:8765
- Rhino API: https://developer.rhino3d.com/api/rhinocommon/
- Rhino Guides: https://developer.rhino3d.com/guides/

## 🎓 Historical Context

The project evolved through multiple versions:
- V0.8 → Controlled Rhino execution foundation
- V0.9.0 → Architectural intelligence layer
- V0.9.1 → Integrated capability platform
- V0.9.2 → Self-improving agent with 13 lifecycle methods
- V0.9.3 → Live Rhino 8 transition
- V0.9.3.1 → Unit system fix
- V0.9.4-0.9.8 → Vision, transactions, reasoning, evidence
- V0.9.16 → Conversational Copilot
- V0.1.0 → Current Python implementation (Phases 0-4)

Read `R0_report 01-04.txt` for detailed version history.
