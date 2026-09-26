# AI RHINO ARCHITECT — Decisions Registry

All architectural, technical, and design decisions are recorded here with context,
options considered, and reasoning.

---

## ADR-001: Separation of Reasoning from Execution
- **Date:** Historical (Phases 0–1)
- **Status:** ACCEPTED / IN EFFECT
- **Context:** The AI should not directly manipulate Rhino geometry or generate raw scripts blindly.
- **Decision:** All geometry changes must go through structured Modeling Skills and the MCP tool layer. The LLM generates a structured plan, which is validated before execution.
- **Consequences:** Prevents invalid geometry and security issues, enables transaction rollback.

## ADR-002: Model-Agnostic LLM Provider Interface
- **Date:** Historical (Phase 0)
- **Status:** ACCEPTED / IN EFFECT
- **Context:** The project should not be locked to any single LLM vendor.
- **Decision:** Implement `ModelProvider` abstraction in `ai/providers/` and configure providers in `config/models.yaml`.
- **Consequences:** Easy to swap between Anthropic, OpenAI, local models without rewriting application logic.

## ADR-003: Authoritative Rhino Model Units
- **Date:** Historical (V0.9.3.1)
- **Status:** ACCEPTED / IN EFFECT
- **Context:** User requests in meters were causing dimension errors when the Rhino document was set to millimeters.
- **Decision:** `RhinoDoc.ActiveDoc.ModelUnitSystem` is the single source of truth. All user dimensions are converted to the document's model units before execution.
- **Consequences:** Eliminates dimensional mismatches across different unit setups.

## ADR-004: Multi-Store Knowledge Architecture
- **Date:** Historical (Roadmap)
- **Status:** ACCEPTED / IN EFFECT
- **Context:** Vector search alone is insufficient for architectural relationships and rules.
- **Decision:** Four-tier storage:
  1. PostgreSQL for relational metadata, skills, rules
  2. pgvector for semantic retrieval of documents
  3. Knowledge Graph for spatial/functional relationships
  4. Object Storage for 3DM, GH, image, video assets
- **Consequences:** Rich, multi-modal knowledge retrieval suited to architectural design.

## ADR-005: Project-Level Logging System
- **Date:** 2026-09-26
- **Status:** ACCEPTED / IN EFFECT
- **Context:** Need a persistent, structured logging folder where every session and change is recorded for human review and AI context preservation.
- **Decision:** Create `logs/` folder with `PROJECT_STATE.md`, `SESSION_INDEX.md`, `CHANGELOG.md`, `DECISIONS.md`, `ISSUES.md`, and individual session logs in `logs/sessions/`.
- **Consequences:** Full continuity across sessions and agents; zero context loss.
