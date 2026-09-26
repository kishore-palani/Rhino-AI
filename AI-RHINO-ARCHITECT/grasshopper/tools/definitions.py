"""Stable tool definitions exposed to the orchestration layer."""


GRASSHOPPER_TOOLS: tuple[dict[str, object], ...] = (
    {
        "name": "grasshopper.solve",
        "description": "Solve the active Grasshopper definition.",
        "inputSchema": {"type": "object", "properties": {}, "additionalProperties": False},
    },
    {
        "name": "grasshopper.set_input",
        "description": "Set a named Grasshopper input before solving.",
        "inputSchema": {
            "type": "object",
            "required": ["name", "value"],
            "properties": {"name": {"type": "string"}, "value": {}},
            "additionalProperties": False,
        },
    },
)
