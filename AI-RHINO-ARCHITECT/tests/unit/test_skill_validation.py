import pytest

from ai.skills import (
    SkillDefinition,
    SkillInputValidationError,
    SkillInputValidator,
    SkillRegistry,
)


def _skill(skill_id: str):
    registry = SkillRegistry()
    registry.discover_skills()
    definition = registry.get_skill(skill_id)
    assert definition is not None
    return SkillDefinition(**definition)


def test_valid_point_inputs_are_normalized() -> None:
    skill = _skill("create_point")

    result = SkillInputValidator().validate(skill, {"point": (1, 2.5, 0)})

    assert result == {"point": (1, 2.5, 0)}


def test_missing_and_unknown_inputs_are_reported() -> None:
    skill = _skill("create_wall")

    with pytest.raises(SkillInputValidationError) as error:
        SkillInputValidator().validate(skill, {"curve": "baseline", "extra": 1})

    assert "missing_input: height" in error.value.errors
    assert "missing_input: thickness" in error.value.errors
    assert "invalid_parameter: unknown input 'extra'" in error.value.errors


def test_wall_dimensions_must_be_positive() -> None:
    skill = _skill("create_wall")

    with pytest.raises(SkillInputValidationError) as error:
        SkillInputValidator().validate(
            skill, {"curve": "baseline", "height": -0.1, "thickness": -0.2}
        )

    assert "invalid_parameter: height must be >= 0.0" in error.value.errors
    assert "invalid_parameter: thickness must be >= 0.0" in error.value.errors


def test_create_point_declared_tools_are_checked_against_adapter_catalog() -> None:
    registry = SkillRegistry()
    registry.discover_skills()

    available, errors = registry.validate_tool_availability(
        "create_point", {"create_object", "get_object_info"}
    )

    assert available is True
    assert errors == []


def test_missing_skill_tools_are_reported() -> None:
    registry = SkillRegistry()
    registry.discover_skills()

    available, errors = registry.validate_tool_availability(
        "create_point", {"create_object"}
    )

    assert available is False
    assert errors == ["tool_unavailable: get_object_info"]