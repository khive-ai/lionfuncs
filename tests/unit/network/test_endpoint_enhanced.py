"""
Enhanced unit tests for the Endpoint class to increase coverage.
"""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from lionfuncs.network.endpoint import Endpoint
from lionfuncs.network.primitives import (
    HttpTransportConfig,
    SdkTransportConfig,
    ServiceEndpointConfig,
)


@pytest.fixture
def http_config():
    """Fixture for HTTP transport config."""
    return ServiceEndpointConfig(
        name="test_http",
        transport_type="http",
        base_url="https://api.example.com",
        http_config=HttpTransportConfig(),
    )


@pytest.fixture
def sdk_config():
    """Fixture for SDK transport config."""
    return ServiceEndpointConfig(
        name="test_sdk",
        transport_type="sdk",
        api_key="test_api_key",
        sdk_config=SdkTransportConfig(sdk_provider_name="openai"),
    )


class TestEndpointEnhanced:
    """Enhanced tests for the Endpoint class."""

    @pytest.mark.asyncio
    async def test_get_client_concurrent_calls(self, http_config):
        """Test that concurrent calls to get_client only create one client."""
        with patch("lionfuncs.network.endpoint.AsyncAPIClient") as mock_client_class:
            mock_client = mock_client_class.return_value
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)

            endpoint = Endpoint(http_config)

            # Create multiple concurrent calls to get_client
            async def get_client_task():
                return await endpoint.get_client()

            # Run multiple tasks concurrently
            tasks = [get_client_task() for _ in range(5)]
            results = await asyncio.gather(*tasks)

            # All tasks should return the same client instance
            assert all(result == mock_client for result in results)
            # Client should only be created once
            mock_client_class.assert_called_once()
            mock_client.__aenter__.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_client_with_custom_kwargs(self):
        """Test _create_client with custom constructor kwargs."""
        # Create config with custom constructor kwargs
        custom_http_config = ServiceEndpointConfig(
            name="test_custom_http",
            transport_type="http",
            base_url="https://api.example.com",
            http_config=HttpTransportConfig(),
            # Don't include timeout in constructor_kwargs since it's already a parameter
            client_constructor_kwargs={"follow_redirects": True},
        )

        with patch("lionfuncs.network.endpoint.AsyncAPIClient") as mock_client_class:
            endpoint = Endpoint(custom_http_config)
            await endpoint._create_client()

            # Verify custom kwargs were passed
            mock_client_class.assert_called_once_with(
                base_url="https://api.example.com",
                timeout=60.0,  # Default timeout
                headers={},
                follow_redirects=True,  # Custom kwarg
            )

    @pytest.mark.asyncio
    async def test_create_client_sdk_with_custom_kwargs(self):
        """Test _create_client for SDK with custom constructor kwargs."""
        # Create config with custom constructor kwargs
        custom_sdk_config = ServiceEndpointConfig(
            name="test_custom_sdk",
            transport_type="sdk",
            api_key="test_api_key",
            sdk_config=SdkTransportConfig(sdk_provider_name="openai"),
            client_constructor_kwargs={"organization": "org-123", "base_url": "https://custom.openai.com"},
        )

        with patch("lionfuncs.network.endpoint.create_sdk_adapter") as mock_create_adapter:
            endpoint = Endpoint(custom_sdk_config)
            await endpoint._create_client()

            # Verify custom kwargs were passed
            mock_create_adapter.assert_called_once_with(
                provider="openai",
                api_key="test_api_key",
                organization="org-123",  # Custom kwarg
                base_url="https://custom.openai.com",  # Custom kwarg
            )

    @pytest.mark.asyncio
    async def test_close_with_no_client(self, http_config):
        """Test close method when no client has been created."""
        endpoint = Endpoint(http_config)
        # Close without ever creating a client
        await endpoint.close()
        assert endpoint._closed is True
        assert endpoint._client_instance is None

    @pytest.mark.asyncio
    async def test_close_with_client_no_close_method(self, http_config):
        """Test close method with a client that has no close method or __aexit__."""
        # Create a mock client without close method or __aexit__
        mock_client = MagicMock()
        # Explicitly remove close and __aexit__
        if hasattr(mock_client, "close"):
            delattr(mock_client, "close")
        # Don't set __aexit__ to None, just remove it if it exists
        if hasattr(mock_client, "__aexit__"):
            delattr(mock_client, "__aexit__")

        endpoint = Endpoint(http_config)
        endpoint._client_instance = mock_client  # Manually set client

        # Close should still work without errors
        await endpoint.close()
        assert endpoint._client_instance is None
        assert endpoint._closed is True

    @pytest.mark.asyncio
    async def test_get_client_after_close(self, http_config):
        """Test that get_client raises RuntimeError after endpoint is closed."""
        endpoint = Endpoint(http_config)
        await endpoint.close()  # Close the endpoint

        with pytest.raises(RuntimeError, match="Endpoint .* is closed"):
            await endpoint.get_client()

    @pytest.mark.asyncio
    async def test_context_manager_with_exception(self, http_config):
        """Test async context manager when an exception occurs."""
        # This test is tricky because the context manager's __aexit__ is called during exception handling
        # Let's use a different approach to test this behavior
        
        # Create a custom Endpoint class that we can track
        class TestEndpoint(Endpoint):
            def __init__(self, config):
                super().__init__(config)
                self.close_called = False
                
            async def close(self):
                self.close_called = True
                await super().close()
        
        # Create a client that will be used by the endpoint
        mock_client = MagicMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock()
        
        with patch("lionfuncs.network.endpoint.AsyncAPIClient", return_value=mock_client):
            # Create our test endpoint
            endpoint = TestEndpoint(http_config)
            
            # Use as async context manager with an exception
            try:
                async with endpoint:
                    # Verify client was initialized
                    assert endpoint._client_instance == mock_client
                    # Raise an exception
                    raise ValueError("Test exception")
            except ValueError:
                pass  # Expected exception
            
            # Verify close was called
            assert endpoint.close_called