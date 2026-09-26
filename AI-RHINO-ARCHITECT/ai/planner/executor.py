"""Plan execution engine with rollback support for AI RHINO ARCHITECT.

Executes validated plans step by step, handles errors, and supports
transactional rollback on failure.
"""

from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from ai.skills.executor import SkillExecutor
from ai.skills.registry import SkillRegistry
from rhino.adapters.base import RhinoAdapter

from ai.planner.models import (
    ExecutionResult,
    Plan,
    PlanExecutionError,
    PlanStep,
    PlanStatus,
    StepStatus,
    StepType,
)

logger = logging.getLogger(__name__)


@dataclass
class ExecutionContext:
    """Runtime context for plan execution."""

    plan: Plan
    skill_executor: SkillExecutor
    adapter: RhinoAdapter
    registry: SkillRegistry
    variables: dict[str, Any] = field(default_factory=dict)  # Resolved variable values
    step_results: dict[str, dict[str, Any]] = field(default_factory=dict)  # step_id -> outputs
    object_counts: dict[str, int] = field(default_factory=dict)  # step_id -> object count before
    rollback_stack: list[tuple[str, dict[str, Any]]] = field(default_factory=list)  # (step_id, rollback_data)


class PlanExecutor:
    """Executes plans with transactional semantics and rollback support."""

    def __init__(
        self,
        skill_executor: SkillExecutor,
        adapter: RhinoAdapter,
        registry: SkillRegistry,
        max_parallel_steps: int = 4,
        default_timeout: float = 60.0,
    ) -> None:
        """Initialize the plan executor.

        Args:
            skill_executor: Skill executor for running individual skills
            adapter: Rhino adapter for direct tool calls (rollback)
            registry: Skill registry for validation
            max_parallel_steps: Maximum concurrent steps in parallel groups
            default_timeout: Default timeout per step in seconds
        """
        self._executor = skill_executor
        self._adapter = adapter
        self._registry = registry
        self._max_parallel = max_parallel_steps
        self._default_timeout = default_timeout

    async def execute(self, plan: Plan, dry_run: bool = False) -> ExecutionResult:
        """Execute a plan.

        Args:
            plan: Validated plan to execute
            dry_run: If True, validate but don't execute

        Returns:
            ExecutionResult with success status and details
        """
        start_time = time.time()
        plan.status = PlanStatus.EXECUTING
        plan.started_at = datetime.now()

        ctx = ExecutionContext(
            plan=plan,
            skill_executor=self._executor,
            adapter=self._adapter,
            registry=self._registry,
        )

        result = ExecutionResult(
            plan_id=plan.plan_id,
            success=False,
            completed_steps=0,
            failed_steps=0,
            total_steps=len(plan.steps),
        )

        try:
            if dry_run:
                logger.info(f"Dry run for plan {plan.plan_id}")
                result.success = True
                result.execution_time = time.time() - start_time
                plan.status = PlanStatus.COMPLETED
                return result

            # Execute steps in dependency order
            while not plan.is_complete() and not plan.has_failed():
                ready_steps = plan.get_ready_steps()
                if not ready_steps:
                    # No ready steps but plan not complete - deadlock or all remaining are failed deps
                    remaining = [s for s in plan.steps if s.status == StepStatus.PENDING]
                    for step in remaining:
                        step.status = StepStatus.FAILED
                        step.error = "Dependency failed or circular dependency"
                        result.failed_steps += 1
                    break

                # Execute ready steps (respecting parallelism)
                await self._execute_steps(ready_steps, ctx, result)

            # Final status
            if plan.has_failed():
                plan.status = PlanStatus.FAILED
                # Attempt rollback
                await self._rollback(ctx, result)
            else:
                plan.status = PlanStatus.COMPLETED
                result.success = True

        except Exception as e:
            logger.exception(f"Plan execution failed: {e}")
            plan.status = PlanStatus.FAILED
            result.success = False
            result.errors["_plan"] = str(e)
            await self._rollback(ctx, result)

        finally:
            plan.completed_at = datetime.now()
            result.execution_time = time.time() - start_time

        return result

    async def _execute_steps(
        self,
        steps: list[PlanStep],
        ctx: ExecutionContext,
        result: ExecutionResult,
    ) -> None:
        """Execute a batch of ready steps."""
        # Group by step type
        skill_steps = [s for s in steps if s.step_type == StepType.SKILL]
        parallel_groups = [s for s in steps if s.step_type == StepType.PARALLEL]

        # Execute skill steps with limited concurrency
        semaphore = asyncio.Semaphore(self._max_parallel)

        async def execute_with_semaphore(step: PlanStep) -> None:
            async with semaphore:
                await self._execute_step(step, ctx, result)

        await asyncio.gather(*[execute_with_semaphore(s) for s in skill_steps])

        # Execute parallel groups
        for group_step in parallel_groups:
            await self._execute_parallel_group(group_step, ctx, result)

    async def _execute_step(
        self,
        step: PlanStep,
        ctx: ExecutionContext,
        result: ExecutionResult,
    ) -> None:
        """Execute a single skill step."""
        step.status = StepStatus.RUNNING
        step.started_at = datetime.now()
        logger.info(f"Executing step {step.step_id}: {step.skill_id}")

        try:
            # Resolve input references
            resolved_inputs = self._resolve_inputs(step.inputs, ctx)

            # Record object count before execution (for rollback)
            obj_count_result = await ctx.adapter.call_tool("run_python", {
                "script": "import rhinoscriptsyntax as rs; print(rs.ObjectCount())"
            })
            before_count = 0
            if "content" in obj_count_result and obj_count_result["content"]:
                import json
                text = obj_count_result["content"][0].get("text", "0")
                try:
                    outer = json.loads(text)
                    stdout = outer.get("stdout", text)
                    before_count = int(json.loads(stdout)) if isinstance(stdout, str) else int(stdout)
                except (json.JSONDecodeError, ValueError):
                    pass
            ctx.object_counts[step.step_id] = before_count

            # Execute skill
            skill_result = await ctx.skill_executor.execute(step.skill_id, resolved_inputs)

            # Store result
            step.result = skill_result
            step.status = StepStatus.COMPLETED
            step.completed_at = datetime.now()
            ctx.step_results[step.step_id] = skill_result

            # Update context variables with outputs
            for key, value in skill_result.items():
                ctx.variables[f"{step.step_id}.{key}"] = value

            result.completed_steps += 1
            result.results[step.step_id] = skill_result
            logger.info(f"Step {step.step_id} completed successfully")

        except Exception as e:
            step.status = StepStatus.FAILED
            step.error = str(e)
            step.completed_at = datetime.now()
            result.failed_steps += 1
            result.errors[step.step_id] = str(e)
            logger.error(f"Step {step.step_id} failed: {e}")
            raise PlanExecutionError(str(e), step_id=step.step_id, rollback=True) from e

    async def _execute_parallel_group(
        self,
        group_step: PlanStep,
        ctx: ExecutionContext,
        result: ExecutionResult,
    ) -> None:
        """Execute a parallel group of steps."""
        group_step.status = StepStatus.RUNNING
        group_step.started_at = datetime.now()

        # Execute all parallel steps concurrently
        semaphore = asyncio.Semaphore(self._max_parallel)

        async def execute_parallel_step(step: PlanStep) -> None:
            async with semaphore:
                await self._execute_step(step, ctx, result)

        await asyncio.gather(*[execute_parallel_step(s) for s in group_step.parallel_steps])

        # Check if any failed
        failed = [s for s in group_step.parallel_steps if s.status == StepStatus.FAILED]
        if failed:
            group_step.status = StepStatus.FAILED
            group_step.error = f"{len(failed)} parallel steps failed"
        else:
            group_step.status = StepStatus.COMPLETED

        group_step.completed_at = datetime.now()

    def _resolve_inputs(self, inputs: dict[str, Any], ctx: ExecutionContext) -> dict[str, Any]:
        """Resolve input references to actual values."""
        resolved = {}
        for key, value in inputs.items():
            if isinstance(value, str) and value.startswith("{{") and value.endswith("}}"):
                ref = value[2:-2].strip()
                if ref in ctx.variables:
                    resolved[key] = ctx.variables[ref]
                elif "." in ref:
                    step_id, output_name = ref.split(".", 1)
                    if step_id in ctx.step_results and output_name in ctx.step_results[step_id]:
                        resolved[key] = ctx.step_results[step_id][output_name]
                    else:
                        raise ValueError(f"Unresolved reference: {ref}")
                else:
                    raise ValueError(f"Invalid reference format: {ref}")
            else:
                resolved[key] = value
        return resolved

    async def _rollback(self, ctx: ExecutionContext, result: ExecutionResult) -> None:
        """Rollback executed steps in reverse order."""
        logger.info(f"Rolling back plan {ctx.plan.plan_id}")
        result.rollback_performed = True

        # Get completed steps in reverse order
        completed_steps = [
            s for s in ctx.plan.steps
            if s.status == StepStatus.COMPLETED
        ]
        completed_steps.reverse()

        for step in completed_steps:
            try:
                await self._rollback_step(step, ctx)
                step.status = StepStatus.ROLLED_BACK
                logger.info(f"Rolled back step {step.step_id}")
            except Exception as e:
                error_msg = f"Rollback failed for step {step.step_id}: {e}"
                logger.error(error_msg)
                result.rollback_errors.append(error_msg)

        ctx.plan.status = PlanStatus.ROLLED_BACK

    async def _rollback_step(self, step: PlanStep, ctx: ExecutionContext) -> None:
        """Rollback a single step by undoing in Rhino."""
        # Use Rhino's undo mechanism
        # The skill executor already wraps operations in transactions
        # but we can also explicitly undo if needed

        # Get the object count before this step
        before_count = ctx.object_counts.get(step.step_id, 0)

        # Count current objects
        obj_count_result = await ctx.adapter.call_tool("run_python", {
            "script": "import rhinoscriptsyntax as rs; print(rs.ObjectCount())"
        })
        current_count = 0
        if "content" in obj_count_result and obj_count_result["content"]:
            import json
            text = obj_count_result["content"][0].get("text", "0")
            try:
                outer = json.loads(text)
                stdout = outer.get("stdout", text)
                current_count = int(json.loads(stdout)) if isinstance(stdout, str) else int(stdout)
            except (json.JSONDecodeError, ValueError):
                pass

        # If objects were added, undo
        if current_count > before_count:
            undo_count = current_count - before_count
            for _ in range(undo_count):
                await ctx.adapter.call_tool("run_python", {
                    "script": "import rhinoscriptsyntax as rs; rs.Command('_-Undo', False)"
                })

    async def validate_plan(self, plan: Plan) -> tuple[bool, list[str]]:
        """Validate a plan without executing.

        Args:
            plan: Plan to validate

        Returns:
            Tuple of (is_valid, list_of_errors)
        """
        errors = []

        # Check all skills exist
        for step in plan.steps:
            if step.skill_id and step.skill_id not in self._registry:
                errors.append(f"Step {step.step_id}: unknown skill '{step.skill_id}'")

            # Check dependencies
            for dep in step.depends_on:
                if not any(s.step_id == dep for s in plan.steps):
                    errors.append(f"Step {step.step_id}: depends on unknown step '{dep}'")

        # Check for cycles
        if not self._is_dag([s.to_dict() for s in plan.steps]):
            errors.append("Plan contains circular dependencies")

        # Validate each skill's inputs against schema
        for step in plan.steps:
            if step.skill_id:
                skill = self._registry.get_skill(step.skill_id)
                if skill:
                    # Check required inputs
                    for param_name, param_def in skill.get("parameters", {}).items():
                        if param_def.get("required", False):
                            if param_name not in step.inputs:
                                errors.append(f"Step {step.step_id}: missing required input '{param_name}'")

        return len(errors) == 0, errors

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