# Modeling Skill Schema

**Schema version:** `0.1.0`  
**Scope:** Reusable modeling skills for the AI RHINO ARCHITECT knowledge library.

This document defines the contract used to describe, discover, validate, execute, and learn from modeling skills. A skill describes the operation and its evidence contract; it does not expose arbitrary implementation code to the model.

## 1. Design Principles

1. **Declarative operations:** Skills describe intent, parameters, operations, and validation without embedding implementation details.
2. **Reusable and parameterized:** One skill definition supports repeated use across projects and model states.
3. **Validation before commit:** Inputs, preconditions, geometry, dimensions, and scope are checked before the document is changed.
4. **Explicit units:** Numeric values are interpreted in the active Rhino document units unless a unit is explicitly supplied.
5. **Controlled mutation:** Create, modify, and boolean skills declare their side effects and risk level.
6. **Evidence-based results:** Execution returns object identifiers and measurable validation evidence.
7. **Structured failure:** Every failure is returned with a stable code, cause, and recovery guidance.
8. **Versioned contracts:** `schema_version` changes when field names, types, enums, or validation semantics change.

## 2. Canonical Skill Fields

| Field | Type | Required | Meaning |
|---|---|---:|---|
| `schema_version` | string | Yes | Semantic version of this schema contract, for example `0.1.0`. |
| `skill_id` | string | Yes | Stable snake_case identifier, unique within the skill registry. |
| `name` | string | Yes | Human-readable skill name. |
| `description` | string | Yes | Concise description of the operation and expected result. |
| `skill_type` | enum | Yes | Operation class: `create`, `read`, `modify`, `boolean`, or `analysis`. |
| `category` | enum | Yes | Domain: `geometry`, `architecture`, `parametric`, or `site`. |
| `inputs` | string array | Yes | Ordered input names accepted by the skill. Names must be unique. |
| `outputs` | string array | Yes | Result names returned after successful execution. |
| `parameters` | object | Yes | Named parameter descriptors keyed by input name. |
| `preconditions` | string array | Yes | Stable precondition rule identifiers that must pass before execution. |
| `operations` | string array | Yes | Stable low-level operation identifiers executed in order. |
| `validation` | string array | Yes | Stable validation rule identifiers applied after execution. |
| `failure_modes` | string array | Yes | Stable failure codes that the skill can return. |
| `metadata` | object | Yes | Discovery, ownership, risk, tooling, and lifecycle information. |

### 2.1 Parameter Descriptor

Each entry in `parameters` uses this shape:

| Field | Type | Required | Meaning |
|---|---|---:|---|
| `type` | enum | Yes | Parameter type from the type catalog. |
| `required` | boolean | Yes | Whether the parameter must be supplied. |
| `description` | string | Yes | Human-readable parameter contract. |
| `default` | scalar | No | Default value used when the parameter is optional. |
| `minimum` | number | No | Inclusive numeric lower bound. |
| `maximum` | number | No | Inclusive numeric upper bound. |
| `units` | string | No | Unit name or `model_units`. |
| `choices` | string array | No | Allowed values for an enum parameter. |
| `geometry_role` | string | No | Semantic role of a geometry reference, such as `profile`, `rail`, or `boundary`. |

## 3. Type Catalog

### 3.1 Categories

| Category | Supported skill subjects |
|---|---|
| `geometry` | Point, line, curve, rectangle, circle, surface, extrusion, Brep, mesh, SubD, point cloud. |
| `architecture` | Wall, floor, door, window, column, beam, stair, roof, room, building mass. |
| `parametric` | Facade, panel, attractor, pattern, grid, parametric component, Grasshopper definition. |
| `site` | Site, terrain, setback, orientation, context mass, site constraint. |

A skill has exactly one primary `category`. A cross-domain skill should use the category that describes its primary result and list secondary domains in `metadata.tags`.

### 3.2 Skill Types

| Type | Behavior | Typical risk |
|---|---|---|
| `create` | Adds new geometry or document objects. | Low to medium mutation. |
| `read` | Queries geometry, document state, measurements, or attributes without mutation. | Read-only. |
| `modify` | Moves, rotates, scales, replaces, or changes attributes of existing objects. | Medium mutation. |
| `boolean` | Unions, subtracts, intersects, splits, or trims solids and curves. | High mutation; requires explicit scope. |
| `analysis` | Evaluates validity, dimensions, relationships, performance, or compliance without changing geometry. | Read-only. |

### 3.3 Parameter Types

