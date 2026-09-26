"""AI RHINO ARCHITECT - Skills Package.

This package provides the skill registry and management for modeling skills.
"""

from .executor import SkillExecutor, SkillExecutionError
from .registry import (
    ParameterDescriptor,
    SkillDefinition,
    SkillMetadata,
    SkillRegistry,
)
from .validation import SkillInputValidationError, SkillInputValidator


def validate_skill(skill_definition: dict) -> tuple[bool, list[str]]:
    """Validate a skill definition using the public skills package API."""
    return SkillRegistry().validate_skill(skill_definition)


__all__ = [
    "ParameterDescriptor",
    "SkillDefinition",
    "SkillMetadata",
    "SkillRegistry",
    "SkillInputValidationError",
    "SkillInputValidator",
    "SkillExecutor",
    "SkillExecutionError",
    "validate_skill",
]

__version__ = "0.1.0"