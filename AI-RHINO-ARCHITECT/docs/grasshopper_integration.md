# AI RHINO ARCHITECT - Grasshopper Integration Documentation

## Grasshopper SDK Overview

### Key Assemblies
- `Grasshopper.dll` - Core Grasshopper API
- `GH_IO.dll` - File I/O for .gh/.ghx files
- `GrasshopperPlugin.dll` - Rhino plugin integration

### Core Namespaces
| Namespace | Purpose |
|-----------|---------|
| `Grasshopper` | Core classes (GH_Document, GH_Component, GH_Param) |
| `Grasshopper.Kernel` | Kernel classes (IGH_DocumentObject, IGH_Component) |
| `Grasshopper.Kernel.Parameters` | Parameter types (GH_Number, GH_Point, GH_Curve, etc.) |
| `Grasshopper.Kernel.Types` | Geometry wrappers (GH_Point, GH_Curve, GH_Surface, GH_Brep) |
| `Grasshopper.GUI` | Canvas UI (GH_Canvas, GH_DocumentEditor) |
| `Grasshopper.FileIO` | File reading/writing |

## Grasshopper Integration Architecture

### Python Adapter Interface

```python
class GrasshopperAdapter:
    """Interface for Grasshopper operations"""
    
    # Document
    async def get_active_document(self) -> GHDocumentInfo
    async def create_document(self) -> GHDocumentInfo
    async def save_document(self, path: str) -> bool
    async def load_document(self, path: str) -> GHDocumentInfo
    
    # Components
    async def list_components(self, category: str = None) -> List[GHComponentInfo]
    async def search_components(self, query: str) -> List[GHComponentInfo]
    async def get_component_info(self, component_id: str) -> GHComponentInfo
    
    # Component Creation
    async def create_component(self, component_type: str, location: Point2d) -> GHCreateResult
    async def create_component_by_nickname(self, nickname: str, location: Point2d) -> GHCreateResult
    
    # Connections
    async def connect_wires(self, connections: List[GHConnection]) -> bool
    async def disconnect_wires(self, connections: List[GHConnection]) -> bool
    async def get_wires(self) -> List[GHWireInfo]
    
    # Parameters
    async def set_parameter(self, component_guid: str, param_name: str, value: Any) -> bool
    async def get_parameter(self, component_guid: str, param_name: str) -> Any
    async def set_parameter_expression(self, component_guid: str, param_name: str, expression: str) -> bool
    
    # Data Trees
    async def set_data_tree(self, param_guid: str, tree: GHDataTree) -> bool
    async def get_data_tree(self, param_guid: str) -> GHDataTree
    
    # Solving
    async def solve_document(self) -> GHSolveResult
    async def expire_solution(self, component_guid: str) -> bool
    
    # Baking
    async def bake_component(self, component_guid: str, bake_options: BakeOptions = None) -> List[str]
    async def bake_all(self, bake_options: BakeOptions = None) -> List[str]
    
    # Groups/Clusters
    async def create_group(self, name: str, component_guids: List[str]) -> str
    async def create_cluster(self, name: str, component_guids: List[str]) -> str
    
    # Preview/Display
    async def set_preview(self, component_guid: str, enabled: bool) -> bool
    async def set_selected(self, component_guids: List[str]) -> bool
```

### Data Models

```python
class GHComponentInfo:
    guid: str
    name: str
    nickname: str
    description: str
    category: str
    subcategory: str
    exposure: GHExposure  # primary, secondary, tertiary, hidden, obscure
    inputs: List[GHParamInfo]
    outputs: List[GHParamInfo]

class GHParamInfo:
    name: str
    nickname: str
    description: str
    type: str  # "Number", "Point", "Curve", "Surface", "Brep", "Mesh", "Integer", "Boolean", "String", "Vector", "Plane", "Color", "Interval", "Domain", "DataTree"
    access: GHParamAccess  # item, list, tree
    optional: bool

class GHConnection:
    source_component: str
    source_param: str
    target_component: str
    target_param: str

class GHDataTree:
    """Represents Grasshopper data tree structure"""
    paths: List[List[int]]  # e.g., [[0], [0, 1], [1, 0]]
    data: List[List[Any]]   # Data at each path

class BakeOptions:
    layer_name: str = None
    group_name: str = None
    attributes: ObjectAttributes = None
    delete_existing: bool = False

class GHSolveResult:
    success: bool
    errors: List[str] = []
    warnings: List[str] = []
    solved_components: int = 0
```