| Type | Accepted representation |
|---|---|
| `point` | A 3D point or point reference. |
| `vector` | A 3D vector. |
| `plane` | A construction plane or plane reference. |
| `curve` | A Rhino curve reference or serializable curve definition. |
| `surface` | A Rhino surface reference. |
| `brep` | A Rhino Brep reference. |
| `mesh` | A Rhino mesh reference. |
| `guid` | A Rhino document object identifier. |
| `object_ref` | A typed document object reference. |
| `number` | A finite numeric value. |
| `integer` | A finite integer value. |
| `boolean` | `true` or `false`. |
| `string` | Text value. |
| `enum` | One value from `choices`. |
| `list` | A homogeneous list with an item type declared in metadata. |

## 4. Validation Rules

Validation identifiers are stable machine-readable codes. A skill may reference global rules and may add skill-specific rules in its own registry.

### 4.1 Contract Validation

- `schema_valid`: The skill definition conforms to this schema version.
- `required_inputs_present`: Every required input is present.
- `parameter_type_valid`: Each value matches its declared parameter type.
- `parameter_range_valid`: Numeric values satisfy `minimum` and `maximum`.
- `enum_value_valid`: Enum values occur in `choices`.
- `units_resolved`: All dimensional values have a resolvable unit.
- `preconditions_met`: Every declared precondition passed.
- `scope_allowed`: The target objects and document region are permitted for mutation.

### 4.2 Geometry Validation

- `valid_curve`: The curve is non-null, finite, and usable by the operation.
- `valid_surface`: The surface is non-null and geometrically valid.
- `valid_brep`: The Brep is non-null and passes Rhino validity checks.
- `closed_solid`: The result is a closed solid where required.
- `manifold`: The result has manifold topology where required.
- `no_self_intersections`: The result contains no unintended self-intersections.
- `valid_extrusion`: The extrusion direction and profile produce a valid result.
- `valid_boolean`: The boolean result is valid and retains the intended topology.

### 4.3 Dimensional and Relationship Validation

- `positive_height`: Height is greater than zero.
- `positive_thickness`: Thickness is greater than zero.
- `positive_radius`: Radius is greater than zero.
- `correct_dimensions`: Result dimensions match requested values within document tolerance.
- `bounding_box_valid`: The result bounding box is finite and within declared limits.
- `expected_object_count`: Execution returns the declared number of objects.
- `required_relationships`: Required containment, adjacency, alignment, or connectivity relationships exist.
- `document_state_consistent`: Object IDs, layers, attributes, and document state are consistent after commit.

## 5. Failure Modes

Failure entries are stable codes. The executor must return the code, a concise cause, the affected input or operation, and a recovery action when available.

| Failure code | Meaning | Typical recovery |
|---|---|---|
| `missing_input` | A required input was not supplied. | Request or infer the missing value. |
| `invalid_parameter` | A value does not match its declared type or range. | Normalize or reject the value. |
| `unit_mismatch` | Values use incompatible or unresolved units. | Resolve units before execution. |
| `precondition_failed` | One or more preconditions did not pass. | Repair the input or select another skill. |
| `permission_denied` | The requested mutation is outside the allowed scope. | Narrow the scope or request approval. |
| `tool_unavailable` | A required Rhino, Grasshopper, or adapter tool is unavailable. | Retry after connection recovery. |
| `execution_failed` | The low-level operation could not complete. | Roll back and inspect the operation result. |
| `invalid_curve` | The profile or baseline curve is unusable. | Rebuild, simplify, or replace the curve. |
| `extrusion_failed` | Curve extrusion did not produce a valid result. | Check direction, tolerance, and curve continuity. |
| `cap_failed` | A solid could not be capped. | Repair the boundary or use a Brep construction path. |
| `boolean_failed` | A boolean operation failed or produced invalid topology. | Simplify inputs, adjust tolerance, or use a fallback operation. |
| `invalid_brep` | The generated Brep is invalid. | Run Brep repair or reject the result. |
| `open_solid` | A result expected to be closed is open. | Add caps or repair boundary loops. |
| `self_intersection` | The result contains unintended self-intersections. | Adjust geometry or tolerances. |
| `dimension_mismatch` | Result dimensions differ from the request. | Re-measure and correct the generating parameters. |
| `rollback_failed` | A failed transaction could not be restored. | Stop execution and report the document state. |

## 6. Execution Contract

The executor processes a skill in this order:

1. Load the skill definition and verify `schema_version`.
2. Resolve units, object references, defaults, and document context.
3. Validate required inputs, parameter types, ranges, and enums.
4. Evaluate `preconditions`.
5. Check mutation scope, permissions, and risk level.
6. Run `operations` in declared order.
7. Run `validation` against the produced geometry and document state.
8. Commit only after validation succeeds; otherwise roll back.
9. Return output identifiers, measurements, validation evidence, and warnings.
10. Record structured failures and feedback for skill memory.

A successful tool response does not by itself prove a successful model operation. Geometry and document-state validation are mandatory for mutation skills.

## 7. Metadata Contract

