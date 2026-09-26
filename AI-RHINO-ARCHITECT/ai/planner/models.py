"""Planner models for AI RHINO ARCHITECT.

Defines the plan structure, step definitions, and execution state.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class PlanStatus(str, Enum):
    """Status of a plan during its lifecycle."""

    PENDING = "pending"
    VALIDATING = "validating"
    VALID = "valid"
    INVALID = "invalid"
    EXECUTING = "executing"
    COMPLETED = "completed"
    FAILED = "failed"
    ROLLED_BACK = "rolled_back"


class StepStatus(str, Enum):
    """Status of an individual plan step."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"
    ROLLED_BACK = "rolled_back"


class StepType(str, Enum):
    """Type of plan step."""

    SKILL = "skill"           # Execute a modeling skill
    VALIDATION = "validation" # Run validation checks
    CONDITIONAL = "conditional"  # Conditional branch
    LOOP = "loop"             # Loop over items
    PARALLEL = "parallel"     # Parallel execution group


@dataclass
class PlanStep:
    """A single step in an execution plan."""

    step_id: str
    step_type: StepType = StepType.SKILL
    skill_id: str | None = None
    inputs: dict[str, Any] = field(default_factory=dict)
    depends_on: list[str] = field(default_factory=list)  # Step IDs this step depends on
    condition: str | None = None  # For conditional steps
    loop_over: str | None = None  # For loop steps
    parallel_steps: list["PlanStep"] = field(default_factory=list)  # For parallel steps
    description: str = ""
    status: StepStatus = StepStatus.PENDING
    result: dict[str, Any] | None = None
    error: str | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None
    rollback_data: dict[str, Any] | None = None  # Data needed for rollback

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "step_id": self.step_id,
            "step_type": self.step_type.value,
            "skill_id": self.skill_id,
            "inputs": self.inputs,
            "depends_on": self.depends_on,
            "condition": self.condition,
            "loop_over": self.loop_over,
            "parallel_steps": [s.to_dict() for s in self.parallel_steps],
            "description": self.description,
            "status": self.status.value,
            "result": self.result,
            "error": self.error,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "rollback_data": self.rollback_data,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "PlanStep":
        """Create from dictionary."""
        step = cls(
            step_id=data["step_id"],
            step_type=StepType(data.get("step_type", "skill")),
            skill_id=data.get("skill_id"),
            inputs=data.get("inputs", {}),
            depends_on=data.get("depends_on", []),
            condition=data.get("condition"),
            loop_over=data.get("loop_over"),
            description=data.get("description", ""),
            status=StepStatus(data.get("status", "pending")),
            result=data.get("result"),
            error=data.get("error"),
            rollback_data=data.get("rollback_data"),
        )
        if data.get("started_at"):
            step.started_at = datetime.fromisoformat(data["started_at"])
        if data.get("completed_at"):
            step.completed_at = datetime.fromisoformat(data["completed_at"])
        if data.get("parallel_steps"):
            step.parallel_steps = [cls.from_dict(s) for s in data["parallel_steps"]]
        return step


class Plan(BaseModel):
    """Complete execution plan with metadata."""

    plan_id: str = Field(..., description="Unique plan identifier")
    name: str = Field(..., description="Human-readable plan name")
    description: str = Field(default="", description="Plan description")
    goal: str = Field(..., description="Natural language goal that generated this plan")
    steps: list[PlanStep] = Field(default_factory=list, description="Ordered plan steps")
    status: PlanStatus = PlanStatus.PENDING
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    started_at: datetime | None = None
    completed_at: datetime | None = None
    context: dict[str, Any] = Field(default_factory=dict, description="Execution context (variables, refs, etc.)")
    metadata: dict[str, Any] = Field(default_factory=dict)

    def get_step(self, step_id: str) -> PlanStep | None:
        """Get a step by ID (including nested parallel steps)."""
        for step in self.steps:
            if step.step_id == step_id:
                return step
            if step.parallel_steps:
                for pstep in step.parallel_steps:
                    if pstep.step_id == step_id:
                        return pstep
        return None

    def get_ready_steps(self) -> list[PlanStep]:
        """Get steps that are ready to execute (dependencies met)."""
        ready = []
        completed_ids = {s.step_id for s in self.steps if s.status == StepStatus.COMPLETED}
        for step in self.steps:
            if step.status != StepStatus.PENDING:
                continue
            if all(dep in completed_ids for dep in step.depends_on):
                ready.append(step)
        return ready

    def is_complete(self) -> bool:
        """Check if all steps are completed."""
        return all(s.status in (StepStatus.COMPLETED, StepStatus.SKIPPED) for s in self.steps)

    def has_failed(self) -> bool:
        """Check if any step has failed."""
        return any(s.status == StepStatus.FAILED for s in self.steps)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "plan_id": self.plan_id,
            "name": self.name,
            "description": self.description,
            "goal": self.goal,
            "steps": [s.to_dict() for s in self.steps],
            "status": self.status.value,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "context": self.context,
            "metadata": self.metadata,
        }


@dataclass
class ExecutionResult:
    """Result of plan execution."""

    plan_id: str
    success: bool
    completed_steps: int
    failed_steps: int
    total_steps: int
    results: dict[str, Any] = field(default_factory=dict)  # step_id -> result
    errors: dict[str, str] = field(default_factory=dict)   # step_id -> error
    execution_time: float = 0.0
    rollback_performed: bool = False
    rollback_errors: list[str] = field(default_factory=list)


class PlanValidationError(Exception):
    """Raised when plan validation fails."""

    def __init__(self, errors: list[str]) -> None:
        self.errors = errors
        super().__init__("; ".join(errors))


class PlanExecutionError(Exception):
    """Raised when plan execution fails."""

    def __init__(self, message: str, step_id: str | None = None, rollback: bool = False) -> None:
        self.step_id = step_id
        self.rollback = rollback
        super().__init__(message)