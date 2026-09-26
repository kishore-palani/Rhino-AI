# AI RHINO ARCHITECT - Development Roadmap

## Overview
This roadmap outlines the 11-phase development plan for building an AI-powered architectural design agent integrated with Rhino 8 and Grasshopper.

---

## Phase 0: Research
**Status:** Complete
**Duration:** 2-3 weeks
**Focus:** Rhino API, Grasshopper API, MCP, AI models, datasets

### Objectives
- [x] Research RhinoCommon API capabilities
- [x] Research Grasshopper API and SDK
- [x] Evaluate MCP (Model Context Protocol) for Rhino integration
- [x] Benchmark AI models for architectural reasoning
- [x] Identify training datasets for video learning
- [x] Create technical specification V0.1

### Deliverables
- [x] Project structure scaffolded
- [x] Configuration system (models.yaml, .env)
- [x] MCP client foundation (config, models, exceptions)
- [x] Retry logic for LLM providers
- [x] Rhino API compatibility verification
- [x] Grasshopper API documentation review
- [x] MCP server (rhinomcp) evaluation
- [x] AI model benchmarking report
- [x] Technical specification V0.1

---

## Phase 1: Rhino Connection
**Status:** Complete
**Duration:** 3-4 weeks
**Focus:** AI <-> Rhino bridge

### Objectives
- [x] Implement MCP client for rhinomcp server
- [x] Create tool executor for Rhino commands
- [x] Build document state reader (units, objects, layers)
- [x] Implement basic geometry creation tools
- [x] Add connection health monitoring

### Deliverables
- [x] Working MCP client with auto-reconnect
- [x] Tool definitions for core Rhino operations
- [x] Document summary retrieval
- [x] Unit tests for Rhino connection
- [x] Integration test with live Rhino instance

---

## Phase 2: Basic Modeling Skills
**Status:** Complete
**Duration:** 4-5 weeks
**Focus:** Point, Line, Rectangle, Wall, Floor, Curve, Surface

### Objectives
- [x] Define modeling skill schema
- [x] Implement primitive geometry skills (Point, Line, Curve)
- [x] Implement architectural primitives (Wall, Floor, Column)
- [x] Add door/window opening skills
- [x] Create skill validation pipeline

### Deliverables
- [x] 12 modeling skills implemented (point, line, curve, rectangle, wall, floor, column, beam, roof, door, window, surface)
- [x] Skill registry and discovery
- [x] Parameter validation for each skill
- [x] Visual regression tests

### Phase 2 completion gates before Phase 3
- [x] Declarative skill schema and registry load all 12 checked-in skill definitions
- [x] Runtime validation reports missing, unknown, malformed, and out-of-range inputs
- [x] Registry can check declared Rhino tool requirements against an adapter tool catalog
- [x] Map each declared operation to an executable Rhino adapter tool
- [x] Add transaction/rollback handling around document mutations
- [x] Add deterministic adapter tests for point, line, curve, wall, and floor execution
- [x] Add a live Rhino smoke test and visual regression fixtures

---

## Phase 3: Agent Planner
**Status:** Complete
**Duration:** 4-5 weeks
**Focus:** Prompt -> Plan -> Tools -> Rhino

### Objectives
- [x] Build LLM-based planner with function calling
- [x] Implement planning prompt templates
- [x] Add plan validation before execution
- [x] Create execution engine with rollback
- [x] Add multi-step plan support

### Deliverables
- [x] Planner that converts NL to tool sequences
- [x] Plan validation and dry-run capability
- [x] Execution with error recovery
- [x] Planning evaluation benchmarks

---

## Phase 4: Validation
**Status:** Complete
**Duration:** 3-4 weeks
**Focus:** Geometry validation, dimensions, recovery

### Objectives
- [x] Geometric validity checks (closed, manifold, etc.)
- [x] Dimensional constraint validation
- [x] Building code compliance checking
- [x] Automatic correction strategies
- [x] Feedback loop to planner

### Deliverables
- [x] Validation pipeline with rules engine
- [x] Dimension/regulation rule definitions
- [x] Auto-correction for common issues
- [x] Validation reporting UI

---

## Phase 5: Memory
**Status:** In Progress
**Duration:** 3-4 weeks
**Focus:** Project, Skill, Failure, Feedback memory

