"""Unit tests for the planner module."""

from __future__ import annotations

import pytest

from ai.planner.models import (
    ExecutionResult,
    Plan,
    PlanStep,
    PlanStatus,
    PlanValidationError,
    StepStatus,
    StepType,
)
from ai.planner.validation import PlanValidator, validate_plan_dict
from ai.skills.registry import SkillRegistry


class TestPlanModels:
    """Tests for plan data models."""

    def test_plan_step_creation(self) -> None:
        """Test creating a plan step."""
        step = PlanStep(
            step_id="step_1",
            step_type=StepType.SKILL,
            skill_id="create_wall",
            inputs={"height": 3000, "thickness": 200},
            depends_on=[],
            description="Create main wall",
        )
        assert step.step_id == "step_1"
        assert step.skill_id == "create_wall"
        assert step.status == StepStatus.PENDING

    def test_plan_step_to_dict(self) -> None:
        """Test plan step serialization."""
        step = PlanStep(
            step_id="step_1",
            step_type=StepType.SKILL,
            skill_id="create_wall",
            inputs={"height": 3000},
            depends_on=[],
        )
        d = step.to_dict()
        assert d["step_id"] == "step_1"
        assert d["skill_id"] == "create_wall"
        assert d["inputs"]["height"] == 3000

    def test_plan_step_from_dict(self) -> None:
        """Test plan step deserialization."""
        data = {
            "step_id": "step_1",
            "step_type": "skill",
            "skill_id": "create_wall",
            "inputs": {"height": 3000},
            "depends_on": [],
            "description": "Test",
            "status": "pending",
        }
        step = PlanStep.from_dict(data)
        assert step.step_id == "step_1"
        assert step.skill_id == "create_wall"

    def test_plan_creation(self) -> None:
        """Test creating a plan."""
        steps = [
            PlanStep(step_id="step_1", skill_id="create_point", inputs={"point": [0, 0, 0]}),
            PlanStep(step_id="step_2", skill_id="create_line", inputs={"start": "{{step_1.point_guid}}", "end": [10, 10, 0]}, depends_on=["step_1"]),
        ]
        plan = Plan(
            plan_id="plan_1",
            name="Test Plan",
            goal="Create a line from origin",
            steps=steps,
        )
        assert plan.plan_id == "plan_1"
        assert len(plan.steps) == 2
        assert plan.status == PlanStatus.PENDING

    def test_plan_get_ready_steps(self) -> None:
        """Test getting ready steps."""
        steps = [
            PlanStep(step_id="step_1", skill_id="create_point", inputs={"point": [0, 0, 0]}),
            PlanStep(step_id="step_2", skill_id="create_line", inputs={}, depends_on=["step_1"]),
        ]
        plan = Plan(plan_id="plan_1", name="Test", goal="Test", steps=steps)

        # Initially only step_1 is ready
        ready = plan.get_ready_steps()
        assert len(ready) == 1
        assert ready[0].step_id == "step_1"

        # After step_1 completes, step_2 should be ready
        steps[0].status = StepStatus.COMPLETED
        ready = plan.get_ready_steps()
        assert len(ready) == 1
        assert ready[0].step_id == "step_2"

    def test_plan_is_complete(self) -> None:
        """Test plan completion check."""
        steps = [
            PlanStep(step_id="step_1", skill_id="create_point", inputs={}),
            PlanStep(step_id="step_2", skill_id="create_line", inputs={}),
        ]
        plan = Plan(plan_id="plan_1", name="Test", goal="Test", steps=steps)

        assert not plan.is_complete()

        steps[0].status = StepStatus.COMPLETED
        assert not plan.is_complete()

        steps[1].status = StepStatus.COMPLETED
        assert plan.is_complete()

    def test_plan_has_failed(self) -> None:
        """Test plan failure check."""
        steps = [
            PlanStep(step_id="step_1", skill_id="create_point", inputs={}),
        ]
        plan = Plan(plan_id="plan_1", name="Test", goal="Test", steps=steps)

        assert not plan.has_failed()

        steps[0].status = StepStatus.FAILED
        assert plan.has_failed()


