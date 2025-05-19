"""
Unit tests for the AsyncAPIClient class.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from lionfuncs.errors import (
    APIClientError,
    APIConnectionError,
    APITimeoutError,
    AuthenticationError,
    RateLimitError,
    ResourceNotFoundError,
    ServerError,
)
from lionfuncs.network.client import AsyncAPIClient
from lionfuncs.network.resilience import CircuitBreaker, RetryConfig


@pytest.fixture
def mock_httpx_client():
    """Fixture for mocking httpx.AsyncClient."""
    with patch("httpx.AsyncClient") as mock_client:
        # Create a mock response
        mock_response = MagicMock()
        mock_response.json.return_value = {"data": "test"}
        mock_response.raise_for_status = MagicMock()
        mock_response.is_closed = False
        mock_response.close = MagicMock()
        mock_response.text = "Response text"

        # Set up the mock client
        client_instance = mock_client.return_value
        client_instance.request = AsyncMock(
            return_value=mock_response
        )  # Use AsyncMock for async methods
        client_instance.aclose = AsyncMock()  # Use AsyncMock for async methods

        yield client_instance, mock_response


@pytest.mark.asyncio
async def test_async_api_client_init():
    """Test AsyncAPIClient initialization."""
    client = AsyncAPIClient(base_url="https://api.example.com")
    assert client.base_url == "https://api.example.com"
    assert client.timeout == 10.0
    assert client.headers == {}
    assert client.auth is None
    assert client._client is None
    assert client._closed is False
    assert client.circuit_breaker is None
    assert client.retry_config is None


@pytest.mark.asyncio
async def test_async_api_client_get_client(mock_httpx_client):
    """Test _get_client method."""
    mock_client, _ = mock_httpx_client

    client = AsyncAPIClient(base_url="https://api.example.com")
    result = await client._get_client()

    assert result == mock_client
    assert client._client == mock_client

    # Second call should return the same client
    result2 = await client._get_client()
    assert result2 == mock_client

    # httpx.AsyncClient should be called with the correct arguments
    httpx.AsyncClient.assert_called_once_with(
        base_url="https://api.example.com",
        timeout=10.0,
        headers={},
        auth=None,
    )


@pytest.mark.asyncio
async def test_async_api_client_close(mock_httpx_client):
    """Test close method."""
    mock_client, _ = mock_httpx_client

    client = AsyncAPIClient(base_url="https://api.example.com")
    await client._get_client()  # Initialize client

    await client.close()

    assert client._closed is True
    assert client._client is None
    mock_client.aclose.assert_called_once()

    # Second call should do nothing
    await client.close()
    mock_client.aclose.assert_called_once()


@pytest.mark.asyncio
async def test_async_api_client_context_manager(mock_httpx_client):
    """Test async context manager protocol."""
    mock_client, _ = mock_httpx_client

    async with AsyncAPIClient(base_url="https://api.example.com") as client:
        assert client._client == mock_client
        assert client._closed is False

    assert client._closed is True
    mock_client.aclose.assert_called_once()


@pytest.mark.asyncio
async def test_async_api_client_request_success(mock_httpx_client):
    """Test request method with successful response."""
    mock_client, mock_response = mock_httpx_client

    client = AsyncAPIClient(base_url="https://api.example.com")
    result = await client.request("GET", "/endpoint")

    assert result == {"data": "test"}
    mock_client.request.assert_called_once_with("GET", "/endpoint")
    mock_response.raise_for_status.assert_called_once()
    mock_response.json.assert_called_once()


@pytest.mark.asyncio
async def test_async_api_client_request_connection_error(mock_httpx_client):
    """Test request method with connection error."""
    mock_client, _ = mock_httpx_client
    mock_client.request.side_effect = httpx.ConnectError("Connection error")

    client = AsyncAPIClient(base_url="https://api.example.com")

    with pytest.raises(APIConnectionError) as excinfo:
        await client.request("GET", "/endpoint")

    assert "Connection error" in str(excinfo.value)


@pytest.mark.asyncio
async def test_async_api_client_request_timeout_error(mock_httpx_client):
    """Test request method with timeout error."""
    mock_client, _ = mock_httpx_client
    mock_client.request.side_effect = httpx.TimeoutException("Timeout error")

    client = AsyncAPIClient(base_url="https://api.example.com")

    with pytest.raises(APITimeoutError) as excinfo:
        await client.request("GET", "/endpoint")

    assert "Timeout error" in str(excinfo.value)


@pytest.mark.asyncio
async def test_async_api_client_request_http_status_errors(mock_httpx_client):
    """Test request method with HTTP status errors."""
    mock_client, mock_response = mock_httpx_client

    # Test cases for different status codes
    test_cases = [
        (401, AuthenticationError, "Authentication error"),
        (404, ResourceNotFoundError, "Resource not found"),
        (429, RateLimitError, "Rate limit exceeded"),
        (500, ServerError, "Server error"),
        (400, APIClientError, "API error"),
    ]

    for status_code, error_class, error_message in test_cases:
        # Reset mocks
        mock_client.reset_mock()
        mock_response.reset_mock()

        # Set up the mock response for this test case
        mock_response.json.return_value = {"detail": error_message}
        mock_response.text = error_message
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            message=f"HTTP Error {status_code}",
            request=MagicMock(),
            response=MagicMock(
                status_code=status_code,
                headers={"X-Test": "test"},
                text=error_message,
            ),
        )

        client = AsyncAPIClient(base_url="https://api.example.com")

        with pytest.raises(error_class) as excinfo:
            await client.request("GET", "/endpoint")

        assert error_message in str(excinfo.value)
        if hasattr(excinfo.value, "status_code"):
            assert excinfo.value.status_code == status_code
        if hasattr(excinfo.value, "response_content"):
            assert error_message in excinfo.value.response_content


@pytest.mark.asyncio
async def test_async_api_client_request_with_retry(mock_httpx_client):
    """Test request method with retry configuration."""
    mock_client, mock_response = mock_httpx_client

    # Set up the retry config
    retry_config = RetryConfig(
        max_retries=2,
        base_delay=0.1,
        retry_exceptions=(APITimeoutError,),
    )

    # First call fails with timeout, second call succeeds
    mock_client.request.side_effect = [
        httpx.TimeoutException("Timeout error"),
        mock_response,
    ]

    client = AsyncAPIClient(
        base_url="https://api.example.com",
        retry_config=retry_config,
    )

    result = await client.request("GET", "/endpoint")

    assert result == {"data": "test"}
    assert mock_client.request.call_count == 2


@pytest.mark.asyncio
async def test_async_api_client_request_with_circuit_breaker(mock_httpx_client):
    """Test request method with circuit breaker."""
    mock_client, mock_response = mock_httpx_client

    # Set up the circuit breaker
    circuit_breaker = CircuitBreaker(
        failure_threshold=2,
        recovery_time=0.1,
    )

    client = AsyncAPIClient(
        base_url="https://api.example.com",
        circuit_breaker=circuit_breaker,
    )

    # First call succeeds
    result = await client.request("GET", "/endpoint")
    assert result == {"data": "test"}

    # Reset mock for next call
    mock_client.reset_mock()
    mock_response.reset_mock()

    # Second call fails
    mock_client.request.side_effect = httpx.ConnectError("Connection error")

    with pytest.raises(APIConnectionError):
        await client.request("GET", "/endpoint")

    # Circuit should still be closed (1 failure)
    assert circuit_breaker.state.value == "closed"

    # Reset mock for next call
    mock_client.reset_mock()

    # Third call fails, should open the circuit
    with pytest.raises(APIConnectionError):
        await client.request("GET", "/endpoint")

    # Circuit should be open now (2 failures)
    assert circuit_breaker.state.value == "open"


@pytest.mark.asyncio
async def test_async_api_client_call(mock_httpx_client):
    """Test call method."""
    mock_client, _ = mock_httpx_client

    client = AsyncAPIClient(base_url="https://api.example.com")

    # Test with different HTTP methods
    request_data = {
        "method": "GET",
        "url": "/endpoint",
        "params": {"param": "value"},
        "json": {"data": "test"},
        "data": "raw data",
        "extra": "value",
    }

    await client.call(request_data)

    mock_client.request.assert_called_once_with(
        "GET",
        "/endpoint",
        params={"param": "value"},
        json={"data": "test"},
        data="raw data",
        extra="value",
    )
