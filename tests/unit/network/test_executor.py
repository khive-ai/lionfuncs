# Copyright (c) 2023 - 2025, HaiyangLi <quantocean.li at gmail dot com>
#
# SPDX-License-Identifier: Apache-2.0

"""
Unit tests for the network executor module.
"""

import asyncio
import unittest
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from lionfuncs.network.events import NetworkRequestEvent, RequestStatus
from lionfuncs.network.executor import Executor


class TestExecutor:
    """Test cases for the Executor class."""

    @pytest.fixture
    async def executor(self):
        """Create an Executor instance for testing."""
        executor = Executor(
            queue_capacity=10,
            concurrency_limit=5,
            requests_rate=10.0,
            requests_period=1.0,
            api_tokens_rate=1000.0,
            api_tokens_period=60.0,
            num_workers=2
        )
        await executor.start()
        yield executor
        await executor.stop()

    @pytest.mark.asyncio
    async def test_init(self):
        """Test initialization with default and custom values."""
        # Test with default values
        executor = Executor()
        assert executor.work_queue.queue.maxsize == 1000
        assert executor.capacity_limiter.total_tokens == 10
        assert executor.requests_rate_limiter.rate == 10.0
        assert executor.requests_rate_limiter.period == 1.0
        assert executor.api_tokens_rate_limiter is None
        assert executor._is_running is False

        # Test with custom values
        executor = Executor(
            queue_capacity=100,
            concurrency_limit=20,
            requests_rate=5.0,
            requests_period=2.0,
            api_tokens_rate=500.0,
            api_tokens_period=30.0,
            num_workers=3
        )
        assert executor.work_queue.queue.maxsize == 100
        assert executor.capacity_limiter.total_tokens == 20
        assert executor.requests_rate_limiter.rate == 5.0
        assert executor.requests_rate_limiter.period == 2.0
        assert executor.api_tokens_rate_limiter is not None
        assert executor.api_tokens_rate_limiter.rate == 500.0
        assert executor.api_tokens_rate_limiter.period == 30.0
        assert executor._is_running is False

    @pytest.mark.asyncio
    async def test_start_stop(self):
        """Test start and stop methods."""
        executor = Executor()
        
        # Test start
        assert executor._is_running is False
        await executor.start()
        assert executor._is_running is True
        
        # Test idempotent start
        await executor.start()  # Should not raise an error
        assert executor._is_running is True
        
        # Test stop
        await executor.stop()
        assert executor._is_running is False
        
        # Test idempotent stop
        await executor.stop()  # Should not raise an error
        assert executor._is_running is False
        
        # Test graceful=False stop
        await executor.start()
        assert executor._is_running is True
        await executor.stop(graceful=False)
        assert executor._is_running is False

    @pytest.mark.asyncio
    async def test_context_manager(self):
        """Test context manager usage."""
        async with Executor() as executor:
            assert executor._is_running is True
        assert executor._is_running is False

    @pytest.mark.asyncio
    async def test_submit_task_not_running(self):
        """Test submitting a task when executor is not running."""
        executor = Executor()
        
        with pytest.raises(RuntimeError, match="Executor is not running"):
            await executor.submit_task(AsyncMock())

    @pytest.mark.asyncio
    async def test_submit_task(self, executor):
        """Test submitting a task."""
        # Create a mock API coroutine
        mock_api_coro = AsyncMock(return_value=(200, {"Content-Type": "application/json"}, {"result": "success"}))
        
        # Submit the task
        event = await executor.submit_task(
            api_call_coroutine=mock_api_coro,
            endpoint_url="https://api.example.com/v1/test",
            method="POST",
            headers={"Authorization": "Bearer test"},
            payload={"test": "data"},
            num_api_tokens_needed=50,
            metadata={"test_key": "test_value"}
        )
        
        # Verify the event
        assert isinstance(event, NetworkRequestEvent)
        assert event.status == RequestStatus.QUEUED
        assert event.endpoint_url == "https://api.example.com/v1/test"
        assert event.method == "POST"
        assert event.headers == {"Authorization": "Bearer test"}
        assert event.payload == {"test": "data"}
        assert event.num_api_tokens_needed == 50
        assert event.metadata == {"test_key": "test_value"}
        
        # Wait for the task to be processed
        await asyncio.sleep(0.1)
        
        # Verify the API coroutine was called
        mock_api_coro.assert_called_once()

    @pytest.mark.asyncio
    async def test_worker_success(self, executor):
        """Test worker processing a successful task."""
        # Create a mock API coroutine
        mock_api_coro = AsyncMock(return_value=(200, {"Content-Type": "application/json"}, {"result": "success"}))
        
        # Create a mock event
        event = NetworkRequestEvent(
            request_id="test-id",
            endpoint_url="https://api.example.com/v1/test",
            method="POST",
            num_api_tokens_needed=50
        )
        
        # Create task data
        task_data = {
            "api_coro": mock_api_coro,
            "event": event
        }
        
        # Process the task
        await executor._worker(task_data)
        
        # Verify the event was updated
        assert event.status == RequestStatus.COMPLETED
        assert event.response_status_code == 200
        assert event.response_headers == {"Content-Type": "application/json"}
        assert event.response_body == {"result": "success"}
        assert event.completed_at is not None
        
        # Verify logs were added
        assert len(event.logs) >= 4  # At least 4 log entries (status changes, rate limit acquisitions)
        assert any("Acquired concurrency slot" in log for log in event.logs)
        assert any("Acquired request rate limit token" in log for log in event.logs)
        assert any("Acquired API token rate limit (50 tokens)" in log for log in event.logs)
        assert any("Status changed from PROCESSING to CALLING" in log for log in event.logs)
        assert any("Status changed from CALLING to COMPLETED" in log for log in event.logs)

    @pytest.mark.asyncio
    async def test_worker_error(self, executor):
        """Test worker processing a task that raises an error."""
        # Create a mock API coroutine that raises an exception
        mock_error = ValueError("Test error")
        mock_api_coro = AsyncMock(side_effect=mock_error)
        
        # Create a mock event
        event = NetworkRequestEvent(
            request_id="test-id",
            endpoint_url="https://api.example.com/v1/test",
            method="POST"
        )
        
        # Create task data
        task_data = {
            "api_coro": mock_api_coro,
            "event": event
        }
        
        # Process the task
        await executor._worker(task_data)
        
        # Verify the event was updated
        assert event.status == RequestStatus.FAILED
        assert event.error_type == "ValueError"
        assert event.error_message == "Test error"
        assert event.error_details is not None
        assert event.completed_at is not None
        
        # Verify logs were added
        assert len(event.logs) >= 3  # At least 3 log entries
        assert any("Call failed: ValueError - Test error" in log for log in event.logs)

    @pytest.mark.asyncio
    async def test_rate_limiting(self):
        """Test rate limiting behavior."""
        # Create an executor with very low rate limits for testing
        executor = Executor(
            requests_rate=2.0,  # 2 requests per second
            requests_period=1.0,
            api_tokens_rate=100.0,  # 100 tokens per minute
            api_tokens_period=60.0,
            num_workers=1
        )
        await executor.start()
        
        try:
            # Mock the rate limiters to track acquisition calls
            executor.requests_rate_limiter.acquire = AsyncMock(return_value=0.0)
            executor.api_tokens_rate_limiter.acquire = AsyncMock(return_value=0.0)
            
            # Create a mock API coroutine
            mock_api_coro = AsyncMock(return_value=(200, {}, {}))
            
            # Submit multiple tasks
            events = []
            for i in range(3):
                event = await executor.submit_task(
                    api_call_coroutine=mock_api_coro,
                    num_api_tokens_needed=50
                )
                events.append(event)
            
            # Wait for tasks to be processed
            await asyncio.sleep(0.2)
            
            # Verify rate limiters were called correctly
            assert executor.requests_rate_limiter.acquire.call_count == 3
            assert executor.api_tokens_rate_limiter.acquire.call_count == 3
            
            # Verify all tasks were processed
            for event in events:
                assert event.status == RequestStatus.COMPLETED
        
        finally:
            await executor.stop()

    @pytest.mark.asyncio
    async def test_concurrency_limiting(self):
        """Test concurrency limiting behavior."""
        # Create an executor with low concurrency limit
        executor = Executor(
            concurrency_limit=2,  # Only 2 concurrent tasks
            num_workers=4  # More workers than concurrency limit
        )
        await executor.start()
        
        try:
            # Mock the capacity limiter to track acquisition
            original_acquire = executor.capacity_limiter.acquire
            acquire_count = 0
            release_count = 0
            
            async def mock_acquire():
                nonlocal acquire_count
                acquire_count += 1
                await original_acquire()
            
            original_release = executor.capacity_limiter.release
            
            def mock_release():
                nonlocal release_count
                release_count += 1
                original_release()
            
            executor.capacity_limiter.acquire = mock_acquire
            executor.capacity_limiter.release = mock_release
            
            # Create a mock API coroutine with delay
            async def delayed_api_coro():
                await asyncio.sleep(0.1)
                return (200, {}, {})
            
            # Submit multiple tasks
            events = []
            for i in range(5):
                event = await executor.submit_task(
                    api_call_coroutine=delayed_api_coro
                )
                events.append(event)
            
            # Wait for tasks to be processed
            await asyncio.sleep(0.5)
            
            # Verify capacity limiter was used correctly
            assert acquire_count == 5
            assert release_count == 5
            
            # Verify all tasks were processed
            for event in events:
                assert event.status == RequestStatus.COMPLETED
        
        finally:
            await executor.stop()


if __name__ == "__main__":
    unittest.main()