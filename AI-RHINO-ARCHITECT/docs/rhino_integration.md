# AI RHINO ARCHITECT - Rhino Integration Documentation

## RhinoCommon API Overview

### Core Namespaces

| Namespace | Purpose |
|-----------|---------|
| `Rhino.Geometry` | Geometric types (Point3d, Vector3d, Curve, Surface, Brep, Mesh, etc.) |
| `Rhino.DocObjects` | Document object types (RhinoObject, ObjectAttributes, Layer, etc.) |
| `Rhino.Commands` | Command infrastructure (Command, Result, RunMode) |
| `Rhino.Input` | User input (GetPoint, GetObject, GetString, etc.) |
| `Rhino.Input.Custom` | Custom input validation |
| `Rhino.DocObjects.Tables` | Document tables (ObjectTable, LayerTable, etc.) |
| `Rhino.Plugins` | Plugin infrastructure (PlugIn, PluginDescription) |
| `Rhino.ApplicationSettings` | Application settings |
| `Rhino.Display` | Display conduits, viewports |
| `Rhino.FileIO` | File I/O (3dm, OBJ, STL, etc.) |

### Key Geometry Classes

```
GeometryBase (abstract)
├── Point / Point3d / Point3f
├── Curve (abstract)
│   ├── LineCurve
│   ├── ArcCurve
│   ├── NurbsCurve
│   ├── PolyCurve
│   ├── PolylineCurve
│   └── CurveProxy (BrepEdge, BrepTrim)
├── Surface (abstract)
│   ├── PlaneSurface
│   ├── NurbsSurface
│   ├── Extrusion
│   ├── RevSurface
│   ├── SumSurface
│   └── SurfaceProxy (BrepFace)
├── Brep (Boundary Representation)
│   ├── BrepFace
│   ├── BrepEdge
│   ├── BrepTrim
│   ├── BrepLoop
│   └── BrepVertex
├── Mesh
├── Extrusion
├── SubD
└── PointCloud
```

### Key Document Classes

```
RhinoDoc (ActiveDoc)
├── Objects (ObjectTable)
│   ├── AddPoint, AddLine, AddCurve, AddSurface, AddBrep, AddMesh
│   ├── AddExtrusion, AddSubD
│   ├── Find, FindByLayer, FindByGroup
│   ├── Delete, Undelete, Purge
│   ├── ModifyAttributes, Replace
│   └── GetSelectedObjects
├── Layers (LayerTable)
├── Groups (GroupTable)
├── Materials (MaterialTable)
├── Linetypes (LinetypeTable)
├── Views (ViewTable)
├── NamedViews (NamedViewTable)
├── ModelUnitSystem (UnitSystem)
├── ModelAbsoluteTolerance
├── ModelAngleTolerance
└── UndoRecording
```

## Rhino Plugin Architecture

### Plugin Structure (C# .NET 8)

```
RhinoMCPPlugin/
├── RhinoMCPPlugin.csproj          # .NET 8 project targeting RhinoCommon 8
├── RhinoMCPPlugin.cs              # Main plugin class (inherits Rhino.Plugins.PlugIn)
├── RhinoMCPServer.cs              # TCP server for MCP communication
├── Commands/
│   ├── McpStartCommand.cs         # Start MCP server
│   └── McpStopCommand.cs          # Stop MCP server
├── Functions/
│   ├── _Registry.cs               # Command dispatch via reflection
│   ├── _Utils.cs                  # Helper methods
│   ├── GeometryCreation.cs        # create_object, create_objects
│   ├── GeometryModification.cs    # modify_object, boolean ops
│   ├── GeometryQuery.cs           # get_objects, analyze_objects
│   ├── Selection.cs               # select_objects
│   ├── Layers.cs                  # create_layer, get_layers
│   ├── Viewport.cs                # capture_viewport
│   ├── Commands.cs                # run_command
│   ├── GrasshopperCatalog.cs      # gh_search, gh_list
│   └── GrasshopperMutation.cs     # gh_create, gh_connect, gh_set_param
├── Contracts/
│   └── schemas/                   # JSON Schema for MCP tools
└── Properties/
    └── AssemblyInfo.cs
```

### MCP Tool Protocol

**Transport**: JSON-RPC 2.0 over TCP (default 127.0.0.1:8765) or stdio