class TestPlanValidator:
    """Tests for plan validation."""

    @pytest.fixture
    def registry(self) -> SkillRegistry:
        """Create a skill registry with test skills."""
        reg = SkillRegistry()
        reg.discover_skills()
        return reg

    def test_validate_valid_plan(self, registry: SkillRegistry) -> None:
        """Test validating a valid plan."""
        plan_dict = {
            "plan_id": "plan_1",
            "name": "Test Plan",
            "goal": "Create a point",
            "steps": [
                {
                    "step_id": "step_1",
                    "step_type": "skill",
                    "skill_id": "create_point",
                    "inputs": {"point": [0, 0, 0]},
                    "depends_on": [],
                }
            ],
        }
        valid, errors, warnings = validate_plan_dict(plan_dict, registry)
        assert valid
        assert len(errors) == 0

    def test_validate_missing_skill(self, registry: SkillRegistry) -> None:
        """Test validation fails for unknown skill."""
        plan_dict = {
            "plan_id": "plan_1",
            "name": "Test Plan",
            "goal": "Test",
            "steps": [
                {
                    "step_id": "step_1",
                    "step_type": "skill",
                    "skill_id": "nonexistent_skill",
                    "inputs": {},
                    "depends_on": [],
                }
            ],
        }
        valid, errors, warnings = validate_plan_dict(plan_dict, registry)
        assert not valid
        assert any("unknown skill" in e for e in errors)

    def test_validate_missing_required_input(self, registry: SkillRegistry) -> None:
        """Test validation fails for missing required input."""
        plan_dict = {
            "plan_id": "plan_1",
            "name": "Test Plan",
            "goal": "Test",
            "steps": [
                {
                    "step_id": "step_1",
                    "step_type": "skill",
                    "skill_id": "create_point",
                    "inputs": {},  # Missing required 'point'
                    "depends_on": [],
                }
            ],
        }
        valid, errors, warnings = validate_plan_dict(plan_dict, registry)
        assert not valid
        assert any("missing required input" in e for e in errors)

    def test_validate_unknown_input(self, registry: SkillRegistry) -> None:
        """Test validation fails for unknown input."""
        plan_dict = {
            "plan_id": "plan_1",
            "name": "Test Plan",
            "goal": "Test",
            "steps": [
                {
                    "step_id": "step_1",
                    "step_type": "skill",
                    "skill_id": "create_point",
                    "inputs": {"point": [0, 0, 0], "unknown_param": 123},
                    "depends_on": [],
                }
            ],
        }
        valid, errors, warnings = validate_plan_dict(plan_dict, registry)
        assert not valid
        assert any("unknown input" in e for e in errors)

    def test_validate_invalid_dependency(self, registry: SkillRegistry) -> None:
        """Test validation fails for unknown dependency."""
        plan_dict = {
            "plan_id": "plan_1",
            "name": "Test Plan",
            "goal": "Test",
            "steps": [
                {
                    "step_id": "step_1",
                    "step_type": "skill",
                    "skill_id": "create_point",
                    "inputs": {"point": [0, 0, 0]},
                    "depends_on": ["nonexistent_step"],
                }
            ],
        }
        valid, errors, warnings = validate_plan_dict(plan_dict, registry)
        assert not valid
        assert any("depends on unknown step" in e for e in errors)

    def test_validate_circular_dependency(self, registry: SkillRegistry) -> None:
        """Test validation fails for circular dependency."""
        plan_dict = {
            "plan_id": "plan_1",
            "name": "Test Plan",
            "goal": "Test",
            "steps": [
                {
                    "step_id": "step_1",
                    "step_type": "skill",
                    "skill_id": "create_point",
                    "inputs": {"point": [0, 0, 0]},
                    "depends_on": ["step_2"],
                },
                {
                    "step_id": "step_2",
                    "step_type": "skill",
                    "skill_id": "create_line",
                    "inputs": {"start": [0, 0, 0], "end": [10, 0, 0]},
                    "depends_on": ["step_1"],
                },
            ],
        }
        valid, errors, warnings = validate_plan_dict(plan_dict, registry)
        assert not valid
        assert any("circular" in e.lower() for e in errors)

    def test_validate_invalid_output_reference(self, registry: SkillRegistry) -> None:
        """Test validation fails for invalid output reference."""
        plan_dict = {
            "plan_id": "plan_1",
            "name": "Test Plan",
            "goal": "Test",
            "steps": [
                {
                    "step_id": "step_1",
                    "step_type": "skill",
                    "skill_id": "create_point",
                    "inputs": {"point": [0, 0, 0]},
                    "depends_on": [],
                },
                {
                    "step_id": "step_2",
                    "step_type": "skill",
                    "skill_id": "create_line",
                    "inputs": {"start": "{{step_1.nonexistent_output}}", "end": [10, 0, 0]},
                    "depends_on": ["step_1"],
                },
            ],
        }
        valid, errors, warnings = validate_plan_dict(plan_dict, registry)
        assert not valid
        assert any("non-existent output" in e for e in errors)

    def test_validate_unknown_step_reference(self, registry: SkillRegistry) -> None:
        """Test validation fails for reference to unknown step."""
        plan_dict = {
            "plan_id": "plan_1",
            "name": "Test Plan",
            "goal": "Test",
            "steps": [
                {
                    "step_id": "step_1",
                    "step_type": "skill",
                    "skill_id": "create_line",
                    "inputs": {"start": "{{unknown_step.point_guid}}", "end": [10, 0, 0]},
                    "depends_on": [],
                },
            ],
        }
        valid, errors, warnings = validate_plan_dict(plan_dict, registry)
        assert not valid
        assert any("unknown step" in e for e in errors)

    def test_validate_invalid_reference_format(self, registry: SkillRegistry) -> None:
        """Test validation fails for malformed reference."""
        plan_dict = {
            "plan_id": "plan_1",
            "name": "Test Plan",
            "goal": "Test",
            "steps": [
                {
                    "step_id": "step_1",
                    "step_type": "skill",
                    "skill_id": "create_line",
                    "inputs": {"start": "{step_1.point_guid}", "end": [10, 0, 0]},  # Missing braces
                    "depends_on": [],
                },
            ],
        }
        valid, errors, warnings = validate_plan_dict(plan_dict, registry)
        assert not valid
        assert any("invalid reference format" in e for e in errors)

    def test_validate_duplicate_step_ids(self, registry: SkillRegistry) -> None:
        """Test validation fails for duplicate step IDs."""
        plan_dict = {
            "plan_id": "plan_1",
            "name": "Test Plan",
            "goal": "Test",
            "steps": [
                {
                    "step_id": "step_1",
                    "step_type": "skill",
                    "skill_id": "create_point",
                    "inputs": {"point": [0, 0, 0]},
                    "depends_on": [],
                },
                {
                    "step_id": "step_1",  # Duplicate
                    "step_type": "skill",
                    "skill_id": "create_line",
                    "inputs": {"start": [0, 0, 0], "end": [10, 0, 0]},
                    "depends_on": [],
                },
            ],
        }
        valid, errors, warnings = validate_plan_dict(plan_dict, registry)
        assert not valid
        assert any("duplicate step_id" in e for e in errors)

    def test_validation_error_messages_are_lowercase(self, registry: SkillRegistry) -> None:
        """Error message bodies use lowercase, matching the rest of the validator."""
        duplicate_plan = {
            "plan_id": "plan_1",
            "name": "Test Plan",
            "goal": "Test",
            "steps": [
                {
                    "step_id": "step_1",
                    "step_type": "skill",
                    "skill_id": "create_point",
                    "inputs": {"point": [0, 0, 0]},
                    "depends_on": [],
                },
                {
                    "step_id": "step_1",
                    "step_type": "skill",
                    "skill_id": "create_line",
                    "inputs": {"start": [0, 0, 0], "end": [10, 0, 0]},
                    "depends_on": [],
                },
            ],
        }
        valid, errors, _ = validate_plan_dict(duplicate_plan, registry)
        assert not valid
        assert any(e == "duplicate step_id: step_1" for e in errors)

        missing_input_plan = {
            "plan_id": "plan_1",
            "name": "Test Plan",
            "goal": "Test",
            "steps": [
                {
                    "step_id": "step_1",
                    "step_type": "skill",
                    "skill_id": "create_point",
                    "inputs": {},
                    "depends_on": [],
                }
            ],
        }
        valid, errors, _ = validate_plan_dict(missing_input_plan, registry)
        assert not valid
        assert any(e == "Step step_1 (create_point): missing required input 'point'" for e in errors)


