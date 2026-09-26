"""
Unit tests for skill_memory module.
"""

from __future__ import annotations

import pytest

from ai.memory.skill_memory import SkillExecution, SkillMemory


@pytest.fixture
def skill_memory():
    """Create a fresh SkillMemory instance for testing."""
    mem = SkillMemory()
    mem.clear()
    return mem


def test_record_execution_success(skill_memory):
    """Test recording a successful skill execution."""
    execution = SkillExecution(
        skill_id="create_wall",
        parameters={"height": 3000, "thickness": 200},
        success=True,
        execution_time_ms=150.5,
        geometry_ids=["guid-123"],
    )
    result = skill_memory.record_execution(execution)
    assert len(skill_memory._local_history) == 1
    assert skill_memory._local_history[0].skill_id == "create_wall"


def test_record_execution_failure(skill_memory):
    """Test recording a failed skill execution."""
    execution = SkillExecution(
        skill_id="create_column",
        parameters={"width": 100, "height": 3000},
        success=False,
        error="Dimension too small",
    )
    skill_memory.record_execution(execution)
    assert len(skill_memory._local_history) == 1
    assert skill_memory._local_history[0].success is False


def test_get_success_rate_no_executions(skill_memory):
    """Test success rate returns 1.0 for skills never executed."""
    rate = skill_memory.get_success_rate("unknown_skill")
    assert rate == 1.0


def test_get_success_rate_all_success(skill_memory):
    """Test success rate with all successful executions."""
    for i in range(3):
        skill_memory.record_execution(
            SkillExecution(
                skill_id="create_wall",
                parameters={"height": 3000},
                success=True,
            )
        )
    rate = skill_memory.get_success_rate("create_wall")
    assert rate == 1.0


def test_get_success_rate_mixed(skill_memory):
    """Test success rate with mixed success/failure."""
    skill_memory.record_execution(
        SkillExecution(skill_id="create_door", parameters={}, success=True)
    )
    skill_memory.record_execution(
        SkillExecution(skill_id="create_door", parameters={}, success=False)
    )
    skill_memory.record_execution(
        SkillExecution(skill_id="create_door", parameters={}, success=True)
    )
    rate = skill_memory.get_success_rate("create_door")
    assert rate == pytest.approx(2.0 / 3.0)


def test_get_parameter_ranges_successful_only(skill_memory):
    """Test parameter range extraction for successful executions."""
    skill_memory.record_execution(
        SkillExecution(
            skill_id="create_wall",
            parameters={"height": 2700},
            success=True,
        )
    )
    skill_memory.record_execution(
        SkillExecution(
            skill_id="create_wall",
            parameters={"height": 3000},
            success=True,
        )
    )
    skill_memory.record_execution(
        SkillExecution(
            skill_id="create_wall",
            parameters={"height": 3200},
            success=True,
        )
    )

    ranges = skill_memory.get_parameter_ranges("create_wall", "height")
    assert ranges["successful_range"] == (2700, 3200)
    assert ranges["failed_range"] is None


def test_get_parameter_ranges_with_failures(skill_memory):
    """Test parameter range extraction including failures."""
    skill_memory.record_execution(
        SkillExecution(
            skill_id="create_wall",
            parameters={"thickness": 200},
            success=True,
        )
    )
    skill_memory.record_execution(
        SkillExecution(
            skill_id="create_wall",
            parameters={"thickness": 100},
            success=False,
        )
    )

    ranges = skill_memory.get_parameter_ranges("create_wall", "thickness")
    assert ranges["successful_range"] == (200, 200)
    assert ranges["failed_range"] == (100, 100)


def test_query_similar_finds_matches(skill_memory):
    """Test querying similar executions by skill and parameters."""
    skill_memory.record_execution(
        SkillExecution(
            skill_id="create_wall",
            parameters={"height": 3000, "thickness": 200},
            success=True,
        )
    )
    skill_memory.record_execution(
        SkillExecution(
            skill_id="create_wall",
            parameters={"height": 3000, "thickness": 250},
            success=True,
        )
    )
    skill_memory.record_execution(
        SkillExecution(
            skill_id="create_door",
            parameters={"width": 900},
            success=True,
        )
    )

    similar = skill_memory.query_similar("create_wall", {"height": 3000}, limit=5)
    assert len(similar) == 2
    assert all(e.skill_id == "create_wall" for e in similar)


def test_get_executions_filters_by_skill(skill_memory):
    """Test filtering executions by skill_id."""
    skill_memory.record_execution(
        SkillExecution(skill_id="create_wall", parameters={}, success=True)
    )
    skill_memory.record_execution(
        SkillExecution(skill_id="create_door", parameters={}, success=True)
    )

    wall_execs = skill_memory.get_executions(skill_id="create_wall")
    assert len(wall_execs) == 1
    assert wall_execs[0].skill_id == "create_wall"


def test_get_executions_filters_by_success(skill_memory):
    """Test filtering executions by success status."""
    skill_memory.record_execution(
        SkillExecution(skill_id="create_wall", parameters={}, success=True)
    )
    skill_memory.record_execution(
        SkillExecution(skill_id="create_wall", parameters={}, success=False)
    )

    successful = skill_memory.get_executions(success_only=True)
    assert len(successful) == 1
    assert successful[0].success is True


def test_clear_removes_all_history(skill_memory):
    """Test clearing local history."""
    skill_memory.record_execution(
        SkillExecution(skill_id="create_wall", parameters={}, success=True)
    )
    assert len(skill_memory._local_history) == 1

    skill_memory.clear()
    assert len(skill_memory._local_history) == 0