**Message Format**:
```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "method": "tools/call",
  "params": {
    "name": "create_object",
    "arguments": {
      "type": "line",
      "start": [0, 0, 0],
      "end": [1000, 1000, 0]
    }
  }
}
```

**Response**:
```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "result": {
    "status": "success",
    "data": {
      "guid": "abc123...",
      "type": "curve"
    }
  }
}
```

### Available MCP Tools (from rhinomcp)

| Category | Tools |
|----------|-------|
| **Object Creation** | `create_object`, `create_objects` |
| **Object Modification** | `modify_object`, `modify_objects`, `boolean_union`, `boolean_difference`, `boolean_intersection` |
| **Advanced Modeling** | `loft`, `extrude_curve`, `sweep1`, `offset_curve`, `pipe` |
| **Curve Operations** | `project_curve`, `intersect_curves`, `split_curve` |
| **Analysis** | `analyze_objects` (length, area, volume, bbox) |
| **Selection** | `select_objects` (filter by name, color, layer, type) |
| **Query** | `get_objects`, `get_object_info`, `get_selected_objects_info` |
| **Attributes** | `get_object_attributes`, `update_object_attributes` |
| **Layers** | `create_layer`, `delete_layer`, `get_or_set_current_layer` |
| **Document** | `get_document_summary` |
| **Viewport** | `capture_viewport` |
| **Commands** | `run_command` (native Rhino commands) |
| **Scripting** | `execute_rhinoscript_python_code`, `execute_rhinocommon_csharp_code` |
| **Documentation** | `search_rhinoscript_functions`, `get_rhinoscript_docs` |
| **Grasshopper** | `gh_search_components`, `gh_list_components`, `gh_create_component`, `gh_connect_wires`, `gh_set_param`, `gh_bake` |

## Python Adapter Architecture

### Adapter Interface

```python
class RhinoAdapter:
    """Abstract interface for Rhino operations"""
    
    # Connection
    async def connect(self) -> bool
    async def disconnect(self) -> bool
    async def is_connected(self) -> bool
    
    # Document
    async def get_document_summary(self) -> DocumentSummary
    async def get_model_units(self) -> UnitSystem
    async def get_objects(self, filter: ObjectFilter) -> List[RhinoObject]
    async def get_selected_objects(self) -> List[RhinoObject]
    
    # Geometry Creation
    async def create_point(self, point: Point3d) -> CreateResult
    async def create_line(self, start: Point3d, end: Point3d) -> CreateResult
    async def create_rectangle(self, plane: Plane, width: float, height: float) -> CreateResult
    async def create_curve(self, points: List[Point3d], degree: int = 3) -> CreateResult
    async def create_circle(self, center: Point3d, radius: float, plane: Plane = None) -> CreateResult
    async def create_arc(self, center: Point3d, radius: float, angle: float, plane: Plane = None) -> CreateResult
    async def create_surface(self, curves: List[Curve]) -> CreateResult
    async def create_extrusion(self, profile: Curve, direction: Vector3d) -> CreateResult
    async def create_brep(self, surfaces: List[Surface]) -> CreateResult
    
    # Architecture
    async def create_wall(self, baseline: Curve, height: float, thickness: float) -> CreateResult
    async def create_floor(self, boundary: Curve, thickness: float) -> CreateResult
    async def create_column(self, base: Point3d, top: Point3d, radius: float) -> CreateResult
    async def create_door(self, wall_guid: str, position: float, width: float, height: float) -> CreateResult
    async def create_window(self, wall_guid: str, position: float, width: float, height: float, sill_height: float) -> CreateResult
    async def create_stair(self, start: Point3d, end: Point3d, width: float, riser_height: float, tread_depth: float) -> CreateResult
    async def create_roof(self, boundary: Curve, height: float, slope: float) -> CreateResult
    
    # Modification
    async def move_object(self, guid: str, vector: Vector3d) -> ModifyResult
    async def rotate_object(self, guid: str, center: Point3d, angle: float, axis: Vector3d) -> ModifyResult
    async def scale_object(self, guid: str, center: Point3d, factor: float) -> ModifyResult
    async def copy_object(self, guid: str, vector: Vector3d) -> CreateResult
    async def delete_object(self, guid: str) -> bool
    async def offset_curve(self, guid: str, distance: float) -> CreateResult
    async def fillet_curve(self, guid1: str, guid2: str, radius: float) -> CreateResult
    
    # Boolean
    async def boolean_union(self, guids: List[str]) -> CreateResult
    async def boolean_difference(self, guids: List[str]) -> CreateResult
    async def boolean_intersection(self, guids: List[str]) -> CreateResult
    
    # Advanced
    async def loft(self, curves: List[str], loose: bool = False) -> CreateResult
    async def sweep1(self, rail: str, cross_sections: List[str]) -> CreateResult
    async def extrude_curve(self, curve_guid: str, direction: Vector3d) -> CreateResult
    
    # Analysis
    async def analyze_object(self, guid: str) -> AnalysisResult
    async def measure_distance(self, point1: Point3d, point2: Point3d) -> float
    async def measure_area(self, guid: str) -> float
    async def measure_volume(self, guid: str) -> float
    async def check_intersections(self, guid1: str, guid2: str) -> IntersectionResult
    async def validate_geometry(self, guid: str) -> ValidationResult
    
    # Viewport
    async def capture_viewport(self, view_name: str = None) -> bytes
    
    # Layers
    async def create_layer(self, name: str, color: Color = None) -> LayerResult
    async def set_current_layer(self, name: str) -> bool
    async def get_layers(self) -> List[LayerInfo]
    
    # Undo/Redo
    async def undo(self) -> bool
    async def redo(self) -> bool
    
    # Grasshopper
    async def gh_search_components(self, query: str) -> List[GHComponentInfo]
    async def gh_list_components(self) -> List[GHComponentInfo]
    async def gh_create_component(self, component_type: str, location: Point2d) -> GHCreateResult
    async def gh_connect_wires(self, connections: List[GHConnection]) -> bool
    async def gh_set_param(self, component_guid: str, param_name: str, value: any) -> bool
    async def gh_bake(self, component_guid: str) -> List[str]
```

