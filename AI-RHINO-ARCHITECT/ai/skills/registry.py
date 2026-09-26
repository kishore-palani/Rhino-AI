"""Skill Registry for AI RHINO ARCHITECT.

Provides skill discovery, validation, and management using pydantic models.
"""

from __future__ import annotations

import copy
import json
import logging
import math
import os
from collections.abc import Awaitable, Callable, Mapping
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Protocol

from pydantic import BaseModel, Field, ValidationError, field_validator


class ParameterDescriptor(BaseModel):
    """Parameter descriptor for skill inputs."""

    type: str = Field(..., description="Parameter type from the type catalog")
    required: bool = Field(..., description="Whether the parameter must be supplied")
    description: str = Field(..., description="Human-readable parameter contract")
    default: Any | None = Field(None, description="Default value when parameter is optional")
    minimum: float | None = Field(None, description="Inclusive numeric lower bound")
    maximum: float | None = Field(None, description="Inclusive numeric upper bound")
    units: str | None = Field(None, description="Unit name or 'model_units'")
    choices: list[str] | None = Field(None, description="Allowed values for an enum parameter")
    geometry_role: str | None = Field(None, description="Semantic role of a geometry reference")

    @field_validator("type")
    @classmethod
    def validate_type(cls, v: str) -> str:
        valid_types = {
            "point", "vector", "plane", "curve", "surface", "brep", "mesh",
            "guid", "object_ref", "number", "integer", "boolean", "string", "enum", "list"
        }
        if v not in valid_types:
            raise ValueError(f"Invalid parameter type: {v}. Must be one of {valid_types}")
        return v


class SkillMetadata(BaseModel):
    """Metadata for skill discovery and lifecycle."""

    version: str = Field(..., description="Skill implementation version")
    status: str = Field(..., description="draft, experimental, stable, or deprecated")
    author: str = Field(..., description="Maintainer or team")
    risk_level: str = Field(..., description="read_only, low, medium, or high")
    side_effects: list[str] = Field(default_factory=list, description="Declared document or external-system effects")
    rhino_tools: list[str] = Field(default_factory=list, description="Required Rhino adapter or MCP tool identifiers")
    grasshopper_tools: list[str] = Field(default_factory=list, description="Required Grasshopper tool identifiers")
    tags: list[str] = Field(default_factory=list, description="Search and discovery tags")
    references: list[str] = Field(default_factory=list, description="Documentation, standards, or source references")
    created_at: str = Field(..., description="ISO-8601 creation timestamp")
    updated_at: str = Field(..., description="ISO-8601 last update timestamp")

    @field_validator("status")
    @classmethod
    def validate_status(cls, v: str) -> str:
        valid_statuses = {"draft", "experimental", "stable", "deprecated"}
        if v not in valid_statuses:
            raise ValueError(f"Invalid status: {v}. Must be one of {valid_statuses}")
        return v

    @field_validator("risk_level")
    @classmethod
    def validate_risk_level(cls, v: str) -> str:
        valid_levels = {"read_only", "low", "medium", "high"}
        if v not in valid_levels:
            raise ValueError(f"Invalid risk_level: {v}. Must be one of {valid_levels}")
        return v


