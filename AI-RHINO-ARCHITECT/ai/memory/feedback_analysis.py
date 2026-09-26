"""
Feedback analysis and structured correction module for AI RHINO ARCHITECT.

Parses natural-language user feedback, classifies correction categories,
extracts target parameters and entities, and maintains feedback memories.
"""

from __future__ import annotations

import logging
import re
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from ai.memory.agentmemory_client import AgentMemoryClient, get_client

logger = logging.getLogger(__name__)


@dataclass
class FeedbackRecord:
    """Structured representation of a user feedback event."""

    feedback_id: str
    original_request: str
    user_feedback: str
    feedback_type: str  # "dimensional", "stylistic", "functional", "structural", "general"
    extracted_corrections: Dict[str, Any] = field(default_factory=dict)
    affected_elements: List[str] = field(default_factory=list)
    action_taken: Optional[str] = None
    timestamp: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class FeedbackAnalyzer:
    """Analyzes and categorizes natural language feedback from users."""

    def __init__(self, client: Optional[AgentMemoryClient] = None) -> None:
        self.client = client or get_client()
        self._feedback_records: List[FeedbackRecord] = []

    def parse_feedback(
        self,
        original_request: str,
        user_feedback: str,
        action_taken: Optional[str] = None,
    ) -> FeedbackRecord:
        """Parse natural-language feedback into a structured FeedbackRecord."""
        feedback_type = self._classify_feedback_type(user_feedback)
        extracted = self._extract_parameters(user_feedback)
        affected = self._extract_affected_elements(user_feedback)

        record_id = f"fb_{len(self._feedback_records) + 1}_{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}"

        record = FeedbackRecord(
            feedback_id=record_id,
            original_request=original_request,
            user_feedback=user_feedback,
            feedback_type=feedback_type,
            extracted_corrections=extracted,
            affected_elements=affected,
            action_taken=action_taken,
        )

        self._feedback_records.append(record)
        self._persist_feedback(record)
        return record

    def _classify_feedback_type(self, text: str) -> str:
        """Categorize feedback by architectural domain."""
        t = text.lower()

        # Check structural first (most specific)
        if any(w in t for w in ["column", "beam", "load", "support", "foundation", "cantilever", "structural"]):
            return "structural"

        # Check functional (privacy, layout, circulation)
        if any(w in t for w in ["privacy", "separate", "connect", "access", "adjacent", "layout", "circulation"]):
            return "functional"

        # Check stylistic
        if any(w in t for w in ["heavy", "light", "modern", "subtle", "aggressive", "style", "look", "panels"]):
            return "stylistic"

        # Check dimensional (use more specific patterns to avoid false positives)
        if any(w in t for w in ["taller", "shorter", "wider", "narrower", "thicker", "thinner", "dimension", "size"]):
            return "dimensional"
        # Only match explicit dimensional values (numbers with units)
        if re.search(r'\d+(?:\.\d+)?\s*(?:mm|m\b|meter|millimeter)', t):
            return "dimensional"
        if any(w in t for w in ["height", "width", "depth", "thickness"]):
            return "dimensional"

        return "general"

    def _extract_parameters(self, text: str) -> Dict[str, Any]:
        """Extract explicit numeric or relative parameter modifications."""
        corrections: Dict[str, Any] = {}
        t = text.lower()

        # Dimension extraction (e.g. 2.7m, 200mm, 5000mm, 3m)
        m_matches = re.findall(r"(\d+(?:\.\d+)?)\s*(?:m|meters|meter)\b", t)
        if m_matches:
            corrections["dimension_m"] = [float(x) for x in m_matches]

        mm_matches = re.findall(r"(\d+(?:\.\d+)?)\s*(?:mm|millimeters)\b", t)
        if mm_matches:
            corrections["dimension_mm"] = [float(x) for x in mm_matches]

        # Relative directions
        if "make it wider" in t or "wider" in t:
            corrections["relative_width"] = "increase"
        elif "make it narrower" in t or "narrower" in t:
            corrections["relative_width"] = "decrease"

        if "make it taller" in t or "taller" in t or "higher" in t:
            corrections["relative_height"] = "increase"
        elif "make it shorter" in t or "shorter" in t or "lower" in t:
            corrections["relative_height"] = "decrease"

        if "thicker" in t:
            corrections["relative_thickness"] = "increase"
        elif "thinner" in t:
            corrections["relative_thickness"] = "decrease"

        return corrections

    def _extract_affected_elements(self, text: str) -> List[str]:
        """Identify which architectural elements the feedback targets."""
        t = text.lower()
        elements = []
        candidates = [
            "wall", "door", "window", "column", "beam", "roof", "floor",
            "slab", "stair", "room", "facade", "ceiling", "balcony", "entrance"
        ]
        for c in candidates:
            if c in t:
                elements.append(c)
        return elements

    def _persist_feedback(self, record: FeedbackRecord) -> None:
        """Save feedback to AgentMemory."""
        try:
            content = (
                f"User Feedback: '{record.user_feedback}' on request '{record.original_request}' | "
                f"Type: {record.feedback_type} | Corrections: {record.extracted_corrections}"
            )
            self.client.remember(
                content=content,
                memory_type="user_feedback",
                project="ai-rhino-architect",
                concepts=["feedback", record.feedback_type] + record.affected_elements,
            )
        except Exception as exc:
            logger.warning("Failed to persist feedback to AgentMemory: %s", exc)

    def get_records(
        self, feedback_type: Optional[str] = None, element: Optional[str] = None
    ) -> List[FeedbackRecord]:
        """Retrieve feedback records matching criteria."""
        results = self._feedback_records
        if feedback_type:
            results = [r for r in results if r.feedback_type == feedback_type]
        if element:
            results = [r for r in results if element in r.affected_elements]
        return results

    def clear(self) -> None:
        """Clear local feedback records."""
        self._feedback_records.clear()


# Module-level singleton
_feedback_analyzer: Optional[FeedbackAnalyzer] = None


def get_feedback_analyzer() -> FeedbackAnalyzer:
    """Return shared process-wide FeedbackAnalyzer instance."""
    global _feedback_analyzer
    if _feedback_analyzer is None:
        _feedback_analyzer = FeedbackAnalyzer()
    return _feedback_analyzer
