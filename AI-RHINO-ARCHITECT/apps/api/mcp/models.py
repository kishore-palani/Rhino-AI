"""Pydantic models for JSON-RPC 2.0 and MCP protocol messages.

These models describe every wire-format message exchanged between this client
and an MCP-compatible server (such as ``rhinomcp``).  They are used both for
serialising outgoing requests and for deserialising / validating incoming
responses.
"""

from __future__ import annotations

from typing import Any, Dict, List, Literal, Optional, Union

from pydantic import BaseModel, ConfigDict, Field

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

JSONRPC_VERSION: str = "2.0"
MCP_PROTOCOL_VERSION: str = "2024-11-05"
MCP_SERVER_NAME: str = "RhinoMCP"
MCP_SERVER_VERSION: str = "0.1.0"

# Standard JSON-RPC 2.0 error codes
PARSE_ERROR: int = -32700
INVALID_REQUEST: int = -32600
METHOD_NOT_FOUND: int = -32601
INVALID_PARAMS: int = -32602
INTERNAL_ERROR: int = -32603
SERVER_ERROR_MIN: int = -32000
SERVER_ERROR_MAX: int = -32099

# MCP-defined server error codes (in the -32000 reserve)
SERVER_NOT_INITIALIZED: int = -32000
AUTHENTICATION_FAILED: int = -32001
PERMISSION_DENIED: int = -32002
RESOURCE_NOT_FOUND: int = -32003
RATE_LIMITED: int = -32004


# ---------------------------------------------------------------------------
# JSON-RPC 2.0 base types
# ---------------------------------------------------------------------------


class JSONRPCRequest(BaseModel):
    """A JSON-RPC 2.0 request expecting a response."""

    model_config = ConfigDict(extra="allow")

    jsonrpc: str = Field(default=JSONRPC_VERSION)
    id: Optional[Union[int, str]] = Field(default=None)
    method: str
    params: Optional[Union[Dict[str, Any], List[Any]]] = None


class JSONRPCNotification(BaseModel):
    """A JSON-RPC 2.0 notification (no response expected)."""

    model_config = ConfigDict(extra="allow")

    jsonrpc: str = Field(default=JSONRPC_VERSION)
    method: str
    params: Optional[Union[Dict[str, Any], List[Any]]] = None


class JSONRPCErrorObject(BaseModel):
    """The error sub-object of a JSON-RPC 2.0 error response."""

    model_config = ConfigDict(extra="allow")

    code: int
    message: str
    data: Optional[Any] = None


class JSONRPCSuccessResponse(BaseModel):
    """A JSON-RPC 2.0 success response."""

    model_config = ConfigDict(extra="allow")

    jsonrpc: str = Field(default=JSONRPC_VERSION)
    id: Optional[Union[int, str]] = None
    result: Any = None


class JSONRPCErrorResponse(BaseModel):
    """A JSON-RPC 2.0 error response."""

    model_config = ConfigDict(extra="allow")

    jsonrpc: str = Field(default=JSONRPC_VERSION)
    id: Optional[Union[int, str]] = None
    error: JSONRPCErrorObject


JSONRPCResponse = Union[JSONRPCSuccessResponse, JSONRPCErrorResponse]


# ---------------------------------------------------------------------------
# MCP capability models
# ---------------------------------------------------------------------------


class ToolAnnotations(BaseModel):
    """Hints about a tool's behaviour, per the MCP specification."""

    model_config = ConfigDict(extra="allow")

    title: Optional[str] = None
    read_only_hint: Optional[bool] = Field(default=None, alias="readOnlyHint")
    destructive_hint: Optional[bool] = Field(default=None, alias="destructiveHint")
    idempotent_hint: Optional[bool] = Field(default=None, alias="idempotentHint")
    open_world_hint: Optional[bool] = Field(default=None, alias="openWorldHint")


class Tool(BaseModel):
    """A tool definition returned by ``tools/list``."""

    model_config = ConfigDict(extra="allow")

    name: str
    description: Optional[str] = None
    inputSchema: Dict[str, Any] = Field(default_factory=lambda: {"type": "object"})
    outputSchema: Optional[Dict[str, Any]] = None
    annotations: Optional[ToolAnnotations] = None
    title: Optional[str] = Field(default=None, description="Optional display title")


class ToolListResult(BaseModel):
    """Result of a ``tools/list`` request."""

    model_config = ConfigDict(extra="allow")

    tools: List[Tool] = Field(default_factory=list)
    nextCursor: Optional[str] = None


class ListToolsRequestParams(BaseModel):
    """Parameters for ``tools/list``."""

    model_config = ConfigDict(extra="allow")

    cursor: Optional[str] = None