class SkillDefinition(BaseModel):
    """Complete skill definition following the modeling skill schema."""

    schema_version: str = Field(..., description="Semantic version of this schema contract")
    skill_id: str = Field(..., description="Stable snake_case identifier, unique within the skill registry")
    name: str = Field(..., description="Human-readable skill name")
    description: str = Field(..., description="Concise description of the operation and expected result")
    skill_type: str = Field(..., description="Operation class: create, read, modify, boolean, or analysis")
    category: str = Field(..., description="Domain: geometry, architecture, parametric, or site")
    inputs: list[str] = Field(..., description="Ordered input names accepted by the skill")
    outputs: list[str] = Field(..., description="Result names returned after successful execution")
    parameters: dict[str, ParameterDescriptor] = Field(..., description="Named parameter descriptors keyed by input name")
    preconditions: list[str] = Field(..., description="Stable precondition rule identifiers")
    operations: list[str] = Field(..., description="Stable low-level operation identifiers executed in order")
    validation: list[str] = Field(..., description="Stable validation rule identifiers applied after execution")
    failure_modes: list[str] = Field(..., description="Stable failure codes that the skill can return")
    metadata: SkillMetadata = Field(..., description="Discovery, ownership, risk, tooling, and lifecycle information")

    @field_validator("schema_version")
    @classmethod
    def validate_schema_version(cls, v: str) -> str:
        if not v.startswith("0."):
            raise ValueError("Only schema version 0.x is supported")
        return v

    @field_validator("skill_type")
    @classmethod
    def validate_skill_type(cls, v: str) -> str:
        valid_types = {"create", "read", "modify", "boolean", "analysis"}
        if v not in valid_types:
            raise ValueError(f"Invalid skill_type: {v}. Must be one of {valid_types}")
        return v

    @field_validator("category")
    @classmethod
    def validate_category(cls, v: str) -> str:
        valid_categories = {"geometry", "architecture", "parametric", "site"}
        if v not in valid_categories:
            raise ValueError(f"Invalid category: {v}. Must be one of {valid_categories}")
        return v

    @field_validator("inputs")
    @classmethod
    def validate_inputs_unique(cls, v: list[str]) -> list[str]:
        if len(v) != len(set(v)):
            raise ValueError("Input names must be unique")
        return v

    @field_validator("parameters")
    @classmethod
    def validate_parameters_match_inputs(cls, v: dict[str, ParameterDescriptor], info: Any) -> dict[str, ParameterDescriptor]:
        if "inputs" in info.data:
            inputs = set(info.data["inputs"])
            params = set(v.keys())
            if inputs != params:
                missing = inputs - params
                extra = params - inputs
                errors = []
                if missing:
                    errors.append(f"Missing parameter descriptors for inputs: {missing}")
                if extra:
                    errors.append(f"Extra parameter descriptors not in inputs: {extra}")
                if errors:
                    raise ValueError("; ".join(errors))
        return v


