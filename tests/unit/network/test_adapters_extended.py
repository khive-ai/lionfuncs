"""
Extended unit tests for the network adapters module to increase coverage.
"""

from unittest.mock import MagicMock

import pytest

from lionfuncs.network.adapters import AnthropicAdapter, BaseSDKAdapter, OpenAIAdapter


class TestOpenAIAdapter:
    """Additional tests for the OpenAIAdapter class."""

    @pytest.mark.asyncio
    async def test_openai_adapter_client_closed(self):
        """Test _get_client when client is closed."""
        adapter = OpenAIAdapter(api_key="test_api_key")
        adapter._closed = True

        with pytest.raises(RuntimeError, match="Client is closed"):
            await adapter._get_client()


class TestAnthropicAdapter:
    """Additional tests for the AnthropicAdapter class."""

    @pytest.mark.asyncio
    async def test_anthropic_adapter_client_closed(self):
        """Test _get_client when client is closed."""
        adapter = AnthropicAdapter(api_key="test_api_key")
        adapter._closed = True

        with pytest.raises(RuntimeError, match="Client is closed"):
            await adapter._get_client()


class TestBaseSDKAdapterExtended:
    """Additional tests for the BaseSDKAdapter class."""

    class MockSDKAdapter(BaseSDKAdapter):
        """Mock implementation of BaseSDKAdapter for testing."""

        async def _get_client(self):
            if self._closed:
                raise RuntimeError("Client is closed")

            if self._client is None:
                self._client = MagicMock()
                # No aclose method, only close method
                self._client.close = MagicMock()

            return self._client

        async def call(self, method_name, **kwargs):
            _ = await self._get_client()
            return f"Called {method_name} with {kwargs}"

    @pytest.mark.asyncio
    async def test_base_sdk_adapter_close_with_sync_close(self):
        """Test close method with a client that only has sync close."""
        adapter = self.MockSDKAdapter(api_key="test_api_key")
        await adapter._get_client()  # Initialize client

        # Store a reference to the client for later assertion
        client = adapter._client

        # Ensure client has close
        assert hasattr(client, "close")

        # Remove aclose attribute if it exists
        if hasattr(client, "aclose"):
            delattr(client, "aclose")

        await adapter.close()

        # After close, the client should be None, so we need to use the stored reference
        client.close.assert_called_once()
        assert adapter._closed is True
        assert adapter._client is None
