"""
Unit tests for memory_query module.
"""

from __future__ import annotations

import pytest

from ai.memory.failure_patterns import FailurePatternRecognizer
from ai.memory.feedback_analysis import FeedbackAnalyzer
from ai.memory.query import MemoryQuery
from ai.memory.skill_memory import SkillExecution, SkillMemory


@pytest.fixture
def memory_query():
    """Create MemoryQuery instance with isolated subsystems."""
    skill_mem = SkillMemory()
    pattern_rec = FailurePatternRecognizer()
    feedback_an = FeedbackAnalyzer()

    skill_mem.clear()
    pattern_rec.clear()
    feedback_an.clear()

    return MemoryQuery(
        skill_memory=skill_mem,
        pattern_recognizer=pattern_rec,
        feedback_analyzer=feedback_an,
    )


def test_query_before_plan_aggregates_patterns(memory_query):
    """Test query_before_plan retrieves known recurring patterns."""
    # Seed recurring pattern
    memory_query.pattern_recognizer.record_failure(
        task="create_wall",
        error="thickness below minimum",
        failure_type="dimensional",
        suggested_fix="Use min 200mm thickness",
    )
    memory_query.pattern_recognizer.record_failure(
        task="create_wall",
        error="thickness below minimum",
        failure_type="dimensional",
    )

    insights = memory_query.query_before_plan("create a residential wall")
    assert len(insights.known_patterns) == 1
    assert "Use min 200mm thickness" in insights.suggestions


def test_query_before_skill_execution_valid_params(memory_query):
    """Test query_before_skill_execution when parameters are within successful range."""
    # Seed successful executions
    memory_query.skill_memory.record_execution(
        SkillExecution(
            skill_id="create_wall",
            parameters={"thickness": 200, "height": 3000},
            success=True,
        )
    )
    memory_query.skill_memory.record_execution(
        SkillExecution(
            skill_id="create_wall",
            parameters={"thickness": 250, "height": 3200},
            success=True,
        )
    )

    insights = memory_query.query_before_skill_execution(
        "create_wall", {"thickness": 220, "height": 3100}
    )
    assert insights.success_rate == 1.0
    assert len(insights.warnings) == 0


def test_query_before_skill_execution_out_of_range(memory_query):
    """Test query_before_skill_execution detects parameters outside proven range."""
    memory_query.skill_memory.record_execution(
        SkillExecution(
            skill_id="create_wall",
            parameters={"thickness": 200},
            success=True,
        )
    )

    insights = memory_query.query_before_skill_execution(
        "create_wall", {"thickness": 50}
    )
    assert len(insights.warnings) == 1
    assert "outside successful range" in insights.warnings[0]


def test_query_for_correction_finds_pattern_fix(memory_query):
    """Test query_for_correction retrieves pattern-based recommendations."""
    memory_query.pattern_recognizer.record_failure(
        task="create_room",
        error="open solid",
        failure_type="geometry",
        suggested_fix="Cap boundary curve before extrusion",
    )

    suggestions = memory_query.query_for_correction(
        task="create_room",
        error="open solid",
        failure_type="geometry",
    )
    assert "Cap boundary curve before extrusion" in suggestions.pattern_based_fixes
    assert "Cap boundary curve before extrusion" in suggestions.recommendations
