"""
Unified memory query interface for AI RHINO ARCHITECT.

Aggregates insights from skill memory, failure patterns, feedback analysis,
and AgentMemory to provide actionable recommendations for planning and execution.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from ai.memory.agentmemory_client import AgentMemoryClient, get_client
from ai.memory.failure_patterns import (
    FailurePattern,
    FailurePatternRecognizer,
    get_failure_pattern_recognizer,
)
from ai.memory.feedback_analysis import (
    FeedbackAnalyzer,
    FeedbackRecord,
    get_feedback_analyzer,
)
from ai.memory.skill_memory import SkillExecution, SkillMemory, get_skill_memory

logger = logging.getLogger(__name__)


@dataclass
class MemoryInsights:
    """Aggregated memory insights for planning and execution decisions."""

    relevant_failures: List[Dict[str, Any]] = field(default_factory=list)
    known_patterns: List[FailurePattern] = field(default_factory=list)
    user_preferences: Dict[str, Any] = field(default_factory=dict)
    successful_examples: List[SkillExecution] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    suggestions: List[str] = field(default_factory=list)


@dataclass
class SkillInsights:
    """Execution-specific insights for a particular skill."""

    skill_id: str
    success_rate: float
    known_failure_modes: List[str] = field(default_factory=list)
    suggested_parameter_ranges: Dict[str, Any] = field(default_factory=dict)
    warnings: List[str] = field(default_factory=list)


@dataclass
class CorrectionSuggestions:
    """Correction recommendations for a failure scenario."""

    similar_failures: List[Dict[str, Any]] = field(default_factory=list)
    pattern_based_fixes: List[str] = field(default_factory=list)
    related_feedback: List[FeedbackRecord] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)


class MemoryQuery:
    """Unified interface for querying all memory subsystems."""

    def __init__(
        self,
        skill_memory: Optional[SkillMemory] = None,
        pattern_recognizer: Optional[FailurePatternRecognizer] = None,
        feedback_analyzer: Optional[FeedbackAnalyzer] = None,
        agentmemory_client: Optional[AgentMemoryClient] = None,
    ) -> None:
        self.skill_memory = skill_memory or get_skill_memory()
        self.pattern_recognizer = pattern_recognizer or get_failure_pattern_recognizer()
        self.feedback_analyzer = feedback_analyzer or get_feedback_analyzer()
        self.agentmemory = agentmemory_client or get_client()

    def query_before_plan(
        self, task: str, context: Optional[Dict[str, Any]] = None
    ) -> MemoryInsights:
        """
        Aggregate all relevant memories before generating a modeling plan.

        Returns insights on similar past failures, known patterns to avoid,
        user preferences from feedback, and successful approaches.
        """
        ctx = context or {}
        insights = MemoryInsights()

        # 1. Query similar past failures
        try:
            failure_results = self.agentmemory.recall(query=f"failure {task}", limit=5)
            if failure_results.get("success"):
                insights.relevant_failures = failure_results.get("memories", [])
        except Exception as exc:
            logger.debug("AgentMemory query failed: %s", exc)

        # 2. Check known failure patterns
        patterns = self.pattern_recognizer.get_patterns(min_occurrences=2)
        insights.known_patterns = patterns
        for p in patterns:
            if p.suggested_fix:
                insights.warnings.append(
                    f"Known pattern: {p.description} (occurs {p.occurrences}x)"
                )
                insights.suggestions.append(p.suggested_fix)

        # 3. Extract user preferences from feedback
        feedback_records = self.feedback_analyzer.get_records()
        dimensional_prefs: Dict[str, List[float]] = {}
        for fb in feedback_records:
            if fb.feedback_type == "dimensional" and fb.extracted_corrections:
                for key, val in fb.extracted_corrections.items():
                    if isinstance(val, list):
                        dimensional_prefs.setdefault(key, []).extend(val)
        insights.user_preferences = dimensional_prefs

        # 4. Retrieve successful examples from skill memory
        # (only if specific skills mentioned in context)
        if "skills" in ctx:
            for skill_id in ctx["skills"]:
                successes = self.skill_memory.get_executions(
                    skill_id=skill_id, success_only=True
                )
                insights.successful_examples.extend(successes[:3])

        return insights

    def query_before_skill_execution(
        self, skill_id: str, parameters: Dict[str, Any]
    ) -> SkillInsights:
        """
        Retrieve execution-specific insights for a modeling skill.

        Returns success rate, known failure modes, and suggested parameter ranges.
        """
        success_rate = self.skill_memory.get_success_rate(skill_id)
        insights = SkillInsights(skill_id=skill_id, success_rate=success_rate)

        # Check parameter validity against historical ranges
        for param_name, param_value in parameters.items():
            if not isinstance(param_value, (int, float)):
                continue
            ranges = self.skill_memory.get_parameter_ranges(skill_id, param_name)
            if ranges["successful_range"]:
                success_min, success_max = ranges["successful_range"]
                if not (success_min <= param_value <= success_max):
                    insights.warnings.append(
                        f"Parameter '{param_name}' = {param_value} is outside "
                        f"successful range [{success_min}, {success_max}]"
                    )
                    insights.suggested_parameter_ranges[param_name] = ranges[
                        "successful_range"
                    ]

        # Check if this skill has known failure patterns
        patterns = self.pattern_recognizer.get_patterns()
        skill_patterns = [
            p
            for p in patterns
            if skill_id in p.common_attributes.get("task", "").lower()
        ]
        insights.known_failure_modes = [p.description for p in skill_patterns]

        return insights

    def query_for_correction(
        self, task: str, error: str, failure_type: str, context: Optional[Dict[str, Any]] = None
    ) -> CorrectionSuggestions:
        """
        Provide correction suggestions for a failure scenario.

        Returns similar past failures, pattern-based fixes, and related user feedback.
        """
        ctx = context or {}
        suggestions = CorrectionSuggestions()

        # 1. Query similar failures from AgentMemory
        try:
            results = self.agentmemory.recall(query=f"failure {task} {error}", limit=3)
            if results.get("success"):
                suggestions.similar_failures = results.get("memories", [])
        except Exception as exc:
            logger.debug("AgentMemory query failed: %s", exc)

        # 2. Pattern-based fixes
        pattern_fix = self.pattern_recognizer.suggest_correction_for(
            task, failure_type, error
        )
        if pattern_fix:
            suggestions.pattern_based_fixes.append(pattern_fix)

        # 3. Related user feedback
        feedback = self.feedback_analyzer.get_records(feedback_type=failure_type)
        suggestions.related_feedback = feedback[:3]

        # 4. Synthesize recommendations
        if suggestions.pattern_based_fixes:
            suggestions.recommendations.extend(suggestions.pattern_based_fixes)
        if suggestions.similar_failures:
            suggestions.recommendations.append(
                f"Found {len(suggestions.similar_failures)} similar past failures - "
                "consider alternative approach."
            )

        return suggestions


# Module-level singleton
_memory_query: Optional[MemoryQuery] = None


def get_memory_query() -> MemoryQuery:
    """Return shared process-wide MemoryQuery instance."""
    global _memory_query
    if _memory_query is None:
        _memory_query = MemoryQuery()
    return _memory_query
