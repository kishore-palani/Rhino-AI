"""
Project-level memory helpers for AI RHINO ARCHITECT.

Wraps AgentMemoryClient with domain-specific functions for
saving project state, failures, lessons, and feedback.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from ai.memory.agentmemory_client import AgentMemoryClient

logger = logging.getLogger(__name__)

PROJECT_NAME = "ai-rhino-architect"


class ProjectMemory:
    """Domain-specific memory operations for the Rhino Architect project."""

    def __init__(self, client: Optional[AgentMemoryClient] = None) -> None:
        self.client = client or AgentMemoryClient()

    # ------------------------------------------------------------------
    # Project state
    # ------------------------------------------------------------------
    def save_project_state(
        self,
        phase: str,
        status: str,
        details: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Persist the current development phase and status."""
        content = f"Phase {phase} status: {status}"
        if details:
            content += f" | details: {details}"
        return self.client.remember(
            content=content,
            memory_type="state",
            project=PROJECT_NAME,
            concepts=["phase", phase, status],
        )

    # ------------------------------------------------------------------
    # Failures
    # ------------------------------------------------------------------
    def save_failure(
        self,
        task: str,
        error: str,
        failure_type: str = "general",
        diagnosis: str = "",
        correction: str = "",
    ) -> Dict[str, Any]:
        """Record a structured failure for future reference."""
        content = (
            f"Task: {task} | Error: {error} | Type: {failure_type} | "
            f"Diagnosis: {diagnosis} | Correction: {correction}"
        )
        return self.client.remember(
            content=content,
            memory_type="failure",
            project=PROJECT_NAME,
            concepts=["failure", failure_type, task],
        )

    # ------------------------------------------------------------------
    # Lessons
    # ------------------------------------------------------------------
    def save_lesson(
        self,
        task: str,
        lesson: str,
        category: str = "development",
    ) -> Dict[str, Any]:
        """Save a learned lesson from a completed task."""
        return self.client.save_lesson(
            task=task,
            lesson=lesson,
            category=category,
        )

    # ------------------------------------------------------------------
    # Feedback
    # ------------------------------------------------------------------
    def save_feedback(
        self,
        original_request: str,
        feedback: str,
        action_taken: str = "",
    ) -> Dict[str, Any]:
        """Record user feedback and the resulting correction."""
        content = (
            f"Request: {original_request} | Feedback: {feedback} | "
            f"Action: {action_taken}"
        )
        return self.client.remember(
            content=content,
            memory_type="feedback",
            project=PROJECT_NAME,
            concepts=["feedback", "user-correction"],
        )

    # ------------------------------------------------------------------
    # Recall
    # ------------------------------------------------------------------
    def recall_relevant(self, query: str, limit: int = 10) -> Dict[str, Any]:
        """Search memories relevant to the given query."""
        return self.client.recall(query=query, limit=limit)

    def recall_failures(self, task: str, limit: int = 5) -> Dict[str, Any]:
        """Search for past failures related to a task."""
        return self.client.recall(query=f"failure {task}", limit=limit)

    def recall_lessons(self, topic: str, limit: int = 5) -> Dict[str, Any]:
        """Search for past lessons related to a topic."""
        return self.client.search_lessons(query=topic, limit=limit)


# Module-level singleton
_project_memory: Optional[ProjectMemory] = None


def get_project_memory() -> ProjectMemory:
    """Return a process-wide ProjectMemory singleton."""
    global _project_memory
    if _project_memory is None:
        _project_memory = ProjectMemory()
    return _project_memory