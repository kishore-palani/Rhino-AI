"""Helpers for safely framing Server-Sent Events."""

from __future__ import annotations

import json
from typing import Any


def _validate_field(value: str, field_name: str) -> str:
    if "\r" in value or "\n" in value:
        raise ValueError(f"{field_name} must not contain CR or LF")
    return value


def encode_sse_event(
    data: Any,
    *,
    event: str | None = None,
    event_id: str | None = None,
    retry: int | None = None,
) -> str:
    """Encode one JSON payload as an SSE event.

    JSON serialization keeps payload newlines escaped, so attacker-controlled
    strings cannot add SSE fields or terminate the event early.
    """
    lines: list[str] = []
    if event is not None:
        lines.append(f"event: {_validate_field(event, 'event')}")
    if event_id is not None:
        lines.append(f"id: {_validate_field(event_id, 'event_id')}")
    if retry is not None:
        if retry < 0:
            raise ValueError("retry must be non-negative")
        lines.append(f"retry: {retry}")

    payload = json.dumps(
        data,
        ensure_ascii=True,
        allow_nan=False,
        separators=(",", ":"),
    )
    lines.append(f"data: {payload}")
    return "\n".join(lines) + "\n\n"