### Data Models

```python
# Unit System
class UnitSystem(Enum):
    MILLIMETERS = 1
    CENTIMETERS = 2
    METERS = 3
    INCHES = 4
    FEET = 5

# Point/Vector
class Point3d:
    x: float
    y: float
    z: float

class Vector3d:
    x: float
    y: float
    z: float

class Plane:
    origin: Point3d
    x_axis: Vector3d
    y_axis: Vector3d
    z_axis: Vector3d

# Results
class CreateResult:
    success: bool
    guid: str = None
    object_type: str = None
    error: str = None

class ModifyResult:
    success: bool
    guid: str = None
    error: str = None

class AnalysisResult:
    length: float = None
    area: float = None
    volume: float = None
    bounding_box: BoundingBox = None
    centroid: Point3d = None
    is_valid: bool
    is_closed: bool = None

class ValidationResult:
    is_valid: bool
    is_closed_solid: bool = None
    has_self_intersections: bool = None
    errors: List[str] = []

class IntersectionResult:
    intersects: bool
    intersection_curves: List[str] = []
    intersection_points: List[Point3d] = []
```

## RhinoMCP Integration

### Installation

```bash
# In Rhino Package Manager
# Search for "rhinomcp" and install

# Or manual install:
# 1. Build plugin in Release mode
# 2. Copy manifest.yml to bin/Release
# 3. yak build
# 4. yak push rhino_mcp_plugin_xxxx.yak
```

### Configuration (Claude Desktop / MCP Client)

```json
{
  "mcpServers": {
    "rhino": {
      "command": "uvx",
      "args": ["--from", "rhinomcp==0.4.1.1", "rhinomcp"]
    }
  }
}
```

### Environment Variables

```bash
# Security flags (set to 0 to disable dangerous tools)
RHINO_MCP_ENABLE_RUN_COMMAND=1
RHINO_MCP_ENABLE_RHINOSCRIPT=1
RHINO_MCP_ENABLE_CSHARP=1

# Server
RHINO_MCP_HOST=127.0.0.1
RHINO_MCP_PORT=1999
```

## Geometry Creation Patterns

### Basic Geometry

```csharp
// Point
Point3d pt = new Point3d(0, 0, 0);
doc.Objects.AddPoint(pt);

// Line
Line line = new Line(new Point3d(0,0,0), new Point3d(10,0,0));
doc.Objects.AddLine(line);

// Rectangle
Plane plane = Plane.WorldXY;
Rectangle3d rect = new Rectangle3d(plane, new Interval(0, 10), new Interval(0, 5));
doc.Objects.AddPolyline(rect.ToPolyline());

// Circle
Circle circle = new Circle(Plane.WorldXY, 5.0);
doc.Objects.AddCircle(circle);
```

