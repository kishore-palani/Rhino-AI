# AI RHINO ARCHITECT — Next Phase Plan

**Plan Created:** 2026-09-26  
**Current Version:** 0.1.0  
**Current Phase:** Phase 5 (Memory) — 60% complete  
**Target:** Complete Phase 5 + Start Phase 6 Foundation

---

## Executive Summary

The project has completed Phases 0-4 with a solid foundation:
- ✅ Rhino MCP integration working
- ✅ 12 modeling skills implemented and tested
- ✅ LLM-based planner with dependency execution
- ✅ 3-tier validation system (geometry, dimensional, regulatory)
- ✅ AgentMemory REST client integrated
- ✅ 100 passing tests, 83% coverage

**Gap:** The system can execute and validate, but **cannot learn from experience effectively.**

**Next Priority:** Complete memory system to enable experience-based learning, then add architectural knowledge layer.

---

## Phase 5 Completion: Enhanced Memory System

### Current State (60% Complete)

**Implemented:**
- ✅ AgentMemoryClient (`ai/memory/agentmemory_client.py`) — REST wrapper for http://localhost:3111
- ✅ ProjectMemory (`ai/memory/project_memory.py`) — Domain helpers for state, failures, lessons, feedback
- ✅ Basic integration in FastAPI (`apps/api/main.py`) — Records tool failures

**Missing:**
- ❌ Skill execution memory (what worked/failed under what conditions)
- ❌ Failure pattern recognition (learning from repeated errors)
- ❌ Feedback analysis system (structured user correction storage)
- ❌ Unified query interface for planner/executor

### Objectives

Enable the system to:
1. **Remember skill execution context** — Parameters, preconditions, success/failure, timing
2. **Detect failure patterns** — "wall thickness <150mm always fails dimensional validation"
3. **Learn from feedback** — "user corrected wall height 3x → prefer 2.7m for residential"
4. **Query experience before planning** — "Has this approach failed before? What worked instead?"

### Deliverables

#### 1. Skill Memory Module (`ai/memory/skill_memory.py`)

**Purpose:** Track every skill execution with full context

**Schema:**
```python
@dataclass
class SkillExecution:
    skill_id: str                    # e.g., "create_wall"
    timestamp: datetime
    parameters: Dict[str, Any]       # Actual params passed
    preconditions: Dict[str, Any]    # Context when executed
    success: bool
    error: Optional[str]
    execution_time_ms: float
    geometry_ids: List[str]          # Created object IDs
    validation_results: List[str]    # Any validation issues
    plan_context: Optional[str]      # What plan step was this part of?
```

**API:**
```python
class SkillMemory:
    def record_execution(self, execution: SkillExecution) -> None
    def query_similar(self, skill_id: str, params: Dict) -> List[SkillExecution]
    def get_success_rate(self, skill_id: str, filters: Dict = None) -> float
    def get_parameter_ranges(self, skill_id: str, param_name: str) -> Dict
    # Returns: {"min": X, "max": Y, "successful_range": (A, B), "failure_range": [...]}
```

**Integration Points:**
- `ai/skills/executor.py` — Add recording after each execution
- `ai/planner/planner.py` — Query before suggesting risky operations

**Tests:**
- Record multiple executions with varying params
- Query similar executions by skill + params
- Calculate success rate by skill type
- Extract successful parameter ranges
- Test integration with skill executor

**Estimated:** ~200-250 lines, 5-7 tests

---

#### 2. Failure Pattern Recognition (`ai/memory/failure_patterns.py`)

**Purpose:** Aggregate failures and detect recurring patterns

**Pattern Types:**
```python
class FailurePattern:
    pattern_id: str
    failure_type: str        # "geometry", "dimensional", "regulatory", "mcp"
    occurrences: int
    first_seen: datetime
    last_seen: datetime
    common_context: Dict     # What's common across failures?
    suggested_fix: Optional[str]
    confidence: float
```

**API:**
```python
class FailurePatternRecognizer:
    def analyze_failures(self, lookback_days: int = 30) -> List[FailurePattern]
    def detect_pattern(self, new_failure: Dict) -> Optional[FailurePattern]
    def suggest_correction(self, task: str, context: Dict) -> Optional[str]
    def update_pattern(self, pattern_id: str, new_occurrence: Dict) -> None
```

