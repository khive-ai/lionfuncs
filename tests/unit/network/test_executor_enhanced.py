"""
Enhanced unit tests for the Executor class to increase coverage.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from lionfuncs.network.events import NetworkRequestEvent, RequestStatus
from lionfuncs.network.executor import Executor
from lionfuncs.network.primitives import TokenBucketRateLimiter


class TestExecutorEnhanced:
    """Enhanced test cases for the Executor class."""

    @pytest.fixture
    def executor(self):
        """Create an Executor instance for testing."""
        executor = Executor(
            queue_capacity=10,
            concurrency_limit=5,
            requests_rate=10.0,
            requests_period=1.0,
            api_tokens_rate=1000.0,
            api_tokens_period=60.0,
            num_workers=2,
        )
        return executor

    @pytest.mark.asyncio
    async def test_worker_with_request_rate_limit_wait(self, executor):
        """Test _worker method with request rate limit wait time."""
        # Create a mock event
        event = MagicMock(spec=NetworkRequestEvent)
        event.update_status = MagicMock()
        event.add_log = MagicMock()
        event.set_result = MagicMock()
        event.num_api_tokens_needed = 0

        # Create a mock API coroutine
        mock_response = {"result": "success"}
        api_coro = AsyncMock(return_value=mock_response)

        # Create task data
        task_data = {
            "api_coro": api_coro,
            "event": event,
        }

        # Mock the capacity limiter
        executor.capacity_limiter = MagicMock()
        executor.capacity_limiter.__aenter__ = AsyncMock()
        executor.capacity_limiter.__aexit__ = AsyncMock()

        # Mock the requests rate limiter to return a wait time
        executor.requests_rate_limiter = MagicMock()
        executor.requests_rate_limiter.acquire = AsyncMock(
            return_value=0.5
        )  # 0.5 second wait

        # Mock asyncio.sleep
        with patch("asyncio.sleep", new=AsyncMock()) as mock_sleep:
            # Call the _worker method
            await executor._worker(task_data)

            # Verify that sleep was called with the correct wait time
            mock_sleep.assert_called_once_with(0.5)

        # Verify that the event was updated correctly
        event.update_status.assert_any_call(RequestStatus.PROCESSING)
        event.update_status.assert_any_call(RequestStatus.CALLING)
        event.add_log.assert_any_call("Waiting 0.50s for request rate limit.")

    @pytest.mark.asyncio
    async def test_worker_with_api_tokens_rate_limit_wait(self, executor):
        """Test _worker method with API tokens rate limit wait time."""
        # Create a mock event
        event = MagicMock(spec=NetworkRequestEvent)
        event.update_status = MagicMock()
        event.add_log = MagicMock()
        event.set_result = MagicMock()
        event.num_api_tokens_needed = 100  # Need 100 API tokens

        # Create a mock API coroutine
        mock_response = {"result": "success"}
        api_coro = AsyncMock(return_value=mock_response)

        # Create task data
        task_data = {
            "api_coro": api_coro,
            "event": event,
        }

        # Mock the capacity limiter
        executor.capacity_limiter = MagicMock()
        executor.capacity_limiter.__aenter__ = AsyncMock()
        executor.capacity_limiter.__aexit__ = AsyncMock()

        # Mock the requests rate limiter
        executor.requests_rate_limiter = MagicMock()
        executor.requests_rate_limiter.acquire = AsyncMock(return_value=0.0)  # No wait

        # Mock the API tokens rate limiter to return a wait time
        executor.api_tokens_rate_limiter = MagicMock()
        executor.api_tokens_rate_limiter.acquire = AsyncMock(
            return_value=1.5
        )  # 1.5 second wait

        # Mock asyncio.sleep
        with patch("asyncio.sleep", new=AsyncMock()) as mock_sleep:
            # Call the _worker method
            await executor._worker(task_data)

            # Verify that sleep was called with the correct wait time
            mock_sleep.assert_called_once_with(1.5)

        # Verify that the event was updated correctly
        event.update_status.assert_any_call(RequestStatus.PROCESSING)
        event.update_status.assert_any_call(RequestStatus.CALLING)
        event.add_log.assert_any_call(
            "Waiting 1.50s for API token rate limit (100 tokens)."
        )

    @pytest.mark.asyncio
    async def test_start_already_running(self, executor):
        """Test start method when executor is already running."""
        # Start the executor
        await executor.start()

        # Mock the work_queue methods to verify they're not called again
        executor.work_queue.start = AsyncMock()
        executor.work_queue.process = AsyncMock()

        # Call start again
        await executor.start()

        # Verify that work_queue methods were not called
        executor.work_queue.start.assert_not_called()
        executor.work_queue.process.assert_not_called()

        # Clean up
        await executor.stop()

    @pytest.mark.asyncio
    async def test_stop_not_running(self):
        """Test stop method when executor is not running."""
        executor = Executor()
        # Executor is not started, so _is_running is False

        # Mock the work_queue.stop method to verify it's not called
        executor.work_queue.stop = AsyncMock()

        # Call stop
        await executor.stop()

        # Verify that work_queue.stop was not called
        executor.work_queue.stop.assert_not_called()

    @pytest.mark.asyncio
    async def test_stop_graceful_vs_immediate(self, executor):
        """Test stop method with graceful=True vs graceful=False."""
        # Start the executor
        await executor.start()

        # Replace work_queue.stop with a mock to verify calls
        executor.work_queue.stop = AsyncMock()

        # Call stop with graceful=True (default)
        await executor.stop(graceful=True)

        # Verify that work_queue.stop was called with timeout=None
        executor.work_queue.stop.assert_called_once_with(timeout=None)

        # Reset the mock and _is_running flag for the next test
        executor.work_queue.stop.reset_mock()
        executor._is_running = True

        # Call stop with graceful=False
        await executor.stop(graceful=False)

        # Verify that work_queue.stop was called with timeout=0.1
        executor.work_queue.stop.assert_called_once_with(timeout=0.1)

    @pytest.mark.asyncio
    async def test_token_bucket_rate_limiter_initialization(self):
        """Test that TokenBucketRateLimiter is initialized correctly."""
        # Create an executor with specific rate limiter parameters
        executor = Executor(
            requests_rate=20.0,
            requests_period=2.0,
            requests_bucket_capacity=30.0,
            api_tokens_rate=5000.0,
            api_tokens_period=60.0,
            api_tokens_bucket_capacity=7500.0,
        )

        # Verify requests_rate_limiter initialization
        assert isinstance(executor.requests_rate_limiter, TokenBucketRateLimiter)
        assert executor.requests_rate_limiter.rate == 20.0
        assert executor.requests_rate_limiter.period == 2.0
        assert executor.requests_rate_limiter.max_tokens == 30.0

        # Verify api_tokens_rate_limiter initialization
        assert isinstance(executor.api_tokens_rate_limiter, TokenBucketRateLimiter)
        assert executor.api_tokens_rate_limiter.rate == 5000.0
        assert executor.api_tokens_rate_limiter.period == 60.0
        assert executor.api_tokens_rate_limiter.max_tokens == 7500.0

    @pytest.mark.asyncio
    async def test_token_bucket_rate_limiter_default_max_tokens(self):
        """Test that TokenBucketRateLimiter uses rate as max_tokens when not specified."""
        # Create an executor without specifying bucket capacities
        executor = Executor(
            requests_rate=15.0,
            requests_period=1.0,
            requests_bucket_capacity=None,  # Should default to requests_rate
            api_tokens_rate=2000.0,
            api_tokens_period=30.0,
            api_tokens_bucket_capacity=None,  # Should default to api_tokens_rate
        )

        # Verify requests_rate_limiter max_tokens defaults to rate
        assert executor.requests_rate_limiter.max_tokens == 15.0

        # Verify api_tokens_rate_limiter max_tokens defaults to rate
        assert executor.api_tokens_rate_limiter.max_tokens == 2000.0

    @pytest.mark.asyncio
    async def test_submit_task_with_minimal_parameters(self, executor):
        """Test submit_task with minimal required parameters."""
        # Start the executor
        await executor.start()

        try:
            # Create a mock API coroutine
            api_call_coroutine = AsyncMock(return_value={"result": "success"})

            # Call submit_task with minimal parameters
            event = await executor.submit_task(
                api_call_coroutine=api_call_coroutine,
            )

            # Verify that a NetworkRequestEvent was returned
            assert isinstance(event, NetworkRequestEvent)
            assert event.endpoint_url is None
            assert event.method is None
            assert event.payload is None
            assert event.num_api_tokens_needed == 0
            assert event.metadata == {}
            assert event.status == RequestStatus.QUEUED
        finally:
            # Stop the executor
            await executor.stop()
