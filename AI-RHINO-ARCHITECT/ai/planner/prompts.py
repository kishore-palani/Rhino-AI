"""Planning prompt templates for AI RHINO ARCHITECT.

Contains prompt templates for converting natural language goals into
structured execution plans using available modeling skills.
"""

from __future__ import annotations

from typing import Any

from ai.skills.registry import SkillRegistry


# System prompt for the planner
PLANNER_SYSTEM_PROMPT = """You are an expert architectural design planner for Rhino 3D.
Your task is to convert natural language design goals into structured, executable plans
using the available modeling skills.

You have access to a set of modeling skills that can create and manipulate geometry in Rhino.
Each skill has defined inputs, outputs, preconditions, and operations.

Your output must be a valid JSON plan following the specified schema.
Think step by step and create plans that are:
1. Complete - all necessary steps to achieve the goal
2. Ordered - dependencies between steps are explicit
3. Validated - each step's preconditions can be met
4. Recoverable - failures can be rolled back

Available skills will be provided in the context.
"""


# User prompt template for plan generation
PLANNER_USER_PROMPT_TEMPLATE = """Goal: {goal}

Context:
{context}

Available Skills:
{skills}

Create a plan to achieve the goal. The plan must be a JSON object with this structure:

{{
  "plan_id": "unique_id",
  "name": "descriptive_name",
  "description": "brief description",
  "goal": "{goal}",
  "steps": [
    {{
      "step_id": "step_1",
      "step_type": "skill",
      "skill_id": "create_wall",
      "inputs": {{
        "curve": "reference_to_previous_step_or_value",
        "height": 3000,
        "thickness": 200
      }},
      "depends_on": [],
      "description": "Create the main wall"
    }}
  ],
  "context": {{}}
}}

Rules:
1. Each step must have a unique step_id (e.g., "step_1", "step_2")
2. step_type is typically "skill" for modeling operations
3. skill_id must match an available skill exactly
4. inputs can be literal values or references to previous step outputs using format "{{step_id.output_name}}"
5. depends_on lists step_ids that must complete before this step
6. For complex goals, break into multiple steps with clear dependencies
7. Include validation steps where appropriate
8. The plan should be minimal but complete

Output ONLY the JSON plan, no additional text."""


# Prompt for plan validation/review
PLAN_VALIDATION_PROMPT = """Review the following plan for correctness and completeness.

Plan:
{plan_json}

Available Skills:
{skills}

Check for:
1. All skill_ids exist in available skills
2. All required inputs are provided (either literal or referenced)
3. References to previous step outputs are valid (step exists and produces that output)
4. Dependencies form a valid DAG (no cycles)
5. Preconditions can reasonably be met
6. Plan achieves the stated goal

Output a JSON object:
{{
  "valid": true/false,
  "errors": ["list of errors if any"],
  "warnings": ["list of warnings if any"],
  "suggestions": ["optional improvements"]
}}"""


# Prompt for plan refinement/fixing
PLAN_REFINEMENT_PROMPT = """The previous plan had validation errors. Please fix them.

Previous Plan:
{plan_json}

Validation Errors:
{errors}

Available Skills:
{skills}

Output a corrected JSON plan with the same structure."""


# Prompt for multi-step plan decomposition
PLAN_DECOMPOSITION_PROMPT = """Decompose the following high-level goal into a sequence of sub-goals,
each achievable by a single skill or small group of skills.

Goal: {goal}

Available Skills:
{skills}

Output a JSON array of sub-goals:
[
  {{"sub_goal": "Create the building footprint", "skills": ["create_rectangle", "create_wall"]}},
  {{"sub_goal": "Add floors", "skills": ["create_floor"]}},
  ...
]"""


def format_skills_for_prompt(registry: SkillRegistry) -> str:
    """Format available skills for inclusion in prompts."""
    skills = registry.list_skills()
    lines = []
    for skill in skills:
        lines.append(f"### {skill['skill_id']} ({skill['name']})")
        lines.append(f"  Description: {skill['description']}")
        lines.append(f"  Type: {skill['skill_type']}, Category: {skill['category']}")
        lines.append(f"  Inputs: {', '.join(skill['inputs'])}")
        lines.append(f"  Outputs: {', '.join(skill['outputs'])}")
        lines.append(f"  Parameters:")
        for param_name, param_def in skill['parameters'].items():
            req = "required" if param_def['required'] else "optional"
            desc = param_def['description']
            lines.append(f"    - {param_name} ({param_def['type']}, {req}): {desc}")
        lines.append(f"  Operations: {', '.join(skill['operations'])}")
        lines.append(f"  Rhino Tools Required: {', '.join(skill['metadata']['rhino_tools'])}")
        lines.append("")
    return "\n".join(lines)


def build_planner_prompt(goal: str, registry: SkillRegistry, context: dict[str, Any] | None = None) -> list[dict[str, str]]:
    """Build the complete prompt for plan generation."""
    context_str = "No additional context." if not context else "\n".join(f"  {k}: {v}" for k, v in context.items())
    skills_str = format_skills_for_prompt(registry)

    user_prompt = PLANNER_USER_PROMPT_TEMPLATE.format(
        goal=goal,
        context=context_str,
        skills=skills_str,
    )

    return [
        {"role": "system", "content": PLANNER_SYSTEM_PROMPT},
        {"role": "user", "content": user_prompt},
    ]


def build_validation_prompt(plan: dict[str, Any], registry: SkillRegistry) -> list[dict[str, str]]:
    """Build prompt for plan validation."""
    import json
    plan_json = json.dumps(plan, indent=2)
    skills_str = format_skills_for_prompt(registry)

    user_prompt = PLAN_VALIDATION_PROMPT.format(
        plan_json=plan_json,
        skills=skills_str,
    )

    return [
        {"role": "system", "content": "You are a plan validator for architectural modeling."},
        {"role": "user", "content": user_prompt},
    ]


def build_refinement_prompt(plan: dict[str, Any], errors: list[str], registry: SkillRegistry) -> list[dict[str, str]]:
    """Build prompt for plan refinement after validation errors."""
    import json
    plan_json = json.dumps(plan, indent=2)
    errors_str = "\n".join(f"- {e}" for e in errors)
    skills_str = format_skills_for_prompt(registry)

    user_prompt = PLAN_REFINEMENT_PROMPT.format(
        plan_json=plan_json,
        errors=errors_str,
        skills=skills_str,
    )

    return [
        {"role": "system", "content": "You are a plan refiner for architectural modeling."},
        {"role": "user", "content": user_prompt},
    ]


def build_decomposition_prompt(goal: str, registry: SkillRegistry) -> list[dict[str, str]]:
    """Build prompt for goal decomposition."""
    skills_str = format_skills_for_prompt(registry)

    user_prompt = PLAN_DECOMPOSITION_PROMPT.format(
        goal=goal,
        skills=skills_str,
    )

    return [
        {"role": "system", "content": "You are a goal decomposer for architectural modeling."},
        {"role": "user", "content": user_prompt},
    ]