## Common Grasshopper Components for Architecture

### Geometry Creation
| Component | Nickname | Category | Purpose |
|-----------|----------|----------|---------|
| `Point` | Pt | Params/Geometry | Create point |
| `Line` | Ln | Curve/Primitive | Create line |
| `Rectangle` | Rec | Curve/Primitive | Create rectangle |
| `Circle` | C | Curve/Primitive | Create circle |
| `Polygon` | Poly | Curve/Primitive | Create polygon |
| `Extrude` | Extr | Surface/Freeform | Extrude curve |
| `Loft` | Loft | Surface/Freeform | Loft curves |
| `Sweep1` | Swp1 | Surface/Freeform | Single rail sweep |
| `Sweep2` | Swp2 | Surface/Freeform | Two rail sweep |
| `Boundary` | Bnd | Surface/Freeform | Surface from boundary |
| `Brep` | Brep | Surface/Util | Create Brep |
| `Mesh` | Mesh | Mesh/Triangulation | Create mesh |

### Transform
| Component | Nickname | Category | Purpose |
|-----------|----------|----------|---------|
| `Move` | Move | XForm/Euclidean | Translate geometry |
| `Rotate` | Rot | XForm/Euclidean | Rotate geometry |
| `Scale` | Scale | XForm/Euclidean | Scale geometry |
| `Mirror` | Mir | XForm/Euclidean | Mirror geometry |
| `Orient` | Ori | XForm/Euclidean | Orient geometry |
| `Array` | Arr | XForm/Array | Linear/polar array |

### Analysis
| Component | Nickname | Category | Purpose |
|-----------|----------|----------|---------|
| `Area` | Area | Surface/Analysis | Surface area |
| `Volume` | Vol | Surface/Analysis | Volume |
| `Length` | Len | Curve/Analysis | Curve length |
| `Centroid` | Cent | Surface/Analysis | Centroid |
| `BrepEdges` | Edg | Surface/Analysis | Brep edges |
| `BrepFaces` | Fac | Surface/Analysis | Brep faces |

### Data
| Component | Nickname | Category | Purpose |
|-----------|----------|----------|---------|
| `Number` | Num | Params/Primitive | Numeric value |
| `Integer` | Int | Params/Primitive | Integer value |
| `Boolean` | Bool | Params/Primitive | Boolean value |
| `String` | Str | Params/Primitive | Text value |
| `List` | List | Sets/List | List operations |
| `Tree` | Tree | Sets/Tree | Tree operations |
| `Graft` | Graft | Sets/Tree | Graft data |
| `Flatten` | Flat | Sets/Tree | Flatten data |
| `Simplify` | Simp | Sets/Tree | Simplify paths |
| `Cull` | Cull | Sets/Sequence | Cull items |

### Math
| Component | Nickname | Category | Purpose |
|-----------|----------|----------|---------|
| `Add` | + | Math/Operators | Addition |
| `Subtract` | - | Math/Operators | Subtraction |
| `Multiply` | * | Math/Operators | Multiplication |
| `Divide` | / | Math/Operators | Division |
| `Power` | Pow | Math/Operators | Power |
| `Sqrt` | Sqrt | Math/Operators | Square root |
| `Sin` | Sin | Math/Trig | Sine |
| `Cos` | Cos | Math/Trig | Cosine |
| `Remap` | Rmp | Math/Domain | Remap numbers |
| `Bounds` | Bnd | Math/Domain | Domain bounds |
| `ConstructDomain` | Dom | Math/Domain | Create domain |
| `DeconstructDomain` | DDom | Math/Domain | Deconstruct domain |

### Architecture-Specific Components

#### Parametric Facade
```
Surface → DivideSurface → UV points
         → PointDeform / Attractor
         → Panel (Rectangle/Hexagon)
         → Extrude (variable depth)
         → CustomPreview (color by depth)
```

#### Attractor Pattern
```
Grid of points → Distance to attractor point
              → Remap to panel depth
              → Extrude panels
```

#### Space Planning
```
Boundary curve → Subdivide (Voronoi/Grid)
              → Assign functions (Area/Adjacency)
              → Optimize (Galapagos/Wallacei)
              → Generate walls/furniture
```

