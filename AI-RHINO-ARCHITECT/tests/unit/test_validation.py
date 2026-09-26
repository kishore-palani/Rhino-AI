"""Unit tests for the validation module."""

from __future__ import annotations

import pytest

from ai.validation.models import (
    CorrectionResult,
    CorrectionStrategy,
    ValidationCategory,
    ValidationIssue,
    ValidationResult,
    ValidationRule,
    ValidationRuleSet,
    ValidationSeverity,
    ValidationStatus,
)
from ai.validation.pipeline import ValidationFeedback


class TestValidationModels:
    """Tests for validation data models."""

    def test_validation_issue_creation(self) -> None:
        """Test creating a validation issue."""
        issue = ValidationIssue(
            rule_id="test_rule",
            category=ValidationCategory.GEOMETRY,
            severity=ValidationSeverity.ERROR,
            message="Test issue",
            element_id="guid-123",
            element_type="wall",
            expected=True,
            actual=False,
        )
        assert issue.rule_id == "test_rule"
        assert issue.severity == ValidationSeverity.ERROR
        assert issue.element_id == "guid-123"

    def test_validation_issue_to_dict(self) -> None:
        """Test validation issue serialization."""
        issue = ValidationIssue(
            rule_id="test_rule",
            category=ValidationCategory.GEOMETRY,
            severity=ValidationSeverity.ERROR,
            message="Test issue",
        )
        d = issue.to_dict()
        assert d["rule_id"] == "test_rule"
        assert d["category"] == "geometry"
        assert d["severity"] == "error"

    def test_validation_result_creation(self) -> None:
        """Test creating a validation result."""
        result = ValidationResult(
            validation_id="val_1",
            model_id="model_1",
        )
        assert result.validation_id == "val_1"
        assert result.status == ValidationStatus.PENDING

    def test_validation_result_add_issue(self) -> None:
        """Test adding issues to validation result."""
        result = ValidationResult(validation_id="val_1")
        issue = ValidationIssue(
            rule_id="rule_1",
            category=ValidationCategory.GEOMETRY,
            severity=ValidationSeverity.ERROR,
            message="Error issue",
        )
        result.add_issue(issue)
        assert result.failed_count == 1
        assert result.has_errors()

        warning = ValidationIssue(
            rule_id="rule_2",
            category=ValidationCategory.DIMENSIONAL,
            severity=ValidationSeverity.WARNING,
            message="Warning issue",
        )
        result.add_issue(warning)
        assert result.warning_count == 1
        assert result.has_warnings()

    def test_validation_result_get_issues_by_category(self) -> None:
        """Test filtering issues by category."""
        result = ValidationResult(validation_id="val_1")
        result.add_issue(ValidationIssue(
            rule_id="r1", category=ValidationCategory.GEOMETRY,
            severity=ValidationSeverity.ERROR, message="Geom error"
        ))
        result.add_issue(ValidationIssue(
            rule_id="r2", category=ValidationCategory.DIMENSIONAL,
            severity=ValidationSeverity.WARNING, message="Dim warning"
        ))
        result.add_issue(ValidationIssue(
            rule_id="r3", category=ValidationCategory.GEOMETRY,
            severity=ValidationSeverity.INFO, message="Geom info"
        ))

        geom_issues = result.get_issues_by_category(ValidationCategory.GEOMETRY)
        assert len(geom_issues) == 2

        dim_issues = result.get_issues_by_category(ValidationCategory.DIMENSIONAL)
        assert len(dim_issues) == 1

    def test_validation_result_get_issues_by_severity(self) -> None:
        """Test filtering issues by severity."""
        result = ValidationResult(validation_id="val_1")
        result.add_issue(ValidationIssue(
            rule_id="r1", category=ValidationCategory.GEOMETRY,
            severity=ValidationSeverity.ERROR, message="Error"
        ))
        result.add_issue(ValidationIssue(
            rule_id="r2", category=ValidationCategory.DIMENSIONAL,
            severity=ValidationSeverity.WARNING, message="Warning"
        ))
        result.add_issue(ValidationIssue(
            rule_id="r3", category=ValidationCategory.REGULATORY,
            severity=ValidationSeverity.CRITICAL, message="Critical"
        ))

        errors = result.get_issues_by_severity(ValidationSeverity.ERROR)
        assert len(errors) == 1

        critical = result.get_issues_by_severity(ValidationSeverity.CRITICAL)
        assert len(critical) == 1

    def test_validation_rule_creation(self) -> None:
        """Test creating a validation rule."""
        rule = ValidationRule(
            rule_id="test_rule",
            name="Test Rule",
            description="Test description",
            category=ValidationCategory.GEOMETRY,
            severity=ValidationSeverity.ERROR,
            applies_to=["wall", "floor"],
            parameters={"tolerance": 0.01},
        )
        assert rule.rule_id == "test_rule"
        assert rule.matches_element("wall")
        assert rule.matches_element("floor")
        assert not rule.matches_element("door")

    def test_validation_rule_matches_element(self) -> None:
        """Test rule element matching."""
        rule_all = ValidationRule(
            rule_id="r1", name="R1", description="D", category=ValidationCategory.GEOMETRY,
            applies_to=[],
        )
        assert rule_all.matches_element("anything")

        rule_specific = ValidationRule(
            rule_id="r2", name="R2", description="D", category=ValidationCategory.GEOMETRY,
            applies_to=["wall", "floor"],
        )
        assert rule_specific.matches_element("wall")
        assert not rule_specific.matches_element("door")

    def test_correction_strategy_creation(self) -> None:
        """Test creating a correction strategy."""
        strategy = CorrectionStrategy(
            strategy_id="fix_test",
            rule_id="test_rule",
            name="Fix Test",
            description="Fix description",
            auto_applicable=True,
            risk_level="low",
        )
        assert strategy.strategy_id == "fix_test"
        assert strategy.auto_applicable

    def test_correction_result_creation(self) -> None:
        """Test creating a correction result."""
        issue = ValidationIssue(
            rule_id="r1", category=ValidationCategory.GEOMETRY,
            severity=ValidationSeverity.ERROR, message="Error"
        )
        result = CorrectionResult(
            strategy_id="fix_r1",
            issue=issue,
            success=True,
            message="Fixed",
            modified_elements=["guid-1", "guid-2"],
        )
        assert result.success
        assert len(result.modified_elements) == 2

    def test_validation_rule_set(self) -> None:
        """Test validation rule set."""
        rule1 = ValidationRule(
            rule_id="r1", name="R1", description="D", category=ValidationCategory.GEOMETRY,
        )
        rule2 = ValidationRule(
            rule_id="r2", name="R2", description="D", category=ValidationCategory.DIMENSIONAL,
            enabled=False,
        )
        strategy = CorrectionStrategy(
            strategy_id="s1", rule_id="r1", name="S1", description="D",
        )

        ruleset = ValidationRuleSet(
            ruleset_id="rs1",
            name="Test Ruleset",
            description="Test",
            version="1.0",
            rules=[rule1, rule2],
            strategies=[strategy],
        )

        enabled = ruleset.get_enabled_rules()
        assert len(enabled) == 1
        assert enabled[0].rule_id == "r1"

        geom_rules = ruleset.get_enabled_rules(ValidationCategory.GEOMETRY)
        assert len(geom_rules) == 1

        strat = ruleset.get_strategy_for_rule("r1")
        assert strat is not None
        assert strat.strategy_id == "s1"

        strat_none = ruleset.get_strategy_for_rule("r2")
        assert strat_none is None