**Pattern Detection Rules:**
- Dimensional: Same parameter out of range 3+ times
- Geometric: Same validation rule violated 3+ times
- MCP: Same tool/operation failing 2+ times
- Regulatory: Same code section violated 2+ times

**Integration Points:**
- `ai/validation/pipeline.py` — Feed validation failures
- `ai/planner/planner.py` — Query patterns before plan generation
- `apps/api/main.py` — Feed MCP errors

**Tests:**
- Detect dimensional pattern (wall too thin)
- Detect geometric pattern (non-manifold edges)
- Suggest correction based on pattern
- Update pattern with new occurrence
- Integration test with validation pipeline

**Estimated:** ~250-300 lines, 6-8 tests

---

#### 3. Feedback Analysis (`ai/memory/feedback_analysis.py`)

**Purpose:** Structure and learn from user corrections

**Schema:**
```python
class FeedbackRecord:
    feedback_id: str
    timestamp: datetime
    original_request: str
    original_plan: Dict
    executed_steps: List[str]
    user_feedback: str           # Natural language
    feedback_type: str           # "dimensional", "stylistic", "functional", "error"
    affected_elements: List[str] # Which geometry/components
    correction_action: str       # What was changed
    structured_intent: Dict      # Parsed intent from NL feedback
```

**API:**
```python
class FeedbackAnalyzer:
    def parse_feedback(self, feedback: str, context: Dict) -> FeedbackRecord
    def categorize_feedback(self, feedback: str) -> str
    def extract_dimensional_corrections(self, feedback: str) -> Dict
    def query_similar_corrections(self, task: str) -> List[FeedbackRecord]
    def get_preference_summary(self, category: str) -> Dict
```

**Feedback Categories:**
- **Dimensional:** "make it taller", "reduce thickness", "2.7m instead"
- **Stylistic:** "too aggressive", "more subtle", "lighter"
- **Functional:** "bedroom shouldn't open to entrance", "needs more privacy"
- **Error:** "wrong location", "incorrect orientation"

**Integration Points:**
- New endpoint: `POST /feedback` in `apps/api/main.py`
- `ai/planner/planner.py` — Query similar corrections during planning

**Tests:**
- Parse dimensional feedback ("make it 3m tall")
- Categorize feedback types
- Extract structured intent from natural language
- Query similar corrections
- Integration test: full feedback → correction → recall cycle

**Estimated:** ~200-250 lines, 6-8 tests

---

#### 4. Unified Query Interface (`ai/memory/query.py`)

**Purpose:** Single API for planner/executor to query all memory types

**API:**
```python
class MemoryQuery:
    def __init__(self):
        self.skill_memory = SkillMemory()
        self.pattern_recognizer = FailurePatternRecognizer()
        self.feedback_analyzer = FeedbackAnalyzer()
        self.agentmemory_client = AgentMemoryClient()
    
    def query_before_plan(self, task: str, context: Dict) -> MemoryInsights:
        """
        Returns all relevant memories for planning:
        - Similar past failures
        - Known patterns to avoid
        - User preferences from feedback
        - Successful parameter ranges
        """
        pass
    
    def query_before_skill_execution(self, skill_id: str, params: Dict) -> SkillInsights:
        """
        Returns execution-specific insights:
        - Success rate for these params
        - Known failure modes
        - Suggested parameter adjustments
        """
        pass
    
    def query_for_correction(self, error: str, context: Dict) -> CorrectionSuggestions:
        """
        Returns correction suggestions:
        - Similar past failures and their fixes
        - Pattern-based recommendations
        - Related feedback from users
        """
        pass
```

**MemoryInsights Schema:**
```python
@dataclass
class MemoryInsights:
    relevant_failures: List[Dict]
    known_patterns: List[FailurePattern]
    user_preferences: Dict
    successful_examples: List[SkillExecution]
    warnings: List[str]
    suggestions: List[str]
```

**Integration Points:**
- `ai/planner/planner.py` — Call `query_before_plan()` in planning phase
- `ai/skills/executor.py` — Call `query_before_skill_execution()` before each skill
- `ai/validation/pipeline.py` — Call `query_for_correction()` on validation failure

