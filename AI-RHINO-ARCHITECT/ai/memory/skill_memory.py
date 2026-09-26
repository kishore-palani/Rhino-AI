"""
Skill execution memory module for AI RHINO ARCHITECT.

Tracks, records, and analyzes the execution of modeling skills with full
context (parameters, preconditions, execution time, created geometry, success/failure).
Provides statistical insights such as success rate and valid parameter ranges.
"""

from __future__ import annotations

import logging
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from ai.memory.agentmemory_client import AgentMemoryClient, get_client

logger = logging.getLogger(__name__)


@dataclass
class SkillExecution:
    """Represents a single execution record of a modeling skill."""

    skill_id: str
    parameters: Dict[str, Any]
    success: bool
    execution_time_ms: float = 0.0
    preconditions: Dict[str, Any] = field(default_factory=dict)
    geometry_ids: List[str] = field(default_factory=list)
    validation_issues: List[str] = field(default_factory=list)
    error: Optional[str] = None
    plan_context: Optional[str] = None
    timestamp: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class SkillMemory:
    """Manages recording and querying skill execution history."""

    def __init__(self, client: Optional[AgentMemoryClient] = None) -> None:
        self.client = client or get_client()
        self._local_history: List[SkillExecution] = []

    def record_execution(self, execution: SkillExecution) -> Dict[str, Any]:
        """Record a skill execution both in-memory and to AgentMemory."""
        self._local_history.append(execution)

        content = (
            f"Skill: {execution.skill_id} | Success: {execution.success} | "
            f"Params: {execution.parameters} | Time: {execution.execution_time_ms:.1f}ms"
        )
        if execution.error:
            content += f" | Error: {execution.error}"
        if execution.geometry_ids:
            content += f" | Geometries: {len(execution.geometry_ids)}"

        concepts = [
            "skill-execution",
            execution.skill_id,
            "success" if execution.success else "failure",
        ]

        try:
            return self.client.remember(
                content=content,
                memory_type="skill_execution",
                project="ai-rhino-architect",
                concepts=concepts,
            )
        except Exception as exc:
            logger.warning("Failed to persist skill execution to agentmemory: %s", exc)
            return {"success": False, "error": str(exc)}

    def get_executions(
        self, skill_id: Optional[str] = None, success_only: Optional[bool] = None
    ) -> List[SkillExecution]:
        """Retrieve recorded executions matching filters."""
        results = self._local_history
        if skill_id is not None:
            results = [e for e in results if e.skill_id == skill_id]
        if success_only is not None:
            results = [e for e in results if e.success == success_only]
        return results

    def get_success_rate(self, skill_id: str) -> float:
        """Calculate success rate for a specific skill (0.0 to 1.0)."""
        executions = [e for e in self._local_history if e.skill_id == skill_id]
        if not executions:
            return 1.0  # optimistic default if never executed
        successes = sum(1 for e in executions if e.success)
        return successes / len(executions)

    def get_parameter_ranges(
        self, skill_id: str, param_name: str
    ) -> Dict[str, Any]:
        """Analyze parameter distributions for successful vs failed executions."""
        successful_values: List[float] = []
        failed_values: List[float] = []

        for e in self._local_history:
            if e.skill_id != skill_id or param_name not in e.parameters:
                continue
            val = e.parameters[param_name]
            if isinstance(val, (int, float)):
                if e.success:
                    successful_values.append(float(val))
                else:
                    failed_values.append(float(val))

        return {
            "skill_id": skill_id,
            "parameter": param_name,
            "total_samples": len(successful_values) + len(failed_values),
            "successful_range": (
                (min(successful_values), max(successful_values))
                if successful_values
                else None
            ),
            "failed_range": (
                (min(failed_values), max(failed_values))
                if failed_values
                else None
            ),
            "successful_values": successful_values,
            "failed_values": failed_values,
        }

    def query_similar(
        self, skill_id: str, parameters: Dict[str, Any], limit: int = 5
    ) -> List[SkillExecution]:
        """Find executions of the same skill with similar parameters."""
        candidates = [e for e in self._local_history if e.skill_id == skill_id]
        # Sort by parameter match overlap
        def match_score(exec_rec: SkillExecution) -> int:
            score = 0
            for k, v in parameters.items():
                if k in exec_rec.parameters and exec_rec.parameters[k] == v:
                    score += 2
                elif k in exec_rec.parameters:
                    score += 1
            return score

        candidates.sort(key=match_score, reverse=True)
        return candidates[:limit]

    def clear(self) -> None:
        """Clear local in-memory history."""
        self._local_history.clear()


# Module-level singleton
_skill_memory: Optional[SkillMemory] = None


def get_skill_memory() -> SkillMemory:
    """Return shared process-wide SkillMemory instance."""
    global _skill_memory
    if _skill_memory is None:
        _skill_memory = SkillMemory()
    return _skill_memory
