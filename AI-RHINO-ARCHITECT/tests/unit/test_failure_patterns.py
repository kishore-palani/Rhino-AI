"""
Unit tests for failure_patterns module.
"""

from __future__ import annotations

import pytest

from ai.memory.failure_patterns import FailurePatternRecognizer


@pytest.fixture
def recognizer():
    """Create a fresh FailurePatternRecognizer instance."""
    rec = FailurePatternRecognizer()
    rec.clear()
    return rec


def test_record_single_failure_creates_pattern(recognizer):
    """Test recording a single failure creates a pattern."""
    pattern = recognizer.record_failure(
        task="create_wall",
        error="Wall thickness 100mm is below minimum 150mm",
        failure_type="dimensional",
    )
    assert pattern is not None
    assert pattern.occurrences == 1
    assert pattern.failure_type == "dimensional"
    assert "thickness" in pattern.description.lower()


def test_record_duplicate_failure_increments_occurrence(recognizer):
    """Test recording identical failure increments count and increases confidence."""
    p1 = recognizer.record_failure(
        task="create_wall",
        error="Wall thickness below minimum",
        failure_type="dimensional",
    )
    initial_confidence = p1.confidence

    p2 = recognizer.record_failure(
        task="create_wall",
        error="Wall thickness below minimum",
        failure_type="dimensional",
    )
    assert p2.occurrences == 2
    assert p2.confidence > initial_confidence


def test_deduce_fix_dimensional_wall():
    """Test auto-deduction of fixes for dimensional wall failure."""
    rec = FailurePatternRecognizer()
    fix = rec._deduce_fix(
        failure_type="dimensional",
        error="Wall thickness is too thin",
        context={},
    )
    assert fix is not None
    assert "150mm" in fix


def test_deduce_fix_geometry_solid():
    """Test auto-deduction of fixes for open solid failure."""
    rec = FailurePatternRecognizer()
    fix = rec._deduce_fix(
        failure_type="geometry",
        error="Brep is not a closed solid, has naked edges",
        context={},
    )
    assert fix is not None
    assert "closed" in fix.lower()


def test_suggest_correction_for_known_pattern(recognizer):
    """Test suggesting correction for a known failure pattern."""
    recognizer.record_failure(
        task="create_wall",
        error="Wall thickness below minimum",
        failure_type="dimensional",
        suggested_fix="Increase wall thickness to 200mm.",
    )

    suggestion = recognizer.suggest_correction_for(
        task="create_wall",
        failure_type="dimensional",
        error="Wall thickness below minimum",
    )
    assert suggestion == "Increase wall thickness to 200mm."


def test_get_patterns_filters_by_type(recognizer):
    """Test filtering patterns by failure type."""
    recognizer.record_failure(
        task="wall", error="thin", failure_type="dimensional"
    )
    recognizer.record_failure(
        task="brep", error="open", failure_type="geometry"
    )

    dim_patterns = recognizer.get_patterns(failure_type="dimensional")
    assert len(dim_patterns) == 1
    assert dim_patterns[0].failure_type == "dimensional"


def test_get_patterns_filters_by_min_occurrences(recognizer):
    """Test filtering patterns by minimum occurrence frequency."""
    recognizer.record_failure(task="task1", error="err", failure_type="gen")
    recognizer.record_failure(task="task2", error="err", failure_type="gen")
    recognizer.record_failure(task="task2", error="err", failure_type="gen")

    frequent = recognizer.get_patterns(min_occurrences=2)
    assert len(frequent) == 1
    assert frequent[0].occurrences == 2


def test_clear_removes_patterns(recognizer):
    """Test clearing patterns."""
    recognizer.record_failure(task="t", error="e", failure_type="f")
    assert len(recognizer._patterns) == 1

    recognizer.clear()
    assert len(recognizer._patterns) == 0
