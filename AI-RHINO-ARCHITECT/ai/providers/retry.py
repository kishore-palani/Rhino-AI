"""Retry helpers for transient LLM provider failures."""

from __future__ import annotations

import asyncio
import inspect
import json
from collections.abc import Awaitable, Callable, Mapping
from typing import Any, TypeVar

ResultT = TypeVar("ResultT")

_RETRYABLE_STATUS_CODES = {408, 429, 500, 502, 503, 504}
_MAX_BACKOFF_SECONDS = 30.0


def _error_value(error: BaseException | Mapping[str, Any], name: str) -> Any:
    if isinstance(error, Mapping):
        if name in error:
            return error.get(name)
        for nested_name in ("data", "error", "details"):
            nested = error.get(nested_name)
            if isinstance(nested, Mapping):
                value = _error_value(nested, name)
                if value is not None:
                    return value
        return None
    return getattr(error, name, None)


def _status_code(error: BaseException | Mapping[str, Any]) -> int | None:
    response = _error_value(error, "response")
    value = getattr(response, "status_code", None)
    if value is None:
        value = response.get("status_code") if isinstance(response, Mapping) else None
    if value is None:
        value = _error_value(error, "status_code")
    response_body = None
    if value is None:
        response_body = _error_value(error, "responseBody")
    if response_body is None:
        response_body = _error_value(error, "response_body")
    if isinstance(response_body, Mapping):
        value = response_body.get("code")
    elif isinstance(response_body, str):
        try:
            value = json.loads(response_body).get("code")
        except (TypeError, ValueError):
            value = None
    try:
        return int(value) if value is not None else None
    except (TypeError, ValueError):
        return None


def is_retryable_provider_error(error: BaseException | Mapping[str, Any]) -> bool:
    """Return whether an error represents a transient provider failure."""
    if _error_value(error, "isRetryable") is True or _error_value(error, "is_retryable") is True:
        return True
    if isinstance(error, Mapping):
        data = error.get("data")
        if isinstance(data, Mapping) and (
            data.get("isRetryable") is True or data.get("is_retryable") is True
        ):
            return True
    if isinstance(error, (TimeoutError, asyncio.TimeoutError, ConnectionError)):
        return True
    if _status_code(error) in _RETRYABLE_STATUS_CODES:
        return True

    message = str(error).lower()
    return (
        "idle timeout" in message
        or ("timed out" in message and ("provider" in message or "upstream" in message))
    )


def _retry_after_seconds(error: BaseException | Mapping[str, Any]) -> float | None:
    direct_value = _error_value(error, "retry_after")
    if direct_value is not None:
        try:
            return max(0.0, float(direct_value))
        except (TypeError, ValueError):
            pass

    response = _error_value(error, "response")
    headers = getattr(response, "headers", None)
    if headers is None and isinstance(response, Mapping):
        headers = response.get("headers")
    if not headers:
        return None
    value = headers.get("retry-after") or headers.get("Retry-After")
    try:
        return max(0.0, float(value)) if value is not None else None
    except (TypeError, ValueError):
        return None


async def with_provider_retries(
    operation: Callable[[], Awaitable[ResultT]],
    *,
    max_retries: int = 3,
    retry_backoff: float = 1.0,
    sleep: Callable[[float], Awaitable[None]] = asyncio.sleep,
) -> ResultT:
    """Run a provider operation and retry transient failures.

    ``max_retries`` is the number of additional attempts after the initial
    request. Non-transient errors are raised immediately.
    """
    if max_retries < 0:
        raise ValueError("max_retries must be >= 0")
    if retry_backoff < 0:
        raise ValueError("retry_backoff must be >= 0")

    for attempt in range(max_retries + 1):
        try:
            result = operation()
            if inspect.isawaitable(result):
                return await result
            return result
        except Exception as error:
            if not is_retryable_provider_error(error) or attempt >= max_retries:
                raise

            delay = _retry_after_seconds(error)
            if delay is None:
                delay = min(_MAX_BACKOFF_SECONDS, retry_backoff * (2**attempt))
            await sleep(delay)

    raise RuntimeError("provider retry loop exited unexpectedly")