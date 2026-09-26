# AI RHINO ARCHITECT - Architecture Documentation

## System Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                        USER INTERFACE                           │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐              │
│  │   Chat UI   │  │  Rhino UI   │  │  VS Code    │              │
│  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘              │
└─────────┼────────────────┼────────────────┼─────────────────────┘
          │                │                │
          ▼                ▼                ▼
┌─────────────────────────────────────────────────────────────────┐
│                      AI ORCHESTRATOR                            │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐              │
│  │   Planner   │  │   Memory    │  │  Knowledge  │              │
│  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘              │
└─────────┼────────────────┼────────────────┼─────────────────────┘
          │                │                │
          ▼                ▼                ▼
┌─────────────────────────────────────────────────────────────────┐
│                    MODELING SKILLS                              │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐              │
│  │  Geometry   │  │ Architecture│  │ Parametric  │              │
│  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘              │
└─────────┼────────────────┼────────────────┼─────────────────────┘
          │                │                │
          ▼                ▼                ▼
┌─────────────────────────────────────────────────────────────────┐
│                    TOOL EXECUTOR                                │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐              │
│  │ Validation  │  │ Permission  │  │  Execution  │              │
│  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘              │
└─────────┼────────────────┼────────────────┼─────────────────────┘
          │                │                │
          ▼                ▼                ▼
┌─────────────────────────────────────────────────────────────────┐
│                  RHINO / GRASSHOPPER                            │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐              │
│  │  Rhino MCP  │  │ RhinoCommon │  │ Grasshopper │              │
│  └─────────────┘  └─────────────┘  └─────────────┘              │
└─────────────────────────────────────────────────────────────────┘
```

## Core Components

### 1. AI Orchestrator (`ai/orchestrator/`)
Central brain that coordinates all AI activities:
- Intent understanding and normalization
- Task planning and decomposition
- Tool selection and parameter validation
- Execution monitoring and error handling
- Result validation and feedback integration

### 2. Modeling Skills (`knowledge/skills/`)
Reusable, parameterized CAD operations:
- **Geometry Skills**: Point, Line, Curve, Surface, Extrusion, Brep
- **Architecture Skills**: Wall, Floor, Door, Window, Column, Beam, Stair, Roof
- **Parametric Skills**: Facade, Panel, Attractor, Pattern, Grid
- **Site Skills**: Site, Terrain, Setback, Orientation

Each skill defines:
```json
{
  "skill_id": "create_wall",
  "name": "Create Wall",
  "description": "Create a wall from a baseline curve",
  "inputs": ["curve", "height", "thickness"],
  "outputs": ["wall_brep", "wall_guid"],
  "parameters": {"height": "number", "thickness": "number"},
  "preconditions": ["valid_curve", "positive_height", "positive_thickness"],
  "operations": ["extrude_curve", "cap_brep"],
  "validation": ["valid_brep", "closed_solid", "correct_dimensions"],
  "failure_modes": ["invalid_curve", "extrusion_failed", "boolean_failed"]
}
```

### 3. Rhino Integration (`rhino/`)
- **Adapters**: Abstract Rhino operations (create, read, update, delete)
- **Tools**: MCP tool definitions for LLM consumption
- **Validation**: Geometry validation (Brep validity, dimensions, intersections)
- **Plugin**: C# Rhino 8 plugin with MCP server

### 4. Grasshopper Integration (`grasshopper/`)
- **Components**: Custom Grasshopper components for AI operations
- **Generators**: GH definition generation from parametric specs
- **Tools**: Parameter modification, baking, data tree manipulation

### 5. Memory System (`ai/memory/`)
- **Short-term Context**: Current conversation, selection, viewport
- **Long-term Knowledge**: Learned skills, patterns, precedents
- **Project Memory**: Current project state, design intent, constraints
- **Skill Memory**: Skill performance, success/failure rates
- **Failure Memory**: Structured failure records with diagnoses
- **Feedback Memory**: User feedback categorized and structured

### 6. Knowledge Base (`knowledge/`)
- **Documents**: Architectural research, regulations, standards
- **Rules**: Dimensional rules with context (jurisdiction, building type)
- **Skills**: Modeling skill definitions and examples
- **Concepts**: Architectural concepts (spatial relationships, circulation)
- **Precedents**: Reference projects with extracted design patterns
- **Failures**: Failure cases with corrections

### 7. Database Layer (`database/`)
- **PostgreSQL + pgvector**: Structured data + semantic search
- **Neo4j**: Knowledge graph for relationships
- **Object Storage**: Videos, images, .3dm, .gh files

## Data Flow

### Request Processing Pipeline
```
1. USER REQUEST
   ↓
