"""
Unit tests for the Endpoint class.
"""

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


class TestEndpoint:
    """Tests for the Endpoint class."""

    @pytest.mark.asyncio
    async def test_init(self, http_config):
        """Test Endpoint initialization."""
        endpoint = Endpoint(http_config)

        assert endpoint.config == http_config
        assert endpoint._client_instance is None
        assert endpoint._closed is False

    @pytest.mark.asyncio
    async def test_create_client_http(self, http_config):
        """Test _create_client for HTTP transport."""
        with patch("lionfuncs.network.endpoint.AsyncAPIClient") as mock_client_class:
            mock_client = mock_client_class.return_value

            endpoint = Endpoint(http_config)
            client = await endpoint._create_client()

            assert client == mock_client
            mock_client_class.assert_called_once_with(
                base_url="https://api.example.com",
                timeout=60.0,
                headers={},
                **{},  # Empty client_kwargs
            )

    @pytest.mark.asyncio
    async def test_create_client_sdk(self, sdk_config):
        """Test _create_client for SDK transport."""
        with patch(
            "lionfuncs.network.endpoint.create_sdk_adapter"
        ) as mock_create_adapter:
            mock_adapter = MagicMock()
            mock_create_adapter.return_value = mock_adapter

            endpoint = Endpoint(sdk_config)
            client = await endpoint._create_client()

            assert client == mock_adapter
            mock_create_adapter.assert_called_once_with(
                provider="openai",
                api_key="test_api_key",
                **{},  # Empty client_kwargs
            )

    @pytest.mark.asyncio
    async def test_create_client_invalid_transport(self):
        """Test _create_client with invalid transport type."""
        # Create a config with an invalid transport type by bypassing validation
        invalid_config = ServiceEndpointConfig(
            name="test_invalid",
            transport_type="http",  # Start with valid type
            base_url="https://api.example.com",
        )
        # Hack to set an invalid transport type
        object.__setattr__(invalid_config, "transport_type", "invalid")

        endpoint = Endpoint(invalid_config)

        with pytest.raises(ValueError, match="Unsupported transport_type"):
            await endpoint._create_client()

    @pytest.mark.asyncio
    async def test_get_client_creates_once(self, http_config):
        """Test that get_client creates the client only once."""
        with patch("lionfuncs.network.endpoint.AsyncAPIClient") as mock_client_class:
            mock_client = mock_client_class.return_value
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)

            endpoint = Endpoint(http_config)

            # First call should create the client
            client1 = await endpoint.get_client()
            assert client1 == mock_client
            mock_client_class.assert_called_once()
            mock_client.__aenter__.assert_called_once()

            # Second call should return the same client without creating a new one
            mock_client_class.reset_mock()
            mock_client.__aenter__.reset_mock()

            client2 = await endpoint.get_client()
            assert client2 == mock_client
            mock_client_class.assert_not_called()
            mock_client.__aenter__.assert_not_called()

    @pytest.mark.asyncio
    async def test_get_client_closed_endpoint(self, http_config):
        """Test that get_client raises RuntimeError if endpoint is closed."""
        endpoint = Endpoint(http_config)
        endpoint._closed = True

        with pytest.raises(RuntimeError, match="Endpoint .* is closed"):
            await endpoint.get_client()

    @pytest.mark.asyncio
    async def test_close(self, http_config):
        """Test close method."""
        with patch("lionfuncs.network.endpoint.AsyncAPIClient") as mock_client_class:
            mock_client = mock_client_class.return_value
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock()
            # Make sure close is not defined to force using __aexit__
            if hasattr(mock_client, "close"):
                delattr(mock_client, "close")

            endpoint = Endpoint(http_config)
            await endpoint.get_client()  # Create and initialize client

            # Close the endpoint
            await endpoint.close()

            assert endpoint._client_instance is None
            assert endpoint._closed is True
            mock_client.__aexit__.assert_called_once_with(None, None, None)

            # Calling close again should be a no-op
            mock_client.__aexit__.reset_mock()
            await endpoint.close()
            mock_client.__aexit__.assert_not_called()

    @pytest.mark.asyncio
    async def test_close_with_sync_close_method(self, http_config):
        """Test close method with a client that has a synchronous close method."""
        # Create a mock client without using patch to avoid __aexit__ issues
        mock_client = MagicMock()
        # Explicitly set __aexit__ to None
        mock_client.__aexit__ = None
        # Add a synchronous close method
        mock_client.close = MagicMock()

        endpoint = Endpoint(http_config)
        endpoint._client_instance = mock_client  # Manually set client

        # Close the endpoint
        await endpoint.close()

        assert endpoint._client_instance is None
        assert endpoint._closed is True
        mock_client.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_close_with_async_close_method(self, http_config):
        """Test close method with a client that has an asynchronous close method."""
        # Create a mock client without using patch to avoid __aexit__ issues
        mock_client = MagicMock()
        # Explicitly set __aexit__ to None
        mock_client.__aexit__ = None
        # Add an asynchronous close method
        mock_client.close = AsyncMock()

        endpoint = Endpoint(http_config)
        endpoint._client_instance = mock_client  # Manually set client

        # Close the endpoint
        await endpoint.close()

        assert endpoint._client_instance is None
        assert endpoint._closed is True
        mock_client.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_async_context_manager(self, http_config):
        """Test async context manager protocol."""
        with patch("lionfuncs.network.endpoint.AsyncAPIClient") as mock_client_class:
            mock_client = mock_client_class.return_value
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock()
            # Make sure close is not defined to force using __aexit__
            if hasattr(mock_client, "close"):
                delattr(mock_client, "close")

            # Use as async context manager
            async with Endpoint(http_config) as endpoint:
                assert endpoint._client_instance == mock_client
                mock_client.__aenter__.assert_called_once()

            # Should be closed after exiting context
            assert endpoint._closed is True
            mock_client.__aexit__.assert_called_once_with(None, None, None)