`metadata` may contain:

| Field | Type | Meaning |
|---|---|---|
| `version` | string | Skill implementation version, independent of schema version. |
| `status` | enum | `draft`, `experimental`, `stable`, or `deprecated`. |
| `author` | string | Maintainer or team. |
| `risk_level` | enum | `read_only`, `low`, `medium`, or `high`. |
| `side_effects` | string array | Declared document or external-system effects. |
| `rhino_tools` | string array | Required Rhino adapter or MCP tool identifiers. |
| `grasshopper_tools` | string array | Required Grasshopper tool identifiers. |
| `tags` | string array | Search and discovery tags. |
| `references` | string array | Documentation, standards, or source references. |
| `created_at` | string | ISO-8601 creation timestamp. |
| `updated_at` | string | ISO-8601 last update timestamp. |

## 8. Example: `create_wall`

```json
{
  "schema_version": "0.1.0",
  "skill_id": "create_wall",
  "name": "Create Wall",
  "description": "Create a capped solid wall by extruding a baseline curve along the document Z axis.",
  "skill_type": "create",
  "category": "architecture",
  "inputs": ["curve", "height", "thickness"],
  "outputs": ["wall_brep", "wall_guid"],
  "parameters": {
    "curve": {
      "type": "curve",
      "required": true,
      "description": "Planar baseline curve defining the wall centerline or footprint.",
      "geometry_role": "baseline"
    },
    "height": {
      "type": "number",
      "required": true,
      "description": "Vertical wall height.",
      "minimum": 0,
      "units": "model_units"
    },
    "thickness": {
      "type": "number",
      "required": true,
      "description": "Wall thickness measured perpendicular to the baseline.",
      "minimum": 0,
      "units": "model_units"
    }
  },
  "preconditions": [
    "document_connected",
    "valid_curve",
    "positive_height",
    "positive_thickness",
    "scope_allowed"
  ],
  "operations": [
    "resolve_units",
    "extrude_curve",
    "cap_brep",
    "add_brep_to_document"
  ],
  "validation": [
    "valid_brep",
    "closed_solid",
    "manifold",
    "correct_dimensions",
    "expected_object_count",
    "document_state_consistent"
  ],
  "failure_modes": [
    "missing_input",
    "invalid_parameter",
    "unit_mismatch",
    "precondition_failed",
    "permission_denied",
    "tool_unavailable",
    "execution_failed",
    "invalid_curve",
    "extrusion_failed",
    "cap_failed",
    "invalid_brep",
    "open_solid",
    "dimension_mismatch",
    "rollback_failed"
  ],
  "metadata": {
    "version": "0.1.0",
    "status": "experimental",
    "author": "AI RHINO ARCHITECT",
    "risk_level": "medium",
    "side_effects": ["add wall Brep to Rhino document"],
    "rhino_tools": ["create_wall", "extrude_curve", "add_brep"],
    "grasshopper_tools": [],
    "tags": ["architecture", "wall", "solid", "extrusion"],
    "references": ["docs/architecture.md", "docs/rhino_integration.md"]
  }
}
```

Example invocation:

```text
create_wall(
  curve=<Rhino baseline curve>,
  height=3000,
  thickness=200
)
```

Expected successful result:

```json
{
  "status": "success",
  "data": {
    "wall_guid": "rhino-object-guid",
    "wall_brep": "brep-reference",
    "validation": {
      "valid_brep": true,
      "closed_solid": true,
      "height": 3000,
      "thickness": 200
    }
  }
}
```

## 9. Registry and Discovery

- Store one machine-readable skill instance per skill ID using the naming convention `<skill_id>.json`.
- Keep this document as the shared schema and validation reference.
- Index skills by `category`, `skill_type`, `tags`, and declared Rhino/Grasshopper tools.
- Reject duplicate `skill_id` values and unknown enum values at registry load time.
- Keep skill definitions independent of provider-specific prompts; prompt text may be generated from `name`, `description`, `inputs`, `outputs`, and `failure_modes`.
- Record execution outcomes separately in skill memory and failure memory; do not mutate the source definition during execution.

## 10. Skill Authoring Checklist

Before a skill is marked `stable`:

- [ ] It has a unique `skill_id` and a valid `schema_version`.
- [ ] Every input has a parameter descriptor.
- [ ] Required and optional parameters are explicit.
- [ ] Units, ranges, and enum choices are declared where applicable.
- [ ] Preconditions cover document, input, and scope requirements.
- [ ] Operations are ordered and map to controlled tools.
- [ ] Validation covers geometry, dimensions, relationships, and document state.
- [ ] Failure modes include recovery guidance.
- [ ] Side effects and risk level are declared.
- [ ] A deterministic example and expected result are documented.
- [ ] Unit and integration tests cover success and failure paths.