#### Structural Grid
```
Building footprint → Grid (Rectangular/Radial)
                  → Columns at intersections
                  → Beams along grid lines
                  → Slabs spanning beams
```

## GH Data Tree Patterns

### Common Tree Structures

```python
# Single item per branch (Grafted)
# Path: {0}, {1}, {2}...
# Data: [item0], [item1], [item2]...

# List per branch
# Path: {0}, {1}...
# Data: [item0, item1, item2], [item3, item4]...

# Nested (e.g., floors > rooms > walls)
# Path: {0;0}, {0;1}, {1;0}, {1;1}...
# Data: [walls], [walls], [walls], [walls]...
```

### Tree Operations

```python
# Graft: {0} → {0;0}
gh.graft(tree)

# Flatten: {0;0}, {0;1} → {0}
gh.flatten(tree)

# Simplify: {0;0;0} → {0}
gh.simplify(tree)

# Flip: {0;1} → {1;0}
gh.flip(tree)

# Path Mapper: {A;B} → {B;A}
gh.path_mapper(tree, "{A;B}", "{B;A}")
```

## Parametric Definition Generation

### From Python (rhino3dm + GH_IO)

```python
import gh_io
import Grasshopper as gh

# Create document
doc = gh.GH_Document()

# Add components
pt = gh.Kernel.Parameters.Param_Point()
pt.NickName = "Pt"
doc.AddObject(pt, False)

# Add number slider
slider = gh.Kernel.Special.GH_NumberSlider()
slider.NickName = "Radius"
slider.Slider.Minimum = 0
slider.Slider.Maximum = 100
slider.Slider.Value = 10
doc.AddObject(slider, False)

# Connect
doc.ConnectWires(slider.Params.Output[0], pt.Params.Input[0])

# Save
writer = gh_io.GH_Archive()
writer.AppendObject(doc)
writer.WriteToFile("definition.gh")
```

### From JSON Specification

```json
{
  "name": "Parametric Facade",
  "components": [
    {
      "id": "surface",
      "type": "Surface",
      "nickname": "Base Surface",
      "location": [100, 100]
    },
    {
      "id": "divide",
      "type": "DivideSurface",
      "nickname": "Divide",
      "location": [300, 100],
      "inputs": {
        "U": 10,
        "V": 10
      }
    },
    {
      "id": "attractor",
      "type": "Point",
      "nickname": "Attractor",
      "location": [300, 300]
    },
    {
      "id": "distance",
      "type": "Distance",
      "nickname": "Dist to Attractor",
      "location": [500, 200]
    },
    {
      "id": "remap",
      "type": "Remap",
      "nickname": "Remap Depth",
      "location": [700, 200],
      "inputs": {
        "Target": [0.05, 0.2]
      }
    },
    {
      "id": "panel",
      "type": "Rectangle",
      "nickname": "Panel",
      "location": [900, 100]
    },
    {
      "id": "extrude",
      "type": "Extrude",
      "nickname": "Extrude Panels",
      "location": [1100, 100]
    }
  ],
  "connections": [
    {"source": "surface", "sourceParam": "S", "target": "divide", "targetParam": "S"},
    {"source": "divide", "sourceParam": "P", "target": "distance", "targetParam": "A"},
    {"source": "attractor", "sourceParam": "P", "target": "distance", "targetParam": "B"},
    {"source": "distance", "sourceParam": "D", "target": "remap", "targetParam": "V"},
    {"source": "divide", "sourceParam": "P", "target": "panel", "targetParam": "P"},
    {"source": "remap", "sourceParam": "R", "target": "extrude", "targetParam": "D"}
  ]
}
```

## MCP Integration (via rhinomcp)

### Available GH Tools

```python
# Search components
await mcp.call_tool("gh_search_components", {"query": "divide surface"})

# List all components in category
await mcp.call_tool("gh_list_components", {"category": "Surface"})

# Create component
await mcp.call_tool("gh_create_component", {
    "component_type": "DivideSurface",
    "location": {"x": 300, "y": 100}
})

# Connect wires
await mcp.call_tool("gh_connect_wires", {
    "connections": [
        {"source_component": "guid1", "source_param": "S", "target_component": "guid2", "target_param": "S"}
    ]
})

# Set parameter
await mcp.call_tool("gh_set_param", {
    "component_guid": "guid1",
    "param_name": "U",
    "value": 20
})

# Bake to Rhino
await mcp.call_tool("gh_bake", {
    "component_guid": "guid1"
})
```