2. INTENT CLASSIFICATION (LLM)
   ↓
3. CONTEXT RETRIEVAL (Memory + Knowledge Graph + RAG)
   ↓
4. PLAN GENERATION (Planner LLM)
   ↓
5. SKILL SELECTION (Skill matching)
   ↓
6. PARAMETER VALIDATION (Schema validation)
   ↓
7. PERMISSION CHECK (Scope, protection)
   ↓
8. RHINO EXECUTION (MCP → RhinoCommon)
   ↓
9. GEOMETRY VALIDATION (Brep check, dimensions, constraints)
   ↓
10. OBSERVATION (Viewport capture, state diff)
   ↓
11. EVALUATION (Architectural critic)
   ↓
12. RESULT / CORRECTION LOOP
   ↓
13. EXPERIENCE STORAGE (Memory + Knowledge Graph)
```

### Video Learning Pipeline (Phase 9)
```
VIDEO INPUT
   ↓
SEGMENTATION (scene changes, speaker changes)
   ↓
TRANSCRIPTION (speech-to-text with timestamps)
   ↓
OCR / SCREEN UNDERSTANDING (UI detection, command recognition)
   ↓
ACTION RECOGNITION (Rhino commands, Grasshopper operations)
   ↓
CAD OPERATION DETECTION (parameter changes, geometry modifications)
   ↓
DESIGN REASONING EXTRACTION (intent, strategy, evaluation)
   ↓
BEFORE/AFTER GEOMETRY (state snapshots)
   ↓
STRUCTURED TRAINING DATA (skill examples, parametric patterns)
```

## Key Design Principles

1. **Reasoning ≠ Execution**: AI reasons freely but executes only through controlled tools
2. **Modeling Skills over Code Generation**: Reusable skills instead of arbitrary code
3. **Validation First**: Every geometric operation validated before commit
4. **Explicit Scope**: Every operation has explicit editable/protected scope
5. **Evidence-Based**: All architectural claims backed by geometric evidence
6. **Failure as Data**: Every failure structured for learning
7. **Model Agnostic**: Provider abstraction for LLM flexibility
8. **Contextual Regulations**: Rules tied to jurisdiction, building type, occupancy

## Technology Stack

| Layer | Technology |
|-------|------------|
| AI Backend | Python 3.11+, FastAPI, LangChain |
| LLM Providers | OpenAI, Anthropic, Google, Local (Ollama) |
| Rhino Plugin | C# .NET 8, RhinoCommon, Rhino 8 SDK |
| Grasshopper | C# Grasshopper SDK, Python (GhPython) |
| Database | PostgreSQL 16 + pgvector |
| Knowledge Graph | Neo4j 5.x |
| Vector Search | pgvector (PostgreSQL extension) |
| Object Storage | Local (dev) / S3-compatible (prod) |
| MCP | JSON-RPC 2.0 over WebSocket/HTTP |
| Testing | pytest, Rhino live benchmarks |
| CI/CD | GitHub Actions |

## Security Model

```
LLM → Tool Registry → Validation → Permission Check → Execution
         │              │              │
         ▼              ▼              ▼
    Allowed Tools  Schema Check   Scope Check
    Parameter Types  Required/      Protected
    Risk Levels      Optional       Geometry
```

- LLM never has direct system access
- All tools pre-defined with schemas
- Destructive operations require explicit approval
- API keys in environment variables only
- Database credentials encrypted

## Deployment Architecture

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   Client    │────▶│   API GW    │────▶│  AI Service │
│  (UI/Chat)  │     │  (Auth,     │     │  (FastAPI)  │
└─────────────┘     │  Rate Limit)│     └──────┬──────┘
                    └─────────────┘            │
                                               ▼
                    ┌─────────────┐     ┌─────────────┐
                    │  PostgreSQL │◀───▶│   Neo4j     │
                    │  + pgvector │     │  Knowledge  │
                    └─────────────┘     │   Graph     │
                                         └─────────────┘
                    ┌─────────────┐
                    │  Rhino MCP  │
                    │   Server    │
                    └──────┬──────┘
                           │
                    ┌──────▼──────┐
                    │  Rhino 8    │
                    │  Desktop    │
                    └─────────────┘
```