**Tests:**
- Query all memory types for a task
- Aggregate insights from multiple sources
- Rank suggestions by relevance
- Integration test: planner → query → adjusted plan

**Estimated:** ~150-200 lines, 4-5 tests

---

### Phase 5 Summary

**Total Estimated Effort:**
- **Lines of Code:** ~800-1000 new lines
- **Test Cases:** 21-28 new tests
- **Modules:** 4 new Python modules
- **Integration Points:** 5 existing modules updated
- **Development Time:** 5-7 hours (estimated)

**Success Criteria:**
- ✅ Every skill execution is recorded with context
- ✅ System detects recurring failure patterns automatically
- ✅ User feedback is parsed and stored structurally
- ✅ Planner queries memory before generating plans
- ✅ Executor queries memory before skill execution
- ✅ All new tests pass (target: 120+ total tests)

---

## Phase 6 Foundation: Architectural Knowledge

### Current Gap

The system can:
- Execute geometry operations (Phase 2)
- Plan step sequences (Phase 3)
- Validate dimensions and regulations (Phase 4)
- Remember experiences (Phase 5)

The system **cannot:**
- Reason about spatial relationships (bedroom adjacent to entrance = bad)
- Understand functional requirements (bedrooms need privacy)
- Suggest layouts based on architectural principles
- Know typical building component dimensions beyond validation minimums

**Phase 6 bridges "geometry executor" to "architectural reasoner"**

### Objectives

Enable the system to:
1. **Understand spatial relationships** — adjacency, containment, circulation
2. **Know building components** — not just walls, but "master bedroom" with requirements
3. **Reason about architecture** — privacy, orientation, hierarchy, scale
4. **Suggest intelligent layouts** — not random placement, but functionally appropriate

### Deliverables

#### 1. Spatial Relationships Model (`knowledge/spatial/relationships.py`)

**Purpose:** Define and query spatial relationships between architectural elements

**Relationship Types:**
```python
class SpatialRelationType(Enum):
    ADJACENT = "adjacent"           # Shares a boundary
    CONTAINS = "contains"           # Fully inside
    CONNECTS_TO = "connects_to"     # Doorway/opening
    ABOVE = "above"                 # Vertical stacking
    BELOW = "below"
    FACES = "faces"                 # Orientation relationship
    SEPARATES = "separates"         # Acts as barrier between
```

**API:**
```python
class SpatialRelationship:
    source: str              # Room/space ID
    relation: SpatialRelationType
    target: str              # Other room/space ID
    properties: Dict         # Distance, shared wall length, etc.

class SpatialRelationshipGraph:
    def add_relationship(self, rel: SpatialRelationship) -> None
    def query_relationships(self, entity: str, rel_type: Optional[str] = None) -> List[SpatialRelationship]
    def check_constraint(self, constraint: str) -> bool
    # e.g., "bedroom should_not be adjacent_to entrance"
    def suggest_placement(self, entity: str, constraints: List[str]) -> List[Dict]
```

**Integration Points:**
- New module in `ai/reasoning/` directory
- Used by knowledge-enhanced planner

**Tests:**
- Add and query spatial relationships
- Check architectural constraints
- Detect constraint violations
- Suggest valid placements

**Estimated:** ~200-250 lines, 5-6 tests

---

#### 2. Building Component Ontology (`knowledge/components/ontology.py`)

**Purpose:** Hierarchical component taxonomy with functional requirements

**Hierarchy Example:**
```
Space
├── Room
│   ├── Bedroom
│   │   ├── MasterBedroom
│   │   └── GuestBedroom
│   ├── LivingSpace
│   │   ├── LivingRoom
│   │   └── FamilyRoom
│   ├── Kitchen
│   ├── Bathroom
│   │   ├── MasterBathroom
│   │   └── PowderRoom
│   └── UtilitySpace
│       ├── Laundry
│       └── Storage
├── Circulation
│   ├── Hallway
│   ├── Staircase
│   └── Entrance
└── Service
    ├── Garage
    └── MechanicalRoom
```