class SkillRegistry:
    """Registry for managing modeling skills with validation and discovery."""

    SCHEMA_VERSION = "0.1.0"

    def __init__(self, skills_directory: str | None = None) -> None:
        """Initialize the skill registry.

        Args:
            skills_directory: Path to directory containing skill JSON files.
                            Defaults to knowledge/skills relative to this file.
        """
        if skills_directory is None:
            base_dir = Path(__file__).parent.parent.parent
            skills_directory = base_dir / "knowledge" / "skills"

        self._skills_dir = Path(skills_directory)
        self._skills: dict[str, SkillDefinition] = {}
        self._skill_files: dict[str, Path] = {}

    def register_skill(self, skill_def: dict) -> None:
        """Register a skill definition in the registry.

        Args:
            skill_def: Dictionary containing the skill definition.

        Raises:
            ValidationError: If the skill definition is invalid.
            ValueError: If a skill with the same ID already exists.
        """
        skill = SkillDefinition(**skill_def)

        if skill.skill_id in self._skills:
            raise ValueError(f"Skill with ID '{skill.skill_id}' already registered")

        self._skills[skill.skill_id] = skill
        self._skill_files[skill.skill_id] = self._skills_dir / f"{skill.skill_id}.json"

    def get_skill(self, skill_id: str) -> dict | None:
        """Get a skill definition by ID.

        Args:
            skill_id: The skill identifier to retrieve.

        Returns:
            Skill definition as dictionary, or None if not found.
        """
        skill = self._skills.get(skill_id)
        if skill is None:
            return None
        return skill.model_dump(mode="json")

    def validate_tool_availability(
        self, skill_id: str, available_tools: set[str]
    ) -> tuple[bool, list[str]]:
        """Check that a skill's declared Rhino tools exist in an adapter catalog."""
        skill = self._skills.get(skill_id)
        if skill is None:
            return False, [f"skill_not_found: {skill_id}"]

        missing = sorted(set(skill.metadata.rhino_tools) - available_tools)
        errors = [f"tool_unavailable: {tool_name}" for tool_name in missing]
        return not errors, errors

    def list_skills(self, category: str | None = None) -> list[dict]:
        """List all registered skills, optionally filtered by category.

        Args:
            category: Optional category filter (geometry, architecture, parametric, site).

        Returns:
            List of skill definitions as dictionaries.
        """
        skills = list(self._skills.values())
        if category:
            skills = [s for s in skills if s.category == category]
        return [s.model_dump(mode="json") for s in skills]

    def search_skills(self, query: str) -> list[dict]:
        """Search skills by name, description, tags, or skill_id.

        Args:
            query: Search query string (case-insensitive).

        Returns:
            List of matching skill definitions as dictionaries.
        """
        query_lower = query.lower()
        results = []

        for skill in self._skills.values():
            searchable = [
                skill.skill_id.lower(),
                skill.name.lower(),
                skill.description.lower(),
                skill.category.lower(),
                skill.skill_type.lower(),
                *[tag.lower() for tag in skill.metadata.tags],
                *[tool.lower() for tool in skill.metadata.rhino_tools],
                *[tool.lower() for tool in skill.metadata.grasshopper_tools],
            ]
            if any(query_lower in s for s in searchable):
                results.append(skill.model_dump(mode="json"))

        return results

    def validate_skill(self, skill_def: dict) -> tuple[bool, list[str]]:
        """Validate a skill definition against the schema.

        Args:
            skill_def: Dictionary containing the skill definition.

        Returns:
            Tuple of (is_valid, list_of_errors). Empty error list means valid.
        """
        try:
            SkillDefinition(**skill_def)
            return True, []
        except ValidationError as e:
            errors = [f"{err['loc']}: {err['msg']}" for err in e.errors()]
            return False, errors
        except Exception as e:
            return False, [str(e)]

    def discover_skills(self, directory: str | None = None) -> int:
        """Discover and load skills from JSON files in a directory.

        Args:
            directory: Path to directory containing skill JSON files.
                       Defaults to the registry's skills directory.

        Returns:
            Number of skills successfully loaded.
        """
        if directory is None:
            directory = str(self._skills_dir)

        skills_path = Path(directory)
        if not skills_path.exists():
            return 0

        loaded = 0
        for json_file in skills_path.glob("*.json"):
            if json_file.name == "skill_schema.json":
                continue

            try:
                with open(json_file, encoding="utf-8") as f:
                    skill_data = json.load(f)

                self.register_skill(skill_data)
                loaded += 1
            except (json.JSONDecodeError, ValidationError, ValueError) as e:
                print(f"Failed to load skill from {json_file}: {e}")
                continue

        return loaded

    def save_skill(self, skill_id: str, directory: str | None = None) -> Path | None:
        """Save a registered skill to a JSON file.

        Args:
            skill_id: The skill identifier to save.
            directory: Optional target directory. Defaults to registry's skills directory.

        Returns:
            Path to the saved file, or None if skill not found.
        """
        skill = self._skills.get(skill_id)
        if skill is None:
            return None

        if directory is None:
            directory = str(self._skills_dir)

        target_dir = Path(directory)
        target_dir.mkdir(parents=True, exist_ok=True)

        file_path = target_dir / f"{skill_id}.json"
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(skill.model_dump(mode="json"), f, indent=2)

        return file_path

    def remove_skill(self, skill_id: str) -> bool:
        """Remove a skill from the registry.

        Args:
            skill_id: The skill identifier to remove.

        Returns:
            True if skill was removed, False if not found.
        """
        if skill_id in self._skills:
            del self._skills[skill_id]
            del self._skill_files[skill_id]
            return True
        return False

    def get_categories(self) -> list[str]:
        """Get list of all categories present in registered skills."""
        return sorted({s.category for s in self._skills.values()})

    def get_skill_types(self) -> list[str]:
        """Get list of all skill types present in registered skills."""
        return sorted({s.skill_type for s in self._skills.values()})

    def __len__(self) -> int:
        return len(self._skills)

    def __contains__(self, skill_id: str) -> bool:
        return skill_id in self._skills

    def __iter__(self):
        return iter(self._skills.values())
