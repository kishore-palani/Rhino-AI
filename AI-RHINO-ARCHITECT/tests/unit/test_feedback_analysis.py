"""
Unit tests for feedback_analysis module.
"""

from __future__ import annotations

import pytest

from ai.memory.feedback_analysis import FeedbackAnalyzer


@pytest.fixture
def analyzer():
    """Create a fresh FeedbackAnalyzer instance."""
    an = FeedbackAnalyzer()
    an.clear()
    return an


def test_classify_dimensional_feedback(analyzer):
    """Test classifying dimensional feedback."""
    record = analyzer.parse_feedback(
        original_request="Create a 5m wall",
        user_feedback="Make the wall 3m taller and 250mm thick",
    )
    assert record.feedback_type == "dimensional"
    assert "wall" in record.affected_elements
    assert record.extracted_corrections.get("dimension_m") == [3.0]
    assert record.extracted_corrections.get("dimension_mm") == [250.0]


def test_classify_functional_feedback(analyzer):
    """Test classifying functional/layout feedback."""
    record = analyzer.parse_feedback(
        original_request="Create a 2-room house",
        user_feedback="The bedroom should not open directly to the entrance for privacy",
    )
    assert record.feedback_type == "functional"
    assert "entrance" in record.affected_elements


def test_classify_stylistic_feedback(analyzer):
    """Test classifying stylistic feedback."""
    record = analyzer.parse_feedback(
        original_request="Create a facade",
        user_feedback="The facade is too heavy and aggressive, make the panels more subtle",
    )
    assert record.feedback_type == "stylistic"
    assert "facade" in record.affected_elements


def test_classify_structural_feedback(analyzer):
    """Test classifying structural feedback."""
    record = analyzer.parse_feedback(
        original_request="Create a room",
        user_feedback="Add a structural column in the center to support the beam",
    )
    assert record.feedback_type == "structural"
    assert "column" in record.affected_elements
    assert "beam" in record.affected_elements


def test_extract_relative_modifications(analyzer):
    """Test extracting relative direction adjustments (wider, taller, thinner)."""
    record = analyzer.parse_feedback(
        original_request="Create a wall",
        user_feedback="Make it wider and thinner",
    )
    assert record.extracted_corrections.get("relative_width") == "increase"
    assert record.extracted_corrections.get("relative_thickness") == "decrease"


def test_get_records_filters_by_type(analyzer):
    """Test filtering feedback records by feedback_type."""
    analyzer.parse_feedback("req1", "make it 2.7m taller")
    analyzer.parse_feedback("req2", "needs more privacy from entrance")

    dim_records = analyzer.get_records(feedback_type="dimensional")
    assert len(dim_records) == 1
    assert dim_records[0].feedback_type == "dimensional"


def test_get_records_filters_by_element(analyzer):
    """Test filtering feedback records by affected element."""
    analyzer.parse_feedback("req1", "the window is too small")
    analyzer.parse_feedback("req2", "the door is too narrow")

    window_records = analyzer.get_records(element="window")
    assert len(window_records) == 1
    assert "window" in window_records[0].affected_elements


def test_clear_removes_feedback(analyzer):
    """Test clearing feedback records."""
    analyzer.parse_feedback("r", "f")
    assert len(analyzer._feedback_records) == 1

    analyzer.clear()
    assert len(analyzer._feedback_records) == 0