class CallToolRequestParams(BaseModel):
    """Parameters for ``tools/call``."""

    model_config = ConfigDict(extra="allow")

    name: str
    arguments: Optional[Dict[str, Any]] = None


class TextContent(BaseModel):
    """A text content item in a tool-call result."""

    model_config = ConfigDict(extra="allow")

    type: Literal["text"] = "text"
    text: str
    annotation: Optional[Dict[str, Any]] = None


class ImageContent(BaseModel):
    """An image content item in a tool-call result."""

    model_config = ConfigDict(extra="allow")

    type: Literal["image"] = "image"
    data: str
    mimeType: str
    annotation: Optional[Dict[str, Any]] = None


class ResourceContent(BaseModel):
    """A resource content item embedded in a tool-call result."""

    model_config = ConfigDict(extra="allow")

    type: Literal["resource"] = "resource"
    resource: Dict[str, Any]
    annotation: Optional[Dict[str, Any]] = None


ContentItem = Union[TextContent, ImageContent, ResourceContent]


class CallToolResult(BaseModel):
    """Result of a ``tools/call`` request."""

    model_config = ConfigDict(extra="allow")

    content: List[ContentItem] = Field(default_factory=list)
    structuredContent: Optional[Dict[str, Any]] = None
    isError: bool = Field(default=False, alias="isError")

    @property
    def text(self) -> str:
        """Concatenate all text content items into a single string."""
        return "\n".join(
            item.text for item in self.content if isinstance(item, TextContent)
        )

    @property
    def success(self) -> bool:
        """Whether the tool call reported success (no error flag)."""
        return not self.isError


# ---------------------------------------------------------------------------
# MCP initialisation models
# ---------------------------------------------------------------------------


class ClientCapabilities(BaseModel):
    """Capabilities the client supports."""

    model_config = ConfigDict(extra="allow")

    roots: Optional[Dict[str, Any]] = None
    sampling: Optional[Dict[str, Any]] = None
    elicitation: Optional[Dict[str, Any]] = None


class ServerCapabilities(BaseModel):
    """Capabilities the server supports."""

    model_config = ConfigDict(extra="allow")

    tools: Optional[Dict[str, Any]] = None
    prompts: Optional[Dict[str, Any]] = None
    resources: Optional[Dict[str, Any]] = None
    logging: Optional[Dict[str, Any]] = None


class InitializeRequestParams(BaseModel):
    """Parameters for the ``initialize`` MCP request."""

    model_config = ConfigDict(extra="allow")

    protocolVersion: str = MCP_PROTOCOL_VERSION
    capabilities: ClientCapabilities = Field(default_factory=ClientCapabilities)
    clientInfo: Dict[str, str] = Field(
        default_factory=lambda: {"name": "RhinoMCPClient", "version": MCP_SERVER_VERSION}
    )


class ServerInfo(BaseModel):
    """Server identity returned by ``initialize``."""

    model_config = ConfigDict(extra="allow")

    name: str
    version: str


class InitializeResult(BaseModel):
    """Result of the ``initialize`` MCP request."""

    model_config = ConfigDict(extra="allow")

    protocolVersion: str
    capabilities: ServerCapabilities
    serverInfo: ServerInfo
    instructions: Optional[str] = None


# ---------------------------------------------------------------------------
# MCP resource / prompt models
# ---------------------------------------------------------------------------


class McpResource(BaseModel):
    """A resource descriptor returned by ``resources/list``."""

    model_config = ConfigDict(extra="allow")

    uri: str
    name: str
    description: Optional[str] = None
    mimeType: Optional[str] = None


class ResourceListResult(BaseModel):
    """Result of ``resources/list``."""

    model_config = ConfigDict(extra="allow")

    resources: List[McpResource] = Field(default_factory=list)
    nextCursor: Optional[str] = None


class ReadResourceResult(BaseModel):
    """Result of ``resources/read``."""

    model_config = ConfigDict(extra="allow")

    contents: List[Dict[str, Any]] = Field(default_factory=list)


class PromptArgument(BaseModel):
    """A prompt argument declaration."""

    model_config = ConfigDict(extra="allow")

    name: str
    description: Optional[str] = None
    required: bool = False


class Prompt(BaseModel):
    """A prompt declaration returned by ``prompts/list``."""

    model_config = ConfigDict(extra="allow")

    name: str
    description: Optional[str] = None
    arguments: Optional[List[PromptArgument]] = None


class PromptListResult(BaseModel):
    """Result of ``prompts/list``."""

    model_config = ConfigDict(extra="allow")

    prompts: List[Prompt] = Field(default_factory=list)
    nextCursor: Optional[str] = None