**Component Schema:**
```python
@dataclass
class ComponentDefinition:
    component_id: str
    name: str
    parent: Optional[str]
    category: str
    functional_requirements: List[str]
    typical_dimensions: Dict[str, Tuple[float, float]]  # min, max for each dimension
    adjacency_preferences: Dict[str, int]  # component_id -> preference score
    required_features: List[str]
    optional_features: List[str]
```

**Example Definition:**
```python
MASTER_BEDROOM = ComponentDefinition(
    component_id="master_bedroom",
    name="Master Bedroom",
    parent="bedroom",
    category="private_space",
    functional_requirements=[
        "privacy",
        "natural_light",
        "direct_bathroom_access",
        "adequate_circulation"
    ],
    typical_dimensions={
        "area_sqm": (12.0, 25.0),  # Not minimum, but typical
        "width_m": (3.5, 5.0),
        "length_m": (4.0, 6.0),
        "ceiling_height_m": (2.7, 3.0)
    },
    adjacency_preferences={
        "master_bathroom": 10,      # Very preferred
        "closet": 8,
        "hallway": 5,
        "entrance": -10,            # Avoid
        "kitchen": -5,
        "garage": -8
    },
    required_features=["window", "door", "closet_space"],
    optional_features=["ensuite_bathroom", "walk_in_closet", "balcony"]
)
```

**API:**
```python
class ComponentOntology:
    def get_component(self, component_id: str) -> ComponentDefinition
    def get_children(self, component_id: str) -> List[ComponentDefinition]
    def get_requirements(self, component_id: str) -> List[str]
    def get_typical_dimensions(self, component_id: str) -> Dict
    def check_adjacency_score(self, comp_a: str, comp_b: str) -> int
```

**Knowledge Files:**
- `knowledge/components/rooms.json` — Room type definitions
- `knowledge/components/circulation.json` — Circulation space definitions
- `knowledge/components/service.json` — Service space definitions

**Tests:**
- Load component definitions from JSON
- Query component hierarchy
- Check functional requirements
- Calculate adjacency preferences
- Integration test with spatial relationships

**Estimated:** ~250-300 lines Python + ~300-400 lines JSON, 6-8 tests

---

#### 3. Spatial Reasoning Rules (`ai/reasoning/spatial.py`)

**Purpose:** Architectural reasoning logic for layout planning

**Rule Types:**
```python
class SpatialRule:
    rule_id: str
    rule_type: str  # "privacy", "circulation", "orientation", "hierarchy"
    description: str
    check_function: Callable
    severity: str  # "required", "recommended", "preferred"
```

**Example Rules:**
```python
PRIVACY_RULES = [
    SpatialRule(
        rule_id="private_space_separation",
        rule_type="privacy",
        description="Bedrooms should not directly connect to public entrance",
        severity="required"
    ),
    SpatialRule(
        rule_id="bathroom_privacy",
        rule_type="privacy",
        description="Bathrooms should not be visible from entrance",
        severity="required"
    )
]

CIRCULATION_RULES = [
    SpatialRule(
        rule_id="room_accessibility",
        rule_type="circulation",
        description="All rooms must be accessible via circulation space",
        severity="required"
    ),
    SpatialRule(
        rule_id="efficient_circulation",
        rule_type="circulation",
        description="Circulation space should be <20% of total area",
        severity="recommended"
    )
]

ORIENTATION_RULES = [
    SpatialRule(
        rule_id="living_space_orientation",
        rule_type="orientation",
        description="Living spaces should face views/daylight where possible",
        severity="preferred"
    )
]
```

**API:**
```python
class SpatialReasoner:
    def __init__(self, ontology: ComponentOntology, relationship_graph: SpatialRelationshipGraph):
        self.ontology = ontology
        self.relationships = relationship_graph
        self.rules = self._load_rules()
    
    def evaluate_layout(self, layout: Dict) -> List[RuleViolation]
    def suggest_improvements(self, layout: Dict) -> List[Suggestion]
    def generate_layout_options(self, requirements: Dict) -> List[Dict]
    def check_rule(self, rule_id: str, context: Dict) -> bool
```

**Integration Points:**
- Used by knowledge-enhanced planner
- Feeds into validation pipeline

**Tests:**
- Check privacy rules
- Check circulation rules
- Evaluate complete layout
- Suggest improvements
- Generate layout options from requirements

