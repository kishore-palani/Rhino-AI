"""
AgentMemory client wrapper for AI RHINO ARCHITECT.

Provides a thin Python interface to the local agentmemory REST API
at http://localhost:3111/agentmemory. Used to save, recall, and search
project memories, lessons, and failures.
"""

from __future__ import annotations

import json
import logging
import urllib.request
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

AGENTMEMORY_BASE_URL = "http://localhost:3111/agentmemory"


class AgentMemoryClient:
    """Minimal REST client for the local agentmemory service."""

    def __init__(self, base_url: str = AGENTMEMORY_BASE_URL) -> None:
        self.base_url = base_url.rstrip("/")

    def _post(self, path: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        url = f"{self.base_url}{path}"
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            url,
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            logger.error("agentmemory POST %s failed: %s", path, exc)
            return {"success": False, "error": str(exc)}
        except Exception as exc:  # pragma: no cover - network errors
            logger.error("agentmemory POST %s error: %s", path, exc)
            return {"success": False, "error": str(exc)}

    def _get(self, path: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        url = f"{self.base_url}{path}"
        if params:
            from urllib.parse import urlencode
            url = f"{url}?{urlencode(params)}"
        req = urllib.request.Request(url, method="GET")
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            logger.error("agentmemory GET %s failed: %s", path, exc)
            return {"success": False, "error": str(exc)}
        except Exception as exc:  # pragma: no cover
            logger.error("agentmemory GET %s error: %s", path, exc)
            return {"success": False, "error": str(exc)}

    # ------------------------------------------------------------------
    # Sessions
    # ------------------------------------------------------------------
    def start_session(
        self,
        session_id: str,
        project: str,
        cwd: str,
        agent_id: str = "kilo",
    ) -> Dict[str, Any]:
        return self._post(
            "/session/start",
            {
                "sessionId": session_id,
                "project": project,
                "cwd": cwd,
                "agentId": agent_id,
            },
        )

    def end_session(self, session_id: str) -> Dict[str, Any]:
        return self._post("/session/end", {"sessionId": session_id})

    # ------------------------------------------------------------------
    # Memories
    # ------------------------------------------------------------------
    def remember(
        self,
        content: str,
        memory_type: str = "fact",
        project: str = "ai-rhino-architect",
        concepts: Optional[List[str]] = None,
        files: Optional[List[str]] = None,
        ttl_days: Optional[int] = None,
    ) -> Dict[str, Any]:
        payload: Dict[str, Any] = {
            "content": content,
            "type": memory_type,
            "project": project,
            "concepts": concepts or [],
            "files": files or [],
        }
        if ttl_days is not None:
            payload["ttlDays"] = ttl_days
        return self._post("/remember", payload)

    def recall(self, query: str, limit: int = 10) -> Dict[str, Any]:
        return self._post("/search", {"query": query, "limit": limit})

    def smart_search(self, query: str, limit: int = 10) -> Dict[str, Any]:
        return self._post("/smart-search", {"query": query, "limit": limit})

    def forget(self, memory_id: Optional[str] = None, session_id: Optional[str] = None) -> Dict[str, Any]:
        payload: Dict[str, Any] = {}
        if memory_id:
            payload["memoryId"] = memory_id
        if session_id:
            payload["sessionId"] = session_id
        return self._post("/forget", payload)

    # ------------------------------------------------------------------
    # Lessons
    # ------------------------------------------------------------------
    def save_lesson(
        self,
        task: str,
        lesson: str,
        category: str = "general",
        strength: int = 7,
    ) -> Dict[str, Any]:
        return self._post(
            "/lessons",
            {
                "task": task,
                "lesson": lesson,
                "category": category,
                "strength": strength,
            },
        )

    def search_lessons(self, query: str, limit: int = 10) -> Dict[str, Any]:
        return self._post("/lessons/search", {"query": query, "limit": limit})

    # ------------------------------------------------------------------
    # Health
    # ------------------------------------------------------------------
    def health(self) -> Dict[str, Any]:
        return self._get("/health")

    def is_available(self) -> bool:
        try:
            resp = self._get("/livez")
            return resp.get("status") == "ok"
        except Exception:
            return False


# Module-level singleton for convenience
_client: Optional[AgentMemoryClient] = None


def get_client() -> AgentMemoryClient:
    """Return a process-wide AgentMemoryClient singleton."""
    global _client
    if _client is None:
        _client = AgentMemoryClient()
    return _client


def remember(content: str, **kwargs: Any) -> Dict[str, Any]:
    """Convenience wrapper around AgentMemoryClient.remember."""
    return get_client().remember(content, **kwargs)


def recall(query: str, **kwargs: Any) -> Dict[str, Any]:
    """Convenience wrapper around AgentMemoryClient.recall."""
    return get_client().recall(query, **kwargs)