# ---------------------------------------------------------------------------
# MCP logging model
# ---------------------------------------------------------------------------


class LogMessage(BaseModel):
    """A log message notification from the server."""

    model_config = ConfigDict(extra="allow")

    level: str
    message: str
    data: Optional[Dict[str, Any]] = None


# ---------------------------------------------------------------------------
# Rhino-specific data models
# ---------------------------------------------------------------------------


class Point3d(BaseModel):
    """A 3D point in Rhino world coordinates."""

    x: float = 0.0
    y: float = 0.0
    z: float = 0.0


class Vector3d(BaseModel):
    """A 3D vector."""

    x: float = 0.0
    y: float = 0.0
    z: float = 0.0


class ColorRGB(BaseModel):
    """An RGB colour."""

    r: int = Field(ge=0, le=255)
    g: int = Field(ge=0, le=255)
    b: int = Field(ge=0, le=255)


class BoundingBox(BaseModel):
    """Axis-aligned bounding box: [min_corner, max_corner]."""

    model_config = ConfigDict(extra="allow")

    min: Optional[Point3d] = None
    max: Optional[Point3d] = None


class RhinoObject(BaseModel):
    """Lightweight representation of a Rhino document object."""

    model_config = ConfigDict(extra="allow")

    id: str
    name: Optional[str] = None
    type: Optional[str] = None
    layer: Optional[str] = None
    material: Optional[str] = None
    color: Optional[ColorRGB] = None
    bounding_box: Optional[BoundingBox] = None
    geometry: Optional[Dict[str, Any]] = None
    attributes: Optional[Dict[str, Any]] = None


class LayerInfo(BaseModel):
    """A Rhino layer record."""

    model_config = ConfigDict(extra="allow")

    id: Optional[str] = None
    name: str
    full_path: Optional[str] = None
    color: Optional[ColorRGB] = None
    parent: Optional[str] = None
    object_count: Optional[int] = None
    visible: Optional[bool] = None
    locked: Optional[bool] = None


class ObjectMetrics(BaseModel):
    """Type-specific measurements returned by ``analyze_objects``."""

    model_config = ConfigDict(extra="allow")

    length: Optional[float] = None
    area: Optional[float] = None
    volume: Optional[float] = None
    centroid: Optional[Point3d] = None
    is_closed: Optional[bool] = None
    start_point: Optional[Point3d] = None
    end_point: Optional[Point3d] = None
    faces: Optional[int] = None
    edges: Optional[int] = None
    vertices: Optional[int] = None
    naked_edge_count: Optional[int] = None


class AnalysisReport(BaseModel):
    """A single object entry in an ``analyze_objects`` response."""

    model_config = ConfigDict(extra="allow")

    id: str
    name: Optional[str] = None
    type: Optional[str] = None
    layer: Optional[str] = None
    valid: bool = True
    validity_log: Optional[str] = None
    bounding_box: Optional[List[List[float]]] = None
    bbox_dimensions: Optional[List[float]] = None
    metrics: Optional[ObjectMetrics] = None


class AnalysisResult(BaseModel):
    """Full ``analyze_objects`` response body."""

    model_config = ConfigDict(extra="allow")

    object_count: int = 0
    analyses: List[AnalysisReport] = Field(default_factory=list)


class SectionLoop(BaseModel):
    """A single loop in a section profile result."""

    model_config = ConfigDict(extra="allow")

    closed: bool
    perimeter: Optional[float] = None
    area: Optional[float] = None
    centroid: Optional[List[float]] = None
    is_hole: bool = False


class SectionProfile(BaseModel):
    """Per-object profile in a ``section_profile`` result."""

    model_config = ConfigDict(extra="allow")

    id: str
    name: Optional[str] = None
    type: Optional[str] = None
    section_area: Optional[float] = None
    loop_count: Optional[int] = None
    loops: List[SectionLoop] = Field(default_factory=list)


class MeasureResult(BaseModel):
    """Response from ``measure_objects``."""

    model_config = ConfigDict(extra="allow")

    object_a: str
    object_b: str
    clash: bool = False
    intersection_count: int = 0
    bbox_gap: Optional[float] = None
    method: Optional[str] = None


class BooleanResult(BaseModel):
    """Response from a boolean operation."""

    model_config = ConfigDict(extra="allow")

    result_ids: Optional[List[str]] = None
    count: int = 0
    message: str = ""
    dry_run: bool = False
    would_succeed: Optional[bool] = None
    results: Optional[List[Dict[str, Any]]] = None


class LayerResult(BaseModel):
    """Response from ``create_layer``."""

    model_config = ConfigDict(extra="allow")

    name: str
    id: Optional[str] = None
    message: str = ""