### Architecture Elements

```csharp
// Wall from curve
Curve baseline = ...;
double height = 3000; // mm
double thickness = 200; // mm

// Extrude curve to create wall solid
Vector3d extrusionDir = new Vector3d(0, 0, height);
Brep wall = Brep.CreateFromSurface(
    Extrusion.Create(baseline, height, true).ToBrep(), 
    true
)[0];

// Cap the extrusion
wall.CapPlanarHoles(doc.ModelAbsoluteTolerance);
doc.Objects.AddBrep(wall);

// Door in wall
// Boolean difference with door opening
```

### Boolean Operations

```csharp
// Union
Brep[] result = Brep.CreateBooleanUnion(breps, tolerance);

// Difference
Brep[] result = Brep.CreateBooleanDifference(brepA, brepB, tolerance);

// Intersection
Brep[] result = Brep.CreateBooleanIntersection(brepA, brepB, tolerance);
```

### Validation

```csharp
// Check if Brep is valid
bool isValid = brep.IsValid;

// Check if solid
bool isSolid = brep.IsSolid;

// Check for self-intersections
bool hasSelfIntersections = brep.SelfIntersection(tolerance, out _, out _);

// Check dimensions
BoundingBox bbox = brep.GetBoundingBox(true);
double width = bbox.Max.X - bbox.Min.X;
```

## Grasshopper Integration

### GH Document Access

```csharp
// Get active GH document
GH_Document ghDoc = Grasshopper.Instances.ActiveCanvas.Document;

// Find component by name
IGH_DocumentObject obj = ghDoc.FindComponent("component_name");

// Create component
IGH_Component component = GH_ComponentServer.LoadComponent(guid);
ghDoc.AddObject(component, false, new PointF(100, 100));

// Set parameter
IGH_Param param = component.Params.Input[0];
param.SetPersistentData(new GH_Number(5.0));

// Connect wires
ghDoc.ConnectWires(source.Params.Output[0], target.Params.Input[0]);

// Solve
ghDoc.NewSolution(false);

// Bake
component.BakeGeometry(doc, new List<Guid>(), new ObjectAttributes());
```

## Thread Safety

**Critical**: RhinoCommon is NOT thread-safe for document modifications.

All document operations MUST run on the UI thread:

```csharp
// In plugin (RhinoMCPServer.cs)
RhinoApp.InvokeOnUiThread(() => {
    // Document modifications here
    doc.Objects.AddBrep(brep);
    doc.Views.Redraw();
});
```

## Unit Handling

```csharp
// Get document units
UnitSystem units = doc.ModelUnitSystem;

// Convert between units
double meters = RhinoMath.UnitScale(UnitSystem.Meters, UnitSystem.Millimeters);
// 1 meter = 1000 millimeters

// User input: "5m" → parse → convert to document units
double userValue = 5.0; // meters
double rhinoValue = userValue * RhinoMath.UnitScale(UnitSystem.Meters, doc.ModelUnitSystem);
```

## Error Handling

```csharp
try {
    // Rhino operation
    Result result = RunCommand(doc, mode);
    return result;
} catch (Exception ex) {
    RhinoApp.WriteLine($"Error: {ex.Message}");
    return Result.Failure;
}
```

## Performance Considerations

1. **Batch operations**: Use `create_objects` instead of multiple `create_object`
2. **Minimize UI thread calls**: Batch geometry creation
3. **Use Extrusion for simple extrusions**: Lighter than Brep
4. **Disable redraw during batch**: `doc.Views.EnableRedraw(false)` / `doc.Views.EnableRedraw(true)`
5. **Object caching**: Reuse geometry where possible

## Testing

### Live Rhino Tests

```csharp
// In test project
[Test]
public void TestCreateWall() {
    var doc = RhinoDoc.ActiveDoc;
    var baseline = new LineCurve(new Point3d(0,0,0), new Point3d(5000,0,0));
    var wall = CreateWall(baseline, 3000, 200);
    
    Assert.IsNotNull(wall);
    Assert.IsTrue(wall.IsSolid);
    Assert.AreEqual(5000 * 3000 * 200, wall.GetVolume(), 1.0); // mm³
}
```

### Simulator Mode

For CI/testing without Rhino:
- Use `rhino3dm` (Python/.NET) for geometry operations
- Mock MCP server responses
- Validate geometry mathematically