## Definition Templates

### Parametric Facade Template
```python
FACADE_TEMPLATE = {
    "components": [
        {"id": "surface", "type": "Surface", "location": [100, 100]},
        {"id": "divide", "type": "DivideSurface", "location": [300, 100], "inputs": {"U": "u_count", "V": "v_count"}},
        {"id": "attractor", "type": "Point", "location": [300, 300]},
        {"id": "distance", "type": "Distance", "location": [500, 200]},
        {"id": "remap", "type": "Remap", "location": [700, 200], "inputs": {"Target": "depth_range"}},
        {"id": "panel", "type": "Rectangle", "location": [900, 100]},
        {"id": "extrude", "type": "Extrude", "location": [1100, 100]},
        {"id": "preview", "type": "CustomPreview", "location": [1300, 100]}
    ],
    "connections": [
        {"source": "surface", "target": "divide", "sourceParam": "S", "targetParam": "S"},
        {"source": "divide", "target": "distance", "sourceParam": "P", "targetParam": "A"},
        {"source": "attractor", "target": "distance", "sourceParam": "P", "targetParam": "B"},
        {"source": "distance", "target": "remap", "sourceParam": "D", "targetParam": "V"},
        {"source": "divide", "target": "panel", "sourceParam": "P", "targetParam": "P"},
        {"source": "remap", "target": "extrude", "sourceParam": "R", "targetParam": "D"},
        {"source": "panel", "target": "extrude", "sourceParam": "C", "targetParam": "B"},
        {"source": "extrude", "target": "preview", "sourceParam": "G", "targetParam": "G"}
    ],
    "parameters": {
        "u_count": {"type": "integer", "default": 10, "min": 2, "max": 50},
        "v_count": {"type": "integer", "default": 10, "min": 2, "max": 50},
        "depth_range": {"type": "domain", "default": [0.05, 0.3]},
        "attractor_point": {"type": "point", "default": [0, 0, 0]}
    }
}
```

### Space Planning Template
```python
SPACE_PLANNING_TEMPLATE = {
    "components": [
        {"id": "boundary", "type": "Curve", "location": [100, 100]},
        {"id": "subdivide", "type": "Voronoi", "location": [300, 100], "inputs": {"Count": "room_count"}},
        {"id": "areas", "type": "Area", "location": [500, 100]},
        {"id": "galapagos", "type": "Galapagos", "location": [700, 100]},
        {"id": "walls", "type": "Extrude", "location": [900, 100]}
    ],
    "parameters": {
        "room_count": {"type": "integer", "default": 6},
        "room_areas": {"type": "list[float]", "default": [20, 15, 12, 10, 8, 6]},
        "wall_height": {"type": "float", "default": 3000},
        "wall_thickness": {"type": "float", "default": 200}
    }
}
```

## Error Handling

```python
try:
    result = await gh_adapter.solve_document()
    if not result.success:
        for error in result.errors:
            logger.error(f"GH Error: {error}")
        # Attempt recovery
        await gh_adapter.expire_solution(problematic_component)
        await gh_adapter.solve_document()
except GHException as e:
    logger.error(f"Grasshopper error: {e}")
    # Fallback to RhinoCommon direct geometry creation
```

## Performance Tips

1. **Minimize solves**: Batch parameter changes, then solve once
2. **Disable preview** for heavy components during solving
3. **Use data trees efficiently**: Avoid unnecessary grafting/flattening
4. **Cache component references**: Don't search by name repeatedly
5. **Use clusters** for reusable sub-definitions
6. **Profile with `GH_Profiler`**: Identify slow components

## Testing

```python
@pytest.mark.asyncio
async def test_parametric_facade():
    gh = GrasshopperAdapter()
    await gh.connect()
    
    # Create facade definition
    result = await gh.create_definition_from_template(
        "parametric_facade",
        {"u_count": 5, "v_count": 5, "depth_range": [0.05, 0.2]}
    )
    
    assert result.success
    assert len(result.baked_guids) > 0
    
    # Validate geometry
    for guid in result.baked_guids:
        validation = await rhino_adapter.validate_geometry(guid)
        assert validation.is_valid
        assert validation.is_closed_solid
```