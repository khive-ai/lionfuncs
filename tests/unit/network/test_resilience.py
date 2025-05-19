"""
Unit tests for the resilience module.
"""

import asyncio
from unittest.mock import AsyncMock

import pytest

from lionfuncs.errors import CircuitBreakerOpenError
from lionfuncs.network.resilience import (
    CircuitBreaker,
    CircuitState,
    RetryConfig,
    circuit_breaker,
    retry_with_backoff,
    with_retry,
)


class TestCircuitBreaker:
    """Tests for the CircuitBreaker class."""

    @pytest.mark.asyncio
    async def test_circuit_breaker_init(self):
        """Test CircuitBreaker initialization."""
        cb = CircuitBreaker(
            failure_threshold=3,
            recovery_time=5.0,
            half_open_max_calls=2,
            name="test_breaker",
        )

        assert cb.failure_threshold == 3
        assert cb.recovery_time == 5.0
        assert cb.half_open_max_calls == 2
        assert cb.name == "test_breaker"
        assert cb.state == CircuitState.CLOSED
        assert cb.failure_count == 0
        assert cb.last_failure_time == 0
        assert cb._half_open_calls == 0
        assert cb._metrics["success_count"] == 0
        assert cb._metrics["failure_count"] == 0
        assert cb._metrics["rejected_count"] == 0
        assert len(cb._metrics["state_changes"]) == 0

    @pytest.mark.asyncio
    async def test_circuit_breaker_execute_success(self):
        """Test CircuitBreaker execute with successful function."""
        cb = CircuitBreaker(failure_threshold=3, name="test_breaker")

        # Create a mock async function that succeeds
        mock_func = AsyncMock(return_value="success")

        # Execute the function through the circuit breaker
        result = await cb.execute(mock_func, "arg1", kwarg1="value1")

        assert result == "success"
        mock_func.assert_called_once_with("arg1", kwarg1="value1")
        assert cb.state == CircuitState.CLOSED
        assert cb._metrics["success_count"] == 1
        assert cb._metrics["failure_count"] == 0

    @pytest.mark.asyncio
    async def test_circuit_breaker_execute_failure(self):
        """Test CircuitBreaker execute with failing function."""
        cb = CircuitBreaker(failure_threshold=2, name="test_breaker")

        # Create a mock async function that fails
        mock_func = AsyncMock(side_effect=ValueError("test error"))

        # Execute the function through the circuit breaker
        with pytest.raises(ValueError) as excinfo:
            await cb.execute(mock_func)

        assert "test error" in str(excinfo.value)
        assert cb.state == CircuitState.CLOSED
        assert cb.failure_count == 1
        assert cb._metrics["success_count"] == 0
        assert cb._metrics["failure_count"] == 1

        # Execute again to trigger circuit open
        with pytest.raises(ValueError):
            await cb.execute(mock_func)

        assert cb.state == CircuitState.OPEN
        assert cb.failure_count == 2
        assert cb._metrics["failure_count"] == 2

    @pytest.mark.asyncio
    async def test_circuit_breaker_open_state(self):
        """Test CircuitBreaker in open state."""
        cb = CircuitBreaker(
            failure_threshold=1,
            recovery_time=60.0,
            name="test_breaker",
        )

        # Create a mock async function that fails
        mock_func = AsyncMock(side_effect=ValueError("test error"))

        # Execute to trigger circuit open
        with pytest.raises(ValueError):
            await cb.execute(mock_func)

        assert cb.state == CircuitState.OPEN

        # Try to execute again, should be rejected
        with pytest.raises(CircuitBreakerOpenError) as excinfo:
            await cb.execute(mock_func)

        assert "Circuit breaker 'test_breaker' is open" in str(excinfo.value)
        assert cb._metrics["rejected_count"] == 1
        mock_func.assert_called_once()  # Function should only be called once

    @pytest.mark.asyncio
    async def test_circuit_breaker_half_open_state(self):
        """Test CircuitBreaker transition to half-open state."""
        cb = CircuitBreaker(
            failure_threshold=1,
            recovery_time=0.1,  # Short recovery time for testing
            name="test_breaker",
        )

        # Create a mock async function that fails then succeeds
        mock_func = AsyncMock(side_effect=[ValueError("test error"), "success"])

        # Execute to trigger circuit open
        with pytest.raises(ValueError):
            await cb.execute(mock_func)

        assert cb.state == CircuitState.OPEN

        # Wait for recovery time to elapse
        await asyncio.sleep(0.2)

        # Execute again, should transition to half-open and allow the call
        result = await cb.execute(mock_func)

        assert result == "success"
        assert (
            cb.state == CircuitState.CLOSED
        )  # Success in half-open state closes the circuit
        assert mock_func.call_count == 2

    @pytest.mark.asyncio
    async def test_circuit_breaker_excluded_exceptions(self):
        """Test CircuitBreaker with excluded exceptions."""
        cb = CircuitBreaker(
            failure_threshold=2,
            excluded_exceptions={KeyError},
            name="test_breaker",
        )

        # Create a mock async function that raises excluded exception
        mock_func = AsyncMock(side_effect=KeyError("excluded error"))

        # Execute the function through the circuit breaker
        with pytest.raises(KeyError):
            await cb.execute(mock_func)

        # Excluded exception should not count as a failure
        assert cb.state == CircuitState.CLOSED
        assert cb.failure_count == 0
        assert cb._metrics["failure_count"] == 0

    @pytest.mark.asyncio
    async def test_circuit_breaker_decorator(self):
        """Test circuit_breaker decorator."""
        # Create a mock async function
        mock_func = AsyncMock(return_value="success")

        # Apply the decorator
        decorated_func = circuit_breaker(
            failure_threshold=2,
            recovery_time=5.0,
            name="test_decorator",
        )(mock_func)

        # Call the decorated function
        result = await decorated_func("arg1", kwarg1="value1")

        assert result == "success"
        mock_func.assert_called_once_with("arg1", kwarg1="value1")


