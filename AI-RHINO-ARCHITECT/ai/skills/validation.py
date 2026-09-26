"""Runtime validation for modeling skill inputs."""

from __future__ import annotations

import copy
import math
from collections.abc import Awaitable, Callable, Mapping
from dataclasses import dataclass, field
from typing import Any, Protocol

from .registry import ParameterDescriptor, SkillDefinition


class SkillInputValidationError(ValueError):
    """Raised when runtime inputs do not satisfy a skill contract."""

    def __init__(self, errors: list[str]) -> None:
        self.errors = errors
        super().__init__("; ".join(errors))


class SkillInputValidator:
    """Validate and normalize runtime parameters for a registered skill."""

    def validate(
        self, skill: SkillDefinition, values: dict[str, Any]
    ) -> dict[str, Any]:
        """Return normalized values or raise a structured validation error."""
        normalized: dict[str, Any] = {}
        errors: list[str] = []

        for name in skill.inputs:
            descriptor = skill.parameters[name]
            if name not in values:
                if descriptor.required and descriptor.default is None:
                    errors.append(f"missing_input: {name}")
                    continue
                if descriptor.default is not None:
                    normalized[name] = descriptor.default
                continue

            value = values[name]
            parameter_errors = self._validate_value(name, descriptor, value)
            errors.extend(parameter_errors)
            if not parameter_errors:
                normalized[name] = value

        unknown = sorted(set(values) - set(skill.inputs))
        errors.extend(f"invalid_parameter: unknown input '{name}'" for name in unknown)

        if errors:
            raise SkillInputValidationError(errors)
        return normalized

    def _validate_value(
        self, name: str, descriptor: ParameterDescriptor, value: Any
    ) -> list[str]:
        errors: list[str] = []
        parameter_type = descriptor.type

        if parameter_type in {"number", "integer"}:
            if isinstance(value, bool) or not isinstance(value, (int, float)):
                return [f"invalid_parameter: {name} must be a {parameter_type}"]
            if not math.isfinite(value):
                errors.append(f"invalid_parameter: {name} must be finite")
            if parameter_type == "integer" and not isinstance(value, int):
                errors.append(f"invalid_parameter: {name} must be an integer")
            if descriptor.minimum is not None and value < descriptor.minimum:
                errors.append(f"invalid_parameter: {name} must be >= {descriptor.minimum}")
            if descriptor.maximum is not None and value > descriptor.maximum:
                errors.append(f"invalid_parameter: {name} must be <= {descriptor.maximum}")
            return errors

        if parameter_type == "boolean" and not isinstance(value, bool):
            errors.append(f"invalid_parameter: {name} must be a boolean")
        elif parameter_type == "string" and not isinstance(value, str):
            errors.append(f"invalid_parameter: {name} must be a string")
        elif parameter_type == "enum":
            if not isinstance(value, str) or value not in (descriptor.choices or []):
                errors.append(f"invalid_parameter: {name} must be one of {descriptor.choices}")
        elif parameter_type in {"point", "vector"}:
            errors.extend(self._validate_coordinate_tuple(name, value))
        elif parameter_type == "list" and not isinstance(value, list):
            errors.append(f"invalid_parameter: {name} must be a list")

        return errors

    @staticmethod
    def _validate_coordinate_tuple(name: str, value: Any) -> list[str]:
        if not isinstance(value, (list, tuple)) or len(value) != 3:
            return [f"invalid_parameter: {name} must contain exactly 3 coordinates"]
        if any(isinstance(item, bool) or not isinstance(item, (int, float)) for item in value):
            return [f"invalid_parameter: {name} coordinates must be numeric"]
        if any(not math.isfinite(item) for item in value):
            return [f"invalid_parameter: {name} coordinates must be finite"]
        return []