class SelectResult(BaseModel):
    """Response from ``select_objects``."""

    model_config = ConfigDict(extra="allow")

    count: int = 0


class DeleteResult(BaseModel):
    """Response from ``delete_object``."""

    model_config = ConfigDict(extra="allow")

    id: Optional[str] = None
    name: Optional[str] = None
    deleted: bool = True
    count: Optional[int] = None


class ScriptExecutionResult(BaseModel):
    """Response from ``execute_rhinoscript_python_code`` or ``execute_rhinocommon_csharp_code``."""

    model_config = ConfigDict(extra="allow")

    success: bool = True
    output: Optional[str] = None
    message: Optional[str] = None


class CommandInfo(BaseModel):
    """A Rhino command entry from ``get_commands``."""

    model_config = ConfigDict(extra="allow")

    name: str


class CommandsResult(BaseModel):
    """Response from ``get_commands``."""

    model_config = ConfigDict(extra="allow")

    count: int = 0
    commands: List[str] = Field(default_factory=list)


class CapabilityCommand(BaseModel):
    """A single command entry in ``describe_capabilities``."""

    model_config = ConfigDict(extra="allow")

    name: str
    read_only: bool = False
    supports_dry_run: Optional[bool] = None


class EnvelopeFlag(BaseModel):
    """An opt-in envelope flag reported by ``describe_capabilities``."""

    model_config = ConfigDict(extra="allow")

    flag: str
    attaches: str
    description: str


class PerceptionInfo(BaseModel):
    """Perception metadata reported by ``describe_capabilities``."""

    model_config = ConfigDict(extra="allow")

    description: str
    envelope_flags: List[EnvelopeFlag] = Field(default_factory=list)


class CapabilitiesInfo(BaseModel):
    """Response from ``describe_capabilities``."""

    model_config = ConfigDict(extra="allow")

    version: str
    command_count: int
    commands: List[CapabilityCommand]
    perception: PerceptionInfo
    server_version: Optional[str] = None
    plugin_matches_server: Optional[bool] = None
    update_advice: Optional[str] = None


class DocumentMetadata(BaseModel):
    """Document-level metadata from ``get_document_summary``."""

    model_config = ConfigDict(extra="allow")

    name: Optional[str] = None
    units: Optional[str] = None
    tolerance: Optional[float] = None
    abs_tolerance: Optional[float] = None
    angle_tolerance: Optional[float] = None
    created: Optional[str] = None
    modified: Optional[str] = None


class DocumentSummary(BaseModel):
    """Response from ``get_document_summary``."""

    model_config = ConfigDict(extra="allow")

    metadata: Optional[DocumentMetadata] = None
    total_object_count: int = 0
    object_type_counts: Dict[str, int] = Field(default_factory=dict)
    object_layer_counts: Dict[str, int] = Field(default_factory=dict)
    model_bounding_box: Optional[List[List[float]]] = None
    layers: List[LayerInfo] = Field(default_factory=list)


class ViewportSpec(BaseModel):
    """Parameters for ``capture_viewport``."""

    model_config = ConfigDict(extra="allow")

    viewport: str = "active"
    width: int = 800
    height: int = 600
    show_grid: bool = True
    show_axes: bool = True
    show_cplane_axes: bool = False
    zoom_to_fit: bool = False


class GrasshopperComponentInfo(BaseModel):
    """A Grasshopper component type descriptor."""

    model_config = ConfigDict(extra="allow")

    guid: Optional[str] = None
    name: str
    nickname: Optional[str] = None
    description: Optional[str] = None
    category: Optional[str] = None
    subcategory: Optional[str] = None
    exposure: Optional[str] = None
    inputs: List[Dict[str, Any]] = Field(default_factory=list)
    outputs: List[Dict[str, Any]] = Field(default_factory=list)


class ModelingGuidance(BaseModel):
    """Response from ``get_modeling_guidance``."""

    model_config = ConfigDict(extra="allow")

    topic: str
    content: str


# ---------------------------------------------------------------------------
# High-level convenience wrappers
# ---------------------------------------------------------------------------


class ToolCallResponse(BaseModel):
    """Structured wrapper around a ``tools/call`` result.

    Attributes:
        success: Whether the call succeeded.
        tool_name: The name of the tool that was called.
        content: Raw text content from the response.
        structured_content: Parsed structured result if the server provided it.
        is_error: Whether the server flagged this as an error.
    """

    model_config = ConfigDict(extra="allow")

    success: bool = True
    tool_name: str = ""
    content: str = ""
    structured_content: Optional[Dict[str, Any]] = None
    is_error: bool = False
    error_message: Optional[str] = None
    raw_result: Optional[Dict[str, Any]] = None