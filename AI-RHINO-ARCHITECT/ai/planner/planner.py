"""LLM-based planner for AI RHINO ARCHITECT.

Converts natural language goals into structured execution plans using
available modeling skills and function calling.
"""

from __future__ import annotations

import json
import logging
import uuid
from typing import Any

from ai.skills.registry import SkillRegistry
from ai.planner.models import Plan, PlanStep, PlanStatus, PlanValidationError, StepStatus, StepType
from ai.planner.prompts import (
    build_planner_prompt,
    build_validation_prompt,
    build_refinement_prompt,
    format_skills_for_prompt,
)

logger = logging.getLogger(__name__)


class Planner:
    """LLM-based planner that converts natural language to execution plans."""

    def __init__(
        self,
        registry: SkillRegistry,
        llm_provider: Any = None,
        max_refinement_attempts: int = 3,
    ) -> None:
        """Initialize the planner.

        Args:
            registry: Skill registry with available skills
            llm_provider: LLM provider with a `complete` method (async)
            max_refinement_attempts: Maximum attempts to fix validation errors
        """
        self._registry = registry
        self._llm = llm_provider
        self._max_refinement_attempts = max_refinement_attempts

    async def create_plan(
        self,
        goal: str,
        context: dict[str, Any] | None = None,
        plan_id: str | None = None,
    ) -> Plan:
        """Create a plan from a natural language goal.

        Args:
            goal: Natural language description of the design goal
            context: Optional context (project info, constraints, etc.)
            plan_id: Optional plan ID (generated if not provided)

        Returns:
            Validated Plan object

        Raises:
            PlanValidationError: If plan cannot be validated after refinement attempts
        """
        if plan_id is None:
            plan_id = f"plan_{uuid.uuid4().hex[:8]}"

        # Generate initial plan
        plan_dict = await self._generate_plan(goal, context)

        # Validate and refine
        for attempt in range(self._max_refinement_attempts):
            valid, errors, warnings = await self._validate_plan(plan_dict)
            if valid:
                logger.info(f"Plan {plan_id} validated successfully on attempt {attempt + 1}")
                if warnings:
                    logger.warning(f"Plan warnings: {warnings}")
                break

            logger.warning(f"Plan validation failed (attempt {attempt + 1}): {errors}")
            if attempt < self._max_refinement_attempts - 1:
                plan_dict = await self._refine_plan(plan_dict, errors)
            else:
                raise PlanValidationError(errors)

        # Convert to Plan object
        plan = self._dict_to_plan(plan_dict, plan_id, goal, context)
        return plan

    async def _generate_plan(self, goal: str, context: dict[str, Any] | None) -> dict[str, Any]:
        """Generate initial plan using LLM."""
        if self._llm is None:
            # Fallback: create a simple deterministic plan for testing
            return self._create_fallback_plan(goal, context)

        messages = build_planner_prompt(goal, self._registry, context)
        response = await self._llm.complete(messages)

        # Extract JSON from response
        plan_dict = self._extract_json(response)
        return plan_dict

    async def _validate_plan(self, plan_dict: dict[str, Any]) -> tuple[bool, list[str], list[str]]:
        """Validate a plan using LLM and structural checks."""
        errors = []
        warnings = []

        # Structural validation
        struct_errors = self._validate_structure(plan_dict)
        errors.extend(struct_errors)

        # LLM-based validation if provider available
        if self._llm is not None and not errors:
            messages = build_validation_prompt(plan_dict, self._registry)
            response = await self._llm.complete(messages)
            result = self._extract_json(response)
            if not result.get("valid", False):
                errors.extend(result.get("errors", []))
            warnings.extend(result.get("warnings", []))

        return len(errors) == 0, errors, warnings

    async def _refine_plan(self, plan_dict: dict[str, Any], errors: list[str]) -> dict[str, Any]:
        """Refine plan based on validation errors."""
        if self._llm is None:
            # Can't refine without LLM
            raise PlanValidationError(errors)

        messages = build_refinement_prompt(plan_dict, errors, self._registry)
        response = await self._llm.complete(messages)
        return self._extract_json(response)

    def _validate_structure(self, plan_dict: dict[str, Any]) -> list[str]:
        """Perform structural validation of plan."""
        errors = []

        # Required fields
        required_fields = ["plan_id", "name", "goal", "steps"]
        for field in required_fields:
            if field not in plan_dict:
                errors.append(f"Missing required field: {field}")

        if "steps" not in plan_dict:
            return errors

        steps = plan_dict["steps"]
        step_ids = set()

        # Check each step
        for i, step in enumerate(steps):
            # Step ID
            step_id = step.get("step_id")
            if not step_id:
                errors.append(f"Step {i}: missing step_id")
            elif step_id in step_ids:
                errors.append(f"Duplicate step_id: {step_id}")
            else:
                step_ids.add(step_id)

            # Skill ID
            skill_id = step.get("skill_id")
            if skill_id and skill_id not in self._registry:
                errors.append(f"Step {step_id}: unknown skill '{skill_id}'")

            # Dependencies
            for dep in step.get("depends_on", []):
                if dep not in step_ids:
                    errors.append(f"Step {step_id}: depends on unknown step '{dep}'")

            # Input references
            for key, value in step.get("inputs", {}).items():
                if isinstance(value, str) and value.startswith("{{") and value.endswith("}}"):
                    ref = value[2:-2].strip()
                    if "." in ref:
                        ref_step_id, ref_output = ref.split(".", 1)
                        if ref_step_id not in step_ids:
                            errors.append(f"Step {step_id}: input '{key}' references unknown step '{ref_step_id}'")

        # Check for cycles in dependencies
        if not self._is_dag(steps):
            errors.append("Plan contains circular dependencies")

        return errors

    def _is_dag(self, steps: list[dict[str, Any]]) -> bool:
        """Check if step dependencies form a DAG."""
        graph = {s["step_id"]: set(s.get("depends_on", [])) for s in steps}
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

    def _extract_json(self, response: str) -> dict[str, Any]:
        """Extract JSON from LLM response."""
        # Try to find JSON in the response
        response = response.strip()

        # If response is already JSON
        if response.startswith("{"):
            return json.loads(response)

        # Try to extract from code blocks
        import re
        json_match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", response, re.DOTALL)
        if json_match:
            return json.loads(json_match.group(1))

        # Try to find first complete JSON object
        brace_count = 0
        start = -1
        for i, char in enumerate(response):
            if char == "{":
                if brace_count == 0:
                    start = i
                brace_count += 1
            elif char == "}":
                brace_count -= 1
                if brace_count == 0 and start >= 0:
                    try:
                        return json.loads(response[start:i+1])
                    except json.JSONDecodeError:
                        continue

        raise ValueError("Could not extract valid JSON from LLM response")

    def _create_fallback_plan(self, goal: str, context: dict[str, Any] | None) -> dict[str, Any]:
        """Create a simple fallback plan without LLM (for testing)."""
        # This is a very basic fallback - in practice you'd want an LLM
        goal_lower = goal.lower()
        steps = []

        if "wall" in goal_lower:
            steps.append({
                "step_id": "step_1",
                "step_type": "skill",
                "skill_id": "create_wall",
                "inputs": {
                    "curve": "{{step_0.curve_guid}}",
                    "height": 3000,
                    "thickness": 200
                },
                "depends_on": ["step_0"],
                "description": "Create wall from baseline"
            })
            steps.insert(0, {
                "step_id": "step_0",
                "step_type": "skill",
                "skill_id": "create_rectangle",
                "inputs": {
                    "plane": "world_xy",
                    "width": 10000,
                    "height": 8000
                },
                "depends_on": [],
                "description": "Create building footprint rectangle"
            })

        if not steps:
            # Default: create a point
            steps.append({
                "step_id": "step_1",
                "step_type": "skill",
                "skill_id": "create_point",
                "inputs": {"point": [0, 0, 0]},
                "depends_on": [],
                "description": "Create a point at origin"
            })

        return {
            "plan_id": f"plan_{uuid.uuid4().hex[:8]}",
            "name": "Fallback Plan",
            "description": "Auto-generated fallback plan",
            "goal": goal,
            "steps": steps,
            "context": context or {},
        }

    def _dict_to_plan(
        self,
        plan_dict: dict[str, Any],
        plan_id: str,
        goal: str,
        context: dict[str, Any] | None,
    ) -> Plan:
        """Convert plan dictionary to Plan object."""
        steps = [PlanStep.from_dict(s) for s in plan_dict.get("steps", [])]
        return Plan(
            plan_id=plan_dict.get("plan_id", plan_id),
            name=plan_dict.get("name", "Generated Plan"),
            description=plan_dict.get("description", ""),
            goal=goal,
            steps=steps,
            status=PlanStatus.VALID,
            context=context or {},
        )

    def get_available_skills_summary(self) -> str:
        """Get a summary of available skills for display."""
        return format_skills_for_prompt(self._registry)