"""Plan validation for AI RHINO ARCHITECT.

Validates plans before execution, checking for structural correctness,
skill availability, input completeness, and dependency validity.
"""

from __future__ import annotations

import logging
from typing import Any

from ai.skills.registry import SkillRegistry
from ai.planner.models import Plan, PlanStep, PlanValidationError, StepStatus, StepType

logger = logging.getLogger(__name__)


class PlanValidator:
    """Validates execution plans for correctness and executability."""

    def __init__(self, registry: SkillRegistry) -> None:
        """Initialize the validator.

        Args:
            registry: Skill registry with available skills
        """
        self._registry = registry

    def validate(self, plan: Plan) -> tuple[bool, list[str], list[str]]:
        """Validate a plan comprehensively.

        Args:
            plan: Plan to validate

        Returns:
            Tuple of (is_valid, errors, warnings)
        """
        errors = []
        warnings = []

        # Structural validation
        errors.extend(self._validate_structure(plan))

        # Skill availability validation
        errors.extend(self._validate_skills(plan))

        # Input validation
        errors.extend(self._validate_inputs(plan))

        # Dependency validation
        errors.extend(self._validate_dependencies(plan))

        # Output reference validation
        errors.extend(self._validate_output_references(plan))

        # Precondition validation (static checks)
        warnings.extend(self._validate_preconditions(plan))

        # Cycle detection
        if not self._is_dag(plan):
            errors.append("Plan contains circular dependencies")

        return len(errors) == 0, errors, warnings

    def _validate_structure(self, plan: Plan) -> list[str]:
        """Validate basic plan structure."""
        errors = []

        if not plan.plan_id:
            errors.append("Plan missing plan_id")

        if not plan.name:
            errors.append("Plan missing name")

        if not plan.goal:
            errors.append("Plan missing goal")

        if not plan.steps:
            errors.append("Plan has no steps")

        # Check for duplicate step IDs
        step_ids = set()
        for step in plan.steps:
            if step.step_id in step_ids:
                errors.append(f"duplicate step_id: {step.step_id}")
            step_ids.add(step.step_id)

        return errors

    def _validate_skills(self, plan: Plan) -> list[str]:
        """Validate that all referenced skills exist."""
        errors = []

        for step in plan.steps:
            if step.step_type == StepType.SKILL:
                if not step.skill_id:
                    errors.append(f"Step {step.step_id}: skill step missing skill_id")
                elif step.skill_id not in self._registry:
                    errors.append(f"Step {step.step_id}: unknown skill '{step.skill_id}'")

        return errors

    def _validate_inputs(self, plan: Plan) -> list[str]:
        """Validate step inputs against skill parameter definitions."""
        errors = []

        for step in plan.steps:
            if step.step_type != StepType.SKILL or not step.skill_id:
                continue

            skill = self._registry.get_skill(step.skill_id)
            if not skill:
                continue  # Already reported as unknown skill

            # Check required inputs
            for param_name, param_def in skill.get("parameters", {}).items():
                if param_def.get("required", False):
                    if param_name not in step.inputs:
                        errors.append(
                            f"Step {step.step_id} ({step.skill_id}): "
                            f"missing required input '{param_name}'"
                        )

            # Check for unknown inputs
            known_params = set(skill.get("parameters", {}).keys())
            for input_name in step.inputs:
                if input_name not in known_params:
                    errors.append(
                        f"Step {step.step_id} ({step.skill_id}): "
                        f"unknown input '{input_name}'"
                    )

        return errors

    def _validate_dependencies(self, plan: Plan) -> list[str]:
        """Validate step dependencies."""
        errors = []
        step_ids = {s.step_id for s in plan.steps}

        for step in plan.steps:
            for dep in step.depends_on:
                if dep not in step_ids:
                    errors.append(
                        f"Step {step.step_id}: depends on unknown step '{dep}'"
                    )

        return errors

    def _validate_output_references(self, plan: Plan) -> list[str]:
        """Validate that output references point to valid step outputs."""
        errors = []

        # Build map of step_id -> outputs
        step_outputs = {}
        for step in plan.steps:
            if step.skill_id:
                skill = self._registry.get_skill(step.skill_id)
                if skill:
                    step_outputs[step.step_id] = set(skill.get("outputs", []))

        for step in plan.steps:
            for key, value in step.inputs.items():
                if isinstance(value, str):
                    # Check for double-brace format {{step_id.output}}
                    if value.startswith("{{") and value.endswith("}}"):
                        ref = value[2:-2].strip()
                        if "." in ref:
                            ref_step_id, ref_output = ref.split(".", 1)
                            if ref_step_id not in step_outputs:
                                errors.append(
                                    f"Step {step.step_id}: input '{key}' references "
                                    f"unknown step '{ref_step_id}'"
                                )
                            elif ref_output not in step_outputs[ref_step_id]:
                                errors.append(
                                    f"Step {step.step_id}: input '{key}' references "
                                    f"non-existent output '{ref_output}' from step '{ref_step_id}'"
                                )
                        else:
                            errors.append(
                                f"Step {step.step_id}: input '{key}' has invalid "
                                f"reference format '{value}' (expected '{{step_id.output_name}}')"
                            )
                    # Check for single-brace format {step_id.output} - invalid
                    elif value.startswith("{") and value.endswith("}") and "." in value:
                        errors.append(
                            f"Step {step.step_id}: input '{key}' has invalid "
                            f"reference format '{value}' (expected '{{step_id.output_name}}', not single braces)"
                        )

        return errors

    def _validate_preconditions(self, plan: Plan) -> list[str]:
        """Validate preconditions that can be checked statically."""
        warnings = []

        for step in plan.steps:
            if step.step_type != StepType.SKILL or not step.skill_id:
                continue

            skill = self._registry.get_skill(step.skill_id)
            if not skill:
                continue

            preconditions = skill.get("preconditions", [])
            for precond in preconditions:
                # Static precondition checks
                if precond == "document_connected":
                    warnings.append(
                        f"Step {step.step_id}: requires active Rhino document connection"
                    )
                elif precond == "scope_allowed":
                    warnings.append(
                        f"Step {step.step_id}: requires appropriate execution scope/permissions"
                    )

        return warnings

    def _is_dag(self, plan: Plan) -> bool:
        """Check if step dependencies form a DAG."""
        graph = {s.step_id: set(s.depends_on) for s in plan.steps}
        visited = set()
        rec_stack = set()

        def dfs(node: str) -> bool:
            visited.add(node)
            rec_stack.add(node)
            for neighbor in graph.get(node, []):
                if neighbor not in visited:
                    if dfs(neighbor):
                        return True
                elif neighbor in rec_stack:
                    return True
            rec_stack.remove(node)
            return False

        for node in graph:
            if node not in visited:
                if dfs(node):
                    return False
        return True

    def validate_step_inputs(
        self,
        skill_id: str,
        inputs: dict[str, Any],
        available_outputs: dict[str, dict[str, Any]] | None = None,
    ) -> tuple[bool, list[str]]:
        """Validate inputs for a single skill step.

        Args:
            skill_id: The skill to validate inputs for
            inputs: Input values to validate
            available_outputs: Map of step_id -> outputs available for reference resolution

        Returns:
            Tuple of (is_valid, errors)
        """
        errors = []

        skill = self._registry.get_skill(skill_id)
        if not skill:
            return False, [f"Unknown skill: {skill_id}"]

        # Check required inputs
        for param_name, param_def in skill.get("parameters", {}).items():
            if param_def.get("required", False):
                if param_name not in inputs:
                    errors.append(f"missing required input: {param_name}")
                else:
                    # Validate input value
                    value = inputs[param_name]
                    if isinstance(value, str) and value.startswith("{{") and value.endswith("}}"):
                        # Reference - validate it can be resolved
                        if available_outputs:
                            ref = value[2:-2].strip()
                            if "." in ref:
                                ref_step_id, ref_output = ref.split(".", 1)
                                if ref_step_id not in available_outputs:
                                    errors.append(f"Input '{param_name}': reference to unknown step '{ref_step_id}'")
                                elif ref_output not in available_outputs[ref_step_id]:
                                    errors.append(f"Input '{param_name}': step '{ref_step_id}' has no output '{ref_output}'")
                        # If no available_outputs, we can't validate references statically
                    else:
                        # Literal value - basic type validation could go here
                        pass

        return len(errors) == 0, errors


def validate_plan_dict(plan_dict: dict[str, Any], registry: SkillRegistry) -> tuple[bool, list[str], list[str]]:
    """Convenience function to validate a plan dictionary.

    Args:
        plan_dict: Plan as dictionary
        registry: Skill registry

    Returns:
        Tuple of (is_valid, errors, warnings)
    """
    from ai.planner.models import Plan, PlanStep, StepType, StepStatus

    # Convert to Plan object
    steps = [PlanStep.from_dict(s) for s in plan_dict.get("steps", [])]
    plan = Plan(
        plan_id=plan_dict.get("plan_id", ""),
        name=plan_dict.get("name", ""),
        description=plan_dict.get("description", ""),
        goal=plan_dict.get("goal", ""),
        steps=steps,
    )

    validator = PlanValidator(registry)
    return validator.validate(plan)