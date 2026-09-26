"""
Failure pattern recognition module for AI RHINO ARCHITECT.

Detects recurring failures across geometric, dimensional, regulatory, and MCP domains.
Maintains pattern clusters and provides actionable suggestions to the planner.
"""

from __future__ import annotations

import logging
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from ai.memory.agentmemory_client import AgentMemoryClient, get_client

logger = logging.getLogger(__name__)


@dataclass
class FailurePattern:
    """Represents a recognized recurring failure mode."""

    pattern_id: str
    failure_type: str  # "geometry", "dimensional", "regulatory", "mcp", "skill"
    description: str
    occurrences: int = 1
    common_attributes: Dict[str, Any] = field(default_factory=dict)
    suggested_fix: Optional[str] = None
    confidence: float = 0.5
    first_seen: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    last_seen: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class FailurePatternRecognizer:
    """Analyzes failures and groups them into identifiable patterns."""

    def __init__(self, client: Optional[AgentMemoryClient] = None) -> None:
        self.client = client or get_client()
        self._patterns: Dict[str, FailurePattern] = {}
        self._raw_failures: List[Dict[str, Any]] = []

    def record_failure(
        self,
        task: str,
        error: str,
        failure_type: str = "general",
        context: Optional[Dict[str, Any]] = None,
        suggested_fix: Optional[str] = None,
    ) -> FailurePattern:
        """Ingest a failure record, update or create pattern cluster, and persist."""
        ctx = context or {}
        failure_entry = {
            "task": task,
            "error": error,
            "type": failure_type,
            "context": ctx,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        self._raw_failures.append(failure_entry)

        # Derive pattern key
        pattern_id = self._generate_pattern_id(task, failure_type, error, ctx)

        if pattern_id in self._patterns:
            pattern = self._patterns[pattern_id]
            pattern.occurrences += 1
            pattern.last_seen = failure_entry["timestamp"]
            pattern.confidence = min(0.99, pattern.confidence + 0.1)
            if suggested_fix and not pattern.suggested_fix:
                pattern.suggested_fix = suggested_fix
        else:
            fix = suggested_fix or self._deduce_fix(failure_type, error, ctx)
            pattern = FailurePattern(
                pattern_id=pattern_id,
                failure_type=failure_type,
                description=f"{failure_type.capitalize()} failure in {task}: {error}",
                occurrences=1,
                common_attributes={"task": task, "type": failure_type, **ctx},
                suggested_fix=fix,
                confidence=0.5,
            )
            self._patterns[pattern_id] = pattern

        # Persist pattern to AgentMemory if occurrences reach threshold
        if pattern.occurrences >= 2:
            self._persist_pattern(pattern)

        return pattern

    def _generate_pattern_id(
        self, task: str, failure_type: str, error: str, context: Dict[str, Any]
    ) -> str:
        """Create a normalized pattern signature."""
        normalized_error = error.lower()
        if "dimension" in normalized_error or "height" in normalized_error or "thickness" in normalized_error:
            key = f"dim_{task}_{failure_type}"
        elif "manifold" in normalized_error or "solid" in normalized_error or "brep" in normalized_error:
            key = f"geom_{task}_{failure_type}"
        elif "mcp" in normalized_error or "connect" in normalized_error or "slot" in normalized_error:
            key = f"mcp_{failure_type}"
        else:
            key = f"{failure_type}_{task}"
        return key.replace(" ", "_").lower()

    def _deduce_fix(
        self, failure_type: str, error: str, context: Dict[str, Any]
    ) -> Optional[str]:
        """Automatically deduce common corrective actions based on domain heuristics."""
        err = error.lower()
        if "wall" in err and ("thickness" in err or "thin" in err):
            return "Ensure wall thickness is at least 150mm (residential) or 200mm (structural)."
        if "height" in err and "clearance" in err:
            return "Ensure minimum ceiling clearance is at least 2400mm."
        if "open" in err or "naked" in err or "solid" in err:
            return "Ensure boundary curves are closed and planar before extrusion."
        if "mcp" in err or "slot" in err:
            return "Ensure a fresh Rhino slot is spawned and target with correct 'slot' parameter."
        return None

    def _persist_pattern(self, pattern: FailurePattern) -> None:
        """Save recurring pattern as a project lesson in AgentMemory."""
        try:
            self.client.save_lesson(
                task=pattern.common_attributes.get("task", "general"),
                lesson=f"Recurring Pattern [{pattern.failure_type}]: {pattern.description}. Suggested fix: {pattern.suggested_fix}",
                category=pattern.failure_type,
                strength=min(10, pattern.occurrences + 4),
            )
        except Exception as exc:
            logger.warning("Failed to persist pattern lesson: %s", exc)

    def get_patterns(
        self, failure_type: Optional[str] = None, min_occurrences: int = 1
    ) -> List[FailurePattern]:
        """Retrieve recognized patterns filtered by type and frequency."""
        patterns = list(self._patterns.values())
        if failure_type:
            patterns = [p for p in patterns if p.failure_type == failure_type]
        return [p for p in patterns if p.occurrences >= min_occurrences]

    def suggest_correction_for(
        self, task: str, failure_type: str, error: str
    ) -> Optional[str]:
        """Lookup suggested correction for a given failure context."""
        pattern_id = self._generate_pattern_id(task, failure_type, error, {})
        if pattern_id in self._patterns and self._patterns[pattern_id].suggested_fix:
            return self._patterns[pattern_id].suggested_fix
        # Fallback to general type match
        for p in self._patterns.values():
            if p.failure_type == failure_type and p.suggested_fix:
                return p.suggested_fix
        return None

    def clear(self) -> None:
        """Clear local patterns cache."""
        self._patterns.clear()
        self._raw_failures.clear()


# Module-level singleton
_pattern_recognizer: Optional[FailurePatternRecognizer] = None


def get_failure_pattern_recognizer() -> FailurePatternRecognizer:
    """Return shared process-wide FailurePatternRecognizer instance."""
    global _pattern_recognizer
    if _pattern_recognizer is None:
        _pattern_recognizer = FailurePatternRecognizer()
    return _pattern_recognizer