class TestPlanValidatorClass:
    """Tests for PlanValidator class."""

    @pytest.fixture
    def registry(self) -> SkillRegistry:
        """Create a skill registry with test skills."""
        reg = SkillRegistry()
        reg.discover_skills()
        return reg

    @pytest.fixture
    def validator(self, registry: SkillRegistry) -> PlanValidator:
        """Create a plan validator."""
        return PlanValidator(registry)

    def test_validate_step_inputs_valid(self, validator: PlanValidator) -> None:
        """Test validating valid step inputs."""
        valid, errors = validator.validate_step_inputs(
            "create_point",
            {"point": [10, 20, 30]},
        )
        assert valid
        assert len(errors) == 0

    def test_validate_step_inputs_missing_required(self, validator: PlanValidator) -> None:
        """Test validating step inputs with missing required."""
        valid, errors = validator.validate_step_inputs(
            "create_point",
            {},  # Missing 'point'
        )
        assert not valid
        assert any("missing required" in e for e in errors)

    def test_validate_step_inputs_missing_required_message_case(
        self, validator: PlanValidator
    ) -> None:
        """Missing-input message body from validate_step_inputs is lowercase."""
        valid, errors = validator.validate_step_inputs("create_point", {})
        assert not valid
        assert "missing required input: point" in errors

    def test_validate_step_inputs_with_reference(self, validator: PlanValidator) -> None:
        """Test validating step inputs with references."""
        available = {
            "step_1": {"point_guid": "guid-123", "point_ref": "ref-123"},
        }
        valid, errors = validator.validate_step_inputs(
            "create_line",
            {"start": "{{step_1.point_guid}}", "end": [10, 0, 0]},
            available_outputs=available,
        )
        assert valid
        assert len(errors) == 0

    def test_validate_step_inputs_invalid_reference(self, validator: PlanValidator) -> None:
        """Test validating step inputs with invalid reference."""
        available = {
            "step_1": {"point_guid": "guid-123"},
        }
        valid, errors = validator.validate_step_inputs(
            "create_line",
            {"start": "{{step_1.nonexistent}}", "end": [10, 0, 0]},
            available_outputs=available,
        )
        assert not valid
        assert any("no output" in e for e in errors)


class TestExecutionResult:
    """Tests for execution result model."""

    def test_execution_result_creation(self) -> None:
        """Test creating an execution result."""
        result = ExecutionResult(
            plan_id="plan_1",
            success=True,
            completed_steps=3,
            failed_steps=0,
            total_steps=3,
        )
        assert result.plan_id == "plan_1"
        assert result.success
        assert result.completed_steps == 3