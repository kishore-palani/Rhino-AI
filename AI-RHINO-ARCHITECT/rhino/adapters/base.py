"""Interfaces for Rhino and Grasshopper execution adapters."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class RhinoAdapter(ABC):
    """Port used by orchestration code to execute model operations."""

    @abstractmethod
    async def call_tool(self, name: str, arguments: dict[str, Any]) -> Any:
        """Execute a named Rhino or Grasshopper tool."""
        raise NotImplementedError

    @abstractmethod
    async def close(self) -> None:
        """Release transport resources."""
        raise NotImplementedError
