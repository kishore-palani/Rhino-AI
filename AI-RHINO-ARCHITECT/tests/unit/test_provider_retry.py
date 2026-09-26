import asyncio

import pytest

from apps.api.mcp.exceptions import (
    MCPNotFoundError,
    MCPRateLimitError,
    MCPTimeoutError,
    error_from_jsonrpc_error,
)
from ai.providers.retry import is_retryable_provider_error, with_provider_retries


class ProviderError(Exception):
    def __init__(self, status_code: int, message: str = "provider failure") -> None:
        super().__init__(message)
        self.status_code = status_code


class ApiError(Exception):
    def __init__(self) -> None:
        super().__init__("Upstream idle timeout exceeded")
        self.isRetryable = True
        self.responseBody = (
            '{"code":504,"message":"Upstream idle timeout exceeded",'
            '"metadata":{"error_type":"timeout"}}'
        )


def test_retries_503_and_returns_result() -> None:
    async def scenario() -> None:
        attempts = 0
        delays: list[float] = []

        async def operation() -> str:
            nonlocal attempts
            attempts += 1
            if attempts < 3:
                raise ProviderError(503)
            return "ok"

        async def fake_sleep(delay: float) -> None:
            delays.append(delay)

        result = await with_provider_retries(
            operation, max_retries=3, retry_backoff=0.5, sleep=fake_sleep
        )

        assert result == "ok"
        assert attempts == 3
        assert delays == [0.5, 1.0]

    asyncio.run(scenario())


def test_retries_provider_timeout() -> None:
    async def scenario() -> None:
        attempts = 0

        async def operation() -> str:
            nonlocal attempts
            attempts += 1
            if attempts == 1:
                raise asyncio.TimeoutError(
                    "The upstream provider timed out while sending the response."
                )
            return "ok"

        result = await with_provider_retries(
            operation, sleep=lambda _: asyncio.sleep(0)
        )

        assert result == "ok"
        assert attempts == 2

    asyncio.run(scenario())


def test_retries_mcp_response_timeout() -> None:
    async def scenario() -> None:
        attempts = 0

        async def operation() -> str:
            nonlocal attempts
            attempts += 1
            if attempts == 1:
                raise MCPTimeoutError("Response timeout", elapsed=30.0)
            return "ok"

        result = await with_provider_retries(
            operation, retry_backoff=0, sleep=lambda _: asyncio.sleep(0)
        )

        assert result == "ok"
        assert attempts == 2

    asyncio.run(scenario())


def test_retries_mcp_rate_limit_using_retry_after() -> None:
    async def scenario() -> None:
        attempts = 0
        delays: list[float] = []

        async def operation() -> str:
            nonlocal attempts
            attempts += 1
            if attempts == 1:
                raise MCPRateLimitError("Rate limit exceeded", retry_after=2.5)
            return "ok"

        async def fake_sleep(delay: float) -> None:
            delays.append(delay)

        result = await with_provider_retries(
            operation, max_retries=1, retry_backoff=0.1, sleep=fake_sleep
        )

        assert result == "ok"
        assert delays == [2.5]

    asyncio.run(scenario())


def test_maps_mcp_rate_limit_and_not_found_errors() -> None:
    assert isinstance(error_from_jsonrpc_error(-32003, "missing"), MCPNotFoundError)
    assert isinstance(error_from_jsonrpc_error(-32004, "limited"), MCPRateLimitError)


def test_retries_retryable_api_error_payload() -> None:
    async def scenario() -> None:
        attempts = 0

        async def operation() -> str:
            nonlocal attempts
            attempts += 1
            if attempts == 1:
                raise ApiError()
            return "ok"

        result = await with_provider_retries(
            operation, max_retries=1, retry_backoff=0, sleep=lambda _: asyncio.sleep(0)
        )

        assert result == "ok"
        assert attempts == 2

    asyncio.run(scenario())


def test_does_not_retry_non_transient_error() -> None:
    async def scenario() -> None:
        attempts = 0

        async def operation() -> str:
            nonlocal attempts
            attempts += 1
            raise ProviderError(401)

        with pytest.raises(ProviderError):
            await with_provider_retries(
                operation, sleep=lambda _: asyncio.sleep(0)
            )

        assert attempts == 1

    asyncio.run(scenario())


def test_recognizes_json_shaped_api_error() -> None:
    error = {
        "name": "APIError",
        "data": {
            "message": "Upstream idle timeout exceeded",
            "isRetryable": True,
            "responseBody": '{"code":504,"message":"Upstream idle timeout exceeded"}',
        },
    }

    assert is_retryable_provider_error(error)


def test_recognizes_nested_data_status_code_error() -> None:
    error = {
        "name": "APIError",
        "data": {
            "status_code": 504,
            "responseBody": '{"code":504,"message":"Gateway timeout"}',
        },
    }

    assert is_retryable_provider_error(error)