### Objectives
- [ ] Project memory (context, decisions, history)
- [ ] Skill memory (learned parameters, patterns)
- [ ] Failure memory (errors, corrections, causes)
- [ ] Feedback memory (user preferences, ratings)
- [ ] Retrieval-augmented generation integration

### Deliverables
- [ ] Memory stores with vector search
- [ ] Memory-aware planner
- [ ] Failure analysis and prevention
- [ ] User preference learning

---

## Phase 6: Architecture Knowledge
**Status:** Pending
**Duration:** 4-5 weeks
**Focus:** Spatial reasoning, components, regulations

### Objectives
- [ ] Spatial reasoning module
- [ ] Building component taxonomy
- [ ] Regulation knowledge base (IBC, local codes)
- [ ] Program/space adjacency rules
- [ ] Precedent database integration

### Deliverables
- [ ] Knowledge graph with Neo4j
- [ ] Spatial reasoning engine
- [ ] Regulation lookup by jurisdiction
- [ ] Precedent search and retrieval

---

## Phase 7: Grasshopper
**Status:** Pending
**Duration:** 4-5 weeks
**Focus:** Parametric generation

### Objectives
- [ ] Grasshopper component library
- [ ] Definition generation from parameters
- [ ] Data tree manipulation
- [ ] Slider/parameter binding
- [ ] Baker integration for Rhino output

### Deliverables
- [ ] 20+ parametric components
- [ ] Definition generator from NL
- [ ] Parameter exploration UI
- [ ] Integration with Rhino geometry

---

## Phase 8: Vision
**Status:** Pending
**Duration:** 3-4 weeks
**Focus:** Image -> Understanding -> Geometry

### Objectives
- [ ] Viewport capture and analysis
- [ ] Site plan/image understanding
- [ ] Massing generation from images
- [ ] Style transfer and precedent matching
- [ ] Sketch-to-geometry pipeline

### Deliverables
- [ ] Image analysis pipeline
- [ ] Massing generation from site photos
- [ ] Precedent matching system
- [ ] Sketch interpretation

---

## Phase 9: Video Learning
**Status:** Pending
**Duration:** 5-6 weeks
**Focus:** Video -> Process Understanding -> CAD Skills

### Objectives
- [ ] Video segmentation and transcription
- [ ] Action recognition (CAD operations)
- [ ] Design reasoning extraction
- [ ] Before/after geometry pairing
- [ ] Training data pipeline

### Deliverables
- [ ] Video processing pipeline
- [ ] CAD operation classifier
- [ ] Process-to-skill extractor
- [ ] Training dataset generator

---

## Phase 10: Continuous Learning
**Status:** Pending
**Duration:** 4-5 weeks
**Focus:** Trends, feedback, failures

### Objectives
- [ ] Trend detection from design data
- [ ] Online learning from feedback
- [ ] Failure pattern mining
- [ ] Model fine-tuning pipeline
- [ ] A/B testing framework

### Deliverables
- [ ] Continuous learning pipeline
- [ ] Trend dashboard
- [ ] Automated model updates
- [ ] Evaluation framework

---

## Version Milestones

| Version | Target | Key Features |
|---------|--------|--------------|
| V0.1 | Week 2 | Tech spec, research complete |
| V0.5 | Week 6 | Rhino connection, basic skills |
| V0.9 | Week 14 | Planner, validation, memory |
| V0.9.16 | Week 20 | Conversational copilot, MCP |
| V0.9.17 | Week 22 | Multimodal context |
| V1.0 | Week 26 | Production release |

---

## Success Criteria

### Phase 0 Complete When:
- [x] Rhino API fully documented for our use cases
- [x] MCP server (rhinomcp) tested and working
- [x] AI model benchmarks completed
- [x] Technical specification V0.1 approved

### Phase 1 Complete When:
- [x] AI can connect to Rhino and read document state
- [x] AI can create basic geometry (point, line, rectangle)
- [x] Connection is stable with auto-reconnect

### Phase 2 Complete When:
- [ ] AI can create walls, floors, columns, doors, windows
- [ ] Skills are parameterized and validated
- [ ] Skills compose into simple buildings

### Phase 3 Complete When:
- [ ] Natural language -> building plan -> Rhino geometry
- [ ] Multi-step plans execute reliably
- [ ] Errors trigger replanning

### V1.0 Complete When:
- [ ] Full NL -> architectural design -> validated Rhino/GH model
- [ ] Learns from video tutorials
- [ ] Validates against regulations
- [ ] Continuous improvement from feedback
