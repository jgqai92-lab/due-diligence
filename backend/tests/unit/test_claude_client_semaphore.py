"""Unit tests for the API rate-limit semaphore in claude_client.

Tests verify:
- Concurrent API calls are limited to 2 by the semaphore
- Semaphore does not block sequential calls
- Both call_claude and call_claude_raw respect the semaphore
- Log messages are emitted when the semaphore is full
- Semaphore is properly released on exceptions
"""

import asyncio
import logging
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from pydantic import BaseModel

import app.services.claude_client as claude_client_module
from app.services.claude_client import API_SEMAPHORE_LIMIT


# ── Test response model ──────────────────────────────────────────────────────

class DummyResponse(BaseModel):
    answer: str


# ── Helpers ──────────────────────────────────────────────────────────────────

def _make_fake_api_response(text: str = '{"answer": "test"}'):
    """Create a mock Anthropic API response object."""
    content_block = MagicMock()
    content_block.text = text

    usage = MagicMock()
    usage.input_tokens = 100
    usage.output_tokens = 50

    response = MagicMock()
    response.content = [content_block]
    response.usage = usage
    return response


@pytest.fixture(autouse=True)
def reset_semaphore():
    """Reset the module-level semaphore before each test.

    Each pytest-asyncio test gets a fresh event loop, so the semaphore
    (which binds to an event loop) must be recreated.
    """
    claude_client_module._api_semaphore = None
    yield
    claude_client_module._api_semaphore = None


# ── Tests ────────────────────────────────────────────────────────────────────

class TestApiSemaphore:
    """Tests for the _api_semaphore concurrency limiter."""

    @pytest.mark.asyncio
    async def test_semaphore_limits_concurrent_calls(self):
        """At most 2 API calls should execute concurrently."""
        max_concurrent = 0
        current_concurrent = 0
        lock = asyncio.Lock()

        async def slow_api_call(**kwargs):
            nonlocal max_concurrent, current_concurrent
            async with lock:
                current_concurrent += 1
                if current_concurrent > max_concurrent:
                    max_concurrent = current_concurrent
            await asyncio.sleep(0.05)  # Simulate API latency
            async with lock:
                current_concurrent -= 1
            return _make_fake_api_response()

        mock_client = MagicMock()
        mock_client.messages.create = AsyncMock(side_effect=slow_api_call)

        with patch("app.services.claude_client.get_client", return_value=mock_client):
            tasks = [
                claude_client_module.call_claude(
                    system_prompt="test",
                    user_prompt=f"test {i}",
                    response_model=DummyResponse,
                )
                for i in range(5)
            ]

            await asyncio.gather(*tasks)

        # The semaphore allows at most API_SEMAPHORE_LIMIT concurrent calls
        assert max_concurrent <= API_SEMAPHORE_LIMIT, (
            f"Expected at most {API_SEMAPHORE_LIMIT} concurrent API calls, but saw {max_concurrent}"
        )
        # With 5 tasks and semaphore=API_SEMAPHORE_LIMIT, max should be exactly the limit
        assert max_concurrent == API_SEMAPHORE_LIMIT, (
            f"Expected exactly {API_SEMAPHORE_LIMIT} concurrent API calls (semaphore value), "
            f"but saw {max_concurrent}"
        )

        # Verify semaphore is fully released after all calls complete
        sem = claude_client_module._get_semaphore()
        assert sem._value == claude_client_module.API_SEMAPHORE_LIMIT

    @pytest.mark.asyncio
    async def test_semaphore_limits_call_claude_raw(self):
        """call_claude_raw also respects the semaphore."""
        max_concurrent = 0
        current_concurrent = 0
        lock = asyncio.Lock()

        async def slow_api_call(**kwargs):
            nonlocal max_concurrent, current_concurrent
            async with lock:
                current_concurrent += 1
                if current_concurrent > max_concurrent:
                    max_concurrent = current_concurrent
            await asyncio.sleep(0.05)
            async with lock:
                current_concurrent -= 1
            return _make_fake_api_response(text="raw response text")

        mock_client = MagicMock()
        mock_client.messages.create = AsyncMock(side_effect=slow_api_call)

        with patch("app.services.claude_client.get_client", return_value=mock_client):
            tasks = [
                claude_client_module.call_claude_raw(
                    system_prompt="test",
                    user_prompt=f"test {i}",
                )
                for i in range(4)
            ]

            results = await asyncio.gather(*tasks)

        assert max_concurrent <= API_SEMAPHORE_LIMIT
        assert all(r == "raw response text" for r in results)

    @pytest.mark.asyncio
    async def test_semaphore_logs_when_full(self, caplog):
        """A log message is emitted when a call waits on a full semaphore."""
        call_count = 0
        release_event = asyncio.Event()

        async def blocking_api_call(**kwargs):
            nonlocal call_count
            call_count += 1
            if call_count <= API_SEMAPHORE_LIMIT:
                # First N calls block until we signal
                await release_event.wait()
            return _make_fake_api_response()

        mock_client = MagicMock()
        mock_client.messages.create = AsyncMock(side_effect=blocking_api_call)

        with patch("app.services.claude_client.get_client", return_value=mock_client):
            with caplog.at_level(logging.INFO, logger="app.services.claude_client"):
                # Start N+1 calls: N will acquire, 1 should wait
                tasks = [
                    asyncio.create_task(
                        claude_client_module.call_claude(
                            system_prompt="test",
                            user_prompt=f"test {i}",
                            response_model=DummyResponse,
                        )
                    )
                    for i in range(API_SEMAPHORE_LIMIT + 1)
                ]

                # Give time for the first N to acquire and (N+1)th to hit the log
                await asyncio.sleep(0.1)

                # Release all blocked calls
                release_event.set()

                await asyncio.gather(*tasks)

        # Check that the semaphore-waiting log was emitted
        semaphore_logs = [
            r for r in caplog.records
            if "semaphore full" in r.message.lower()
        ]
        assert len(semaphore_logs) >= 1, (
            f"Expected at least one 'semaphore full' log message when {API_SEMAPHORE_LIMIT + 1} calls "
            f"compete for {API_SEMAPHORE_LIMIT} semaphore slots"
        )

    @pytest.mark.asyncio
    async def test_sequential_calls_not_blocked(self):
        """Sequential calls should never wait on the semaphore."""
        mock_client = MagicMock()
        mock_client.messages.create = AsyncMock(
            return_value=_make_fake_api_response()
        )

        with patch("app.services.claude_client.get_client", return_value=mock_client):
            for i in range(5):
                result = await claude_client_module.call_claude(
                    system_prompt="test",
                    user_prompt=f"test {i}",
                    response_model=DummyResponse,
                )
                assert result.answer == "test"

        assert mock_client.messages.create.call_count == 5

    @pytest.mark.asyncio
    async def test_semaphore_releases_on_exception(self):
        """Semaphore is released even if the API call raises an exception."""
        mock_client = MagicMock()
        mock_client.messages.create = AsyncMock(
            side_effect=Exception("API error")
        )

        with patch("app.services.claude_client.get_client", return_value=mock_client):
            with pytest.raises(Exception, match="API error"):
                await claude_client_module.call_claude_raw(
                    system_prompt="test",
                    user_prompt="test",
                )

        # Semaphore must be fully released after exception
        sem = claude_client_module._get_semaphore()
        assert sem._value == claude_client_module.API_SEMAPHORE_LIMIT, (
            "Semaphore was not released after an exception"
        )

    @pytest.mark.asyncio
    async def test_mixed_call_types_share_semaphore(self):
        """call_claude and call_claude_raw share the same semaphore."""
        max_concurrent = 0
        current_concurrent = 0
        lock = asyncio.Lock()

        async def slow_api_call(**kwargs):
            nonlocal max_concurrent, current_concurrent
            async with lock:
                current_concurrent += 1
                if current_concurrent > max_concurrent:
                    max_concurrent = current_concurrent
            await asyncio.sleep(0.05)
            async with lock:
                current_concurrent -= 1
            return _make_fake_api_response()

        mock_client = MagicMock()
        mock_client.messages.create = AsyncMock(side_effect=slow_api_call)

        with patch("app.services.claude_client.get_client", return_value=mock_client):
            tasks = [
                claude_client_module.call_claude(
                    system_prompt="test",
                    user_prompt="structured 1",
                    response_model=DummyResponse,
                ),
                claude_client_module.call_claude_raw(
                    system_prompt="test",
                    user_prompt="raw 1",
                ),
                claude_client_module.call_claude(
                    system_prompt="test",
                    user_prompt="structured 2",
                    response_model=DummyResponse,
                ),
                claude_client_module.call_claude_raw(
                    system_prompt="test",
                    user_prompt="raw 2",
                ),
            ]

            await asyncio.gather(*tasks)

        # Both function types share the semaphore, so max concurrent is still the limit
        assert max_concurrent <= API_SEMAPHORE_LIMIT, (
            f"Expected at most {API_SEMAPHORE_LIMIT} concurrent API calls across both function types, "
            f"but saw {max_concurrent}"
        )

    @pytest.mark.asyncio
    async def test_semaphore_created_lazily(self):
        """The semaphore is created on first use, not at import time."""
        # After reset_semaphore fixture, _api_semaphore should be None
        assert claude_client_module._api_semaphore is None

        sem = claude_client_module._get_semaphore()
        assert sem is not None
        assert isinstance(sem, asyncio.Semaphore)
        assert sem._value == claude_client_module.API_SEMAPHORE_LIMIT

        # Subsequent calls return the same instance
        sem2 = claude_client_module._get_semaphore()
        assert sem is sem2