**Estimated:** ~300-350 lines, 7-9 tests

---

#### 4. Knowledge-Enhanced Planner (`ai/planner/knowledge_planner.py`)

**Purpose:** Extend base planner with architectural reasoning

**Architecture:**
```python
class KnowledgeEnhancedPlanner(Planner):
    def __init__(self, ..., ontology: ComponentOntology, reasoner: SpatialReasoner):
        super().__init__(...)
        self.ontology = ontology
        self.reasoner = reasoner
    
    def plan_from_requirements(self, requirements: str) -> Plan:
        """
        Enhanced planning flow:
        1. Parse architectural requirements
        2. Query component ontology for functional needs
        3. Apply spatial reasoning rules
        4. Generate layout options
        5. Evaluate against rules
        6. Select best option
        7. Generate detailed modeling plan
        """
        # Parse requirements into structured form
        structured_req = self._parse_requirements(requirements)
        
        # Query ontology for component requirements
        components = self._identify_components(structured_req)
        
        # Apply spatial reasoning
        layout_options = self.reasoner.generate_layout_options(structured_req)
        
        # Evaluate and rank options
        scored_options = self._evaluate_options(layout_options)
        
        # Select best and generate detailed plan
        best_layout = scored_options[0]
        return self._generate_modeling_plan(best_layout)
```

**Integration Points:**
- Extends `ai/planner/planner.py`
- Used by API when architectural reasoning is needed
- Falls back to base planner for pure geometry tasks

**Tests:**
- Parse architectural requirements
- Generate layout with spatial reasoning
- Check rule compliance
- Integration test: "create 2-bedroom house" → valid layout

**Estimated:** ~250-300 lines, 5-7 tests

---

#### 5. Initial Knowledge Base Files

**`knowledge/components/rooms.json`**
```json
{
  "components": [
    {
      "id": "bedroom",
      "name": "Bedroom",
      "category": "private_space",
      "typical_dimensions": {
        "area_sqm": [9.0, 20.0],
        "width_m": [3.0, 4.5],
        "length_m": [3.0, 5.0]
      },
      "functional_requirements": ["privacy", "natural_light", "ventilation"],
      "adjacency_preferences": {
        "hallway": 5,
        "bathroom": 7,
        "entrance": -10
      }
    }
    // ... more room types
  ]
}
```

**`knowledge/spatial/adjacency_rules.json`**
```json
{
  "rules": [
    {
      "id": "private_entrance_separation",
      "source": "bedroom",
      "relation": "connects_to",
      "target": "entrance",
      "allowed": false,
      "severity": "required",
      "reason": "Bedrooms should not open directly to public entrance"
    }
    // ... more rules
  ]
}
```

**`knowledge/dimensions/typical_ranges.json`**
```json
{
  "residential": {
    "wall_height_m": [2.7, 3.0],
    "wall_thickness_mm": [200, 250],
    "door_width_mm": [900, 1000],
    "window_sill_height_mm": [900, 1100]
  },
  "commercial": {
    "wall_height_m": [3.0, 3.6],
    "wall_thickness_mm": [200, 300]
  }
}
```

**Estimated:** ~400-500 lines JSON total

---

### Phase 6 Foundation Summary

**Total Estimated Effort:**
- **Lines of Code:** ~1000-1200 Python + ~400-500 JSON
- **Test Cases:** 28-37 new tests
- **Modules:** 4 new Python modules + 3 JSON knowledge files
- **Integration Points:** 2 existing modules extended (planner, validation)
- **Development Time:** 6-9 hours (estimated)

**Success Criteria:**
- ✅ Spatial relationships can be modeled and queried
- ✅ Component ontology loaded from JSON with 10+ room types
- ✅ Spatial reasoning rules evaluate layouts correctly
- ✅ Knowledge-enhanced planner generates architecturally sound layouts
- ✅ Integration test: "create 2-bedroom house" → compliant design
- ✅ All new tests pass (target: 150+ total tests)

---

## Implementation Order

### Session 1: Phase 5 Core Memory (3-4 hours)
1. Implement `ai/memory/skill_memory.py` + tests
2. Implement `ai/memory/failure_patterns.py` + tests
3. Update `ai/skills/executor.py` to record executions
4. Update `ai/validation/pipeline.py` to feed patterns

### Session 2: Phase 5 Feedback & Query (2-3 hours)
1. Implement `ai/memory/feedback_analysis.py` + tests
2. Implement `ai/memory/query.py` + tests
3. Add `POST /feedback` endpoint to `apps/api/main.py`
4. Update `ai/planner/planner.py` to query memory
5. Run full test suite, verify 120+ passing tests

### Session 3: Phase 6 Knowledge Foundation (3-4 hours)
1. Create `knowledge/` directory structure
2. Implement `knowledge/spatial/relationships.py` + tests
3. Implement `knowledge/components/ontology.py` + tests
4. Create initial JSON knowledge files (rooms, adjacency rules, dimensions)

### Session 4: Phase 6 Reasoning & Integration (3-5 hours)
1. Implement `ai/reasoning/spatial.py` + tests
2. Implement `ai/planner/knowledge_planner.py` + tests
3. Integration test: full architectural planning cycle
4. Update documentation and PROJECT_STATE

---

## Testing Strategy

### Unit Tests
- Each new module has 4-9 focused unit tests
- Test individual functions/methods in isolation
- Mock external dependencies (AgentMemory, MCP)

### Integration Tests
- **Phase 5:** Full cycle (plan → execute → fail → record → query → retry with memory)
- **Phase 6:** Architectural planning ("create 2-bedroom house" → valid layout)
- End-to-end tests remain skipped when services unavailable

### Coverage Target
- Maintain >80% coverage
- Critical paths (planner, executor, validators) aim for >90%

---

## Success Metrics

### Phase 5 Complete When:
- [ ] Skill execution recording operational
- [ ] Pattern recognition detects 3+ pattern types
- [ ] Feedback parsing handles 4+ feedback categories
- [ ] Query interface returns relevant insights
- [ ] Planner adjusts plans based on memory
- [ ] Test suite: 120+ passing tests
- [ ] Coverage: >80%

### Phase 6 Foundation Complete When:
- [ ] Spatial relationship graph operational
- [ ] Component ontology loaded with 10+ components
- [ ] Spatial reasoning evaluates 5+ rule types
- [ ] Knowledge planner generates compliant layouts
- [ ] Integration test: architectural brief → valid design
- [ ] Test suite: 150+ passing tests
- [ ] Coverage: >80%

---

## Known Risks & Mitigations

### Risk 1: AgentMemory Service Dependency
- **Risk:** Phase 5 requires running service at http://localhost:3111
- **Mitigation:** Tests mock the service, real integration optional
- **Action:** Document service startup in README

### Risk 2: Knowledge Base Completeness
- **Risk:** Initial JSON knowledge files may be incomplete
- **Mitigation:** Start with 5-10 core room types, expand iteratively
- **Action:** Design extensible schema from the start

### Risk 3: Spatial Reasoning Complexity
- **Risk:** Layout generation is algorithmically complex
- **Mitigation:** Phase 6 foundation focuses on evaluation, not generation
- **Action:** Full generation algorithm deferred to Phase 6 completion

---

## Documentation Updates Required

After completing both phases:

1. **README.md** — Update with Phase 5 & 6 capabilities
2. **logs/PROJECT_STATE.md** — Mark phases complete, update metrics
3. **logs/DECISIONS.md** — Add ADR-006 (Memory Architecture) and ADR-007 (Knowledge Representation)
4. **logs/CHANGELOG.md** — Document all new modules and features
5. **logs/SESSION_INDEX.md** — Link to implementation session logs
6. **API.md** — Document new memory and knowledge APIs

---

## Next Session Command

To begin Phase 5 implementation:

```
Implement Phase 5 memory completion: create skill_memory.py, failure_patterns.py, feedback_analysis.py, and query.py modules with full tests. Update executor and planner integrations.
```

To begin Phase 6 foundation:

```
Implement Phase 6 architectural knowledge foundation: create spatial relationships model, component ontology, and initial knowledge base JSON files with tests.
```

To do both sequentially:

```
Complete Phase 5 memory system, then start Phase 6 architectural knowledge foundation as outlined in NEXT_PHASE_PLAN.md.
```

---

**Plan Status:** ✅ READY FOR IMPLEMENTATION