class TestRetry:
    """Tests for retry functionality."""

    @pytest.mark.asyncio
    async def test_retry_with_backoff_success(self):
        """Test retry_with_backoff with successful function."""
        # Create a mock async function that succeeds
        mock_func = AsyncMock(return_value="success")

        # Call with retry
        result = await retry_with_backoff(
            mock_func,
            "arg1",
            kwarg1="value1",
            max_retries=3,
            base_delay=0.1,
        )

        assert result == "success"
        mock_func.assert_called_once_with("arg1", kwarg1="value1")

    @pytest.mark.asyncio
    async def test_retry_with_backoff_retry_success(self):
        """Test retry_with_backoff with function that fails then succeeds."""
        # Create a mock async function that fails twice then succeeds
        mock_func = AsyncMock(
            side_effect=[
                ValueError("error 1"),
                ValueError("error 2"),
                "success",
            ]
        )

        # Call with retry
        result = await retry_with_backoff(
            mock_func,
            max_retries=3,
            base_delay=0.01,  # Small delay for testing
            backoff_factor=1.0,  # No backoff for testing
        )

        assert result == "success"
        assert mock_func.call_count == 3

    @pytest.mark.asyncio
    async def test_retry_with_backoff_max_retries(self):
        """Test retry_with_backoff with function that always fails."""
        # Create a mock async function that always fails
        mock_func = AsyncMock(side_effect=ValueError("persistent error"))

        # Call with retry
        with pytest.raises(ValueError) as excinfo:
            await retry_with_backoff(
                mock_func,
                max_retries=2,
                base_delay=0.01,  # Small delay for testing
            )

        assert "persistent error" in str(excinfo.value)
        assert mock_func.call_count == 3  # Initial call + 2 retries

    @pytest.mark.asyncio
    async def test_retry_with_backoff_excluded_exceptions(self):
        """Test retry_with_backoff with excluded exceptions."""
        # Create a mock async function that raises excluded exception
        mock_func = AsyncMock(side_effect=KeyError("excluded error"))

        # Call with retry
        with pytest.raises(KeyError) as excinfo:
            await retry_with_backoff(
                mock_func,
                max_retries=2,
                base_delay=0.01,
                exclude_exceptions=(KeyError,),
            )

        assert "excluded error" in str(excinfo.value)
        mock_func.assert_called_once()  # Should not retry excluded exceptions

    @pytest.mark.asyncio
    async def test_retry_config(self):
        """Test RetryConfig class."""
        config = RetryConfig(
            max_retries=5,
            base_delay=0.5,
            max_delay=10.0,
            backoff_factor=2.0,
            jitter=True,
            jitter_factor=0.1,
            retry_exceptions=(ValueError, TypeError),
            exclude_exceptions=(KeyError,),
        )

        kwargs = config.as_kwargs()

        assert kwargs["max_retries"] == 5
        assert kwargs["base_delay"] == 0.5
        assert kwargs["max_delay"] == 10.0
        assert kwargs["backoff_factor"] == 2.0
        assert kwargs["jitter"] is True
        assert kwargs["jitter_factor"] == 0.1
        assert kwargs["retry_exceptions"] == (ValueError, TypeError)
        assert kwargs["exclude_exceptions"] == (KeyError,)

    @pytest.mark.asyncio
    async def test_with_retry_decorator(self):
        """Test with_retry decorator."""
        # Create a mock async function
        mock_func = AsyncMock(return_value="success")

        # Apply the decorator
        decorated_func = with_retry(
            max_retries=3,
            base_delay=0.1,
        )(mock_func)

        # Call the decorated function
        result = await decorated_func("arg1", kwarg1="value1")

        assert result == "success"
        mock_func.assert_called_once_with("arg1", kwarg1="value1")
