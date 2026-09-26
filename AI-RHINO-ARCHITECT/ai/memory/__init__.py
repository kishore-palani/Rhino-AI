"""Memory subsystem for AI RHINO ARCHITECT.

Exposes the AgentMemory REST client and project-level memory helpers.
"""

from ai.memory.agentmemory_client import (
    AgentMemoryClient,
    get_client,
    remember,
    recall,
)
from ai.memory.project_memory import ProjectMemory, get_project_memory

__all__ = [
    "AgentMemoryClient",
    "ProjectMemory",
    "get_client",
    "get_project_memory",
    "remember",
    "recall",
]