class TestValidationFeedback:
    """Tests for validation feedback generation."""

    def test_generate_feedback_passed(self) -> None:
        """Test feedback for passed validation."""
        from ai.validation.pipeline import PipelineResult
        from ai.validation.models import ValidationResult

        geom_result = ValidationResult(validation_id="v1")
        geom_result.status = ValidationStatus.PASSED

        pipeline = PipelineResult(
            pipeline_id="p1",
            geometry_result=geom_result,
            success=True,
        )

        feedback = ValidationFeedback.generate_feedback(pipeline)
        assert feedback["validation_passed"]
        assert feedback["total_issues"] == 0
        assert not feedback["replan_required"]

    def test_generate_feedback_failed(self) -> None:
        """Test feedback for failed validation."""
        from ai.validation.pipeline import PipelineResult
        from ai.validation.models import ValidationResult

        geom_result = ValidationResult(validation_id="v1")
        geom_result.add_issue(ValidationIssue(
            rule_id="r1", category=ValidationCategory.GEOMETRY,
            severity=ValidationSeverity.ERROR, message="Error",
            element_id="guid-1", element_type="wall",
        ))
        geom_result.add_issue(ValidationIssue(
            rule_id="r2", category=ValidationCategory.DIMENSIONAL,
            severity=ValidationSeverity.WARNING, message="Warning",
        ))
        geom_result.status = ValidationStatus.FAILED

        pipeline = PipelineResult(
            pipeline_id="p1",
            geometry_result=geom_result,
            success=False,
        )

        feedback = ValidationFeedback.generate_feedback(pipeline)
        assert not feedback["validation_passed"]
        assert feedback["total_issues"] == 2
        assert len(feedback["errors"]) == 1
        assert len(feedback["warnings"]) == 1
        assert feedback["replan_required"]
        assert "geometry" in feedback["by_category"]

    def test_format_for_llm(self) -> None:
        """Test formatting validation results for LLM."""
        from ai.validation.pipeline import PipelineResult
        from ai.validation.models import ValidationResult

        geom_result = ValidationResult(validation_id="v1")
        geom_result.add_issue(ValidationIssue(
            rule_id="geom_closed_solid", category=ValidationCategory.GEOMETRY,
            severity=ValidationSeverity.ERROR, message="Not a closed solid",
            element_id="guid-1", element_type="wall",
            expected=True, actual=False,
        ))
        geom_result.status = ValidationStatus.FAILED

        pipeline = PipelineResult(
            pipeline_id="p1",
            geometry_result=geom_result,
            success=False,
        )

        formatted = ValidationFeedback.format_for_llm(pipeline)
        assert "FAILED" in formatted
        assert "geom_closed_solid" in formatted
        assert "Not a closed solid" in formatted
        assert "guid-1" in formatted
        assert "Expected: True, Actual: False" in formatted


class TestBuiltInRules:
    """Tests for built-in validation rules."""

    def test_geometry_rules_exist(self) -> None:
        """Test that geometry rules are defined."""
        from ai.validation.geometry import GEOMETRY_RULES
        assert len(GEOMETRY_RULES) >= 6
        rule_ids = {r.rule_id for r in GEOMETRY_RULES}
        assert "geom_closed_solid" in rule_ids
        assert "geom_manifold" in rule_ids
        assert "geom_valid_brep" in rule_ids

    def test_dimensional_rules_exist(self) -> None:
        """Test that dimensional rules are defined."""
        from ai.validation.dimensional import DIMENSIONAL_RULES
        assert len(DIMENSIONAL_RULES) >= 10
        rule_ids = {r.rule_id for r in DIMENSIONAL_RULES}
        assert "dim_wall_height" in rule_ids
        assert "dim_wall_thickness" in rule_ids
        assert "dim_door_clearance" in rule_ids

    def test_regulatory_rules_exist(self) -> None:
        """Test that regulatory rules are defined."""
        from ai.validation.regulatory import REGULATORY_RULES
        assert len(REGULATORY_RULES) >= 10
        rule_ids = {r.rule_id for r in REGULATORY_RULES}
        assert "reg_ibc_fire_resistance" in rule_ids
        assert "reg_ibc_means_of_egress" in rule_ids
        assert "reg_ibc_accessibility" in rule_ids

    def test_geometry_strategies_exist(self) -> None:
        """Test that geometry correction strategies are defined."""
        from ai.validation.geometry import GEOMETRY_STRATEGIES
        assert len(GEOMETRY_STRATEGIES) >= 4
        strategy_ids = {s.strategy_id for s in GEOMETRY_STRATEGIES}
        assert "fix_cap_brep" in strategy_ids
        assert "fix_join_surfaces" in strategy_ids

    def test_dimensional_strategies_exist(self) -> None:
        """Test that dimensional correction strategies are defined."""
        from ai.validation.dimensional import DIMENSIONAL_STRATEGIES
        assert len(DIMENSIONAL_STRATEGIES) >= 5
        strategy_ids = {s.strategy_id for s in DIMENSIONAL_STRATEGIES}
        assert "fix_wall_height" in strategy_ids
        assert "fix_wall_thickness" in strategy_ids

    def test_regulatory_strategies_exist(self) -> None:
        """Test that regulatory correction strategies are defined."""
        from ai.validation.regulatory import REGULATORY_STRATEGIES
        assert len(REGULATORY_STRATEGIES) >= 5
        strategy_ids = {s.strategy_id for s in REGULATORY_STRATEGIES}
        assert "fix_fire_rating" in strategy_ids
        assert "fix_egress_width" in strategy_ids


class TestPipelineResult:
    """Tests for pipeline result."""

    def test_pipeline_result_creation(self) -> None:
        """Test creating a pipeline result."""
        from ai.validation.pipeline import PipelineResult

        result = PipelineResult(pipeline_id="p1", model_id="m1")
        assert result.pipeline_id == "p1"
        assert result.model_id == "m1"
        assert not result.success

    def test_pipeline_result_has_errors(self) -> None:
        """Test checking for errors in pipeline result."""
        from ai.validation.pipeline import PipelineResult
        from ai.validation.models import ValidationResult

        geom = ValidationResult(validation_id="v1")
        geom.add_issue(ValidationIssue(
            rule_id="r1", category=ValidationCategory.GEOMETRY,
            severity=ValidationSeverity.ERROR, message="Error",
        ))
        geom.status = ValidationStatus.FAILED

        pipeline = PipelineResult(pipeline_id="p1", geometry_result=geom)
        assert pipeline.has_errors()

    def test_pipeline_result_get_all_issues(self) -> None:
        """Test getting all issues from pipeline."""
        from ai.validation.pipeline import PipelineResult
        from ai.validation.models import ValidationResult

        geom = ValidationResult(validation_id="v1")
        geom.add_issue(ValidationIssue(
            rule_id="r1", category=ValidationCategory.GEOMETRY,
            severity=ValidationSeverity.ERROR, message="Geom error",
        ))

        dim = ValidationResult(validation_id="v2")
        dim.add_issue(ValidationIssue(
            rule_id="r2", category=ValidationCategory.DIMENSIONAL,
            severity=ValidationSeverity.WARNING, message="Dim warning",
        ))

        pipeline = PipelineResult(
            pipeline_id="p1",
            geometry_result=geom,
            dimensional_result=dim,
        )

        all_issues = pipeline.get_all_issues()
        assert len(all_issues) == 2

    def test_pipeline_result_to_dict(self) -> None:
        """Test pipeline result serialization."""
        from ai.validation.pipeline import PipelineResult
        from ai.validation.models import ValidationResult

        geom = ValidationResult(validation_id="v1")
        geom.add_issue(ValidationIssue(
            rule_id="r1", category=ValidationCategory.GEOMETRY,
            severity=ValidationSeverity.ERROR, message="Error",
        ))

        pipeline = PipelineResult(
            pipeline_id="p1",
            geometry_result=geom,
            success=False,
        )

        d = pipeline.to_dict()
        assert d["pipeline_id"] == "p1"
        assert d["success"] is False
        assert d["geometry_result"] is not None
        assert len(d["combined_issues"]) == 1