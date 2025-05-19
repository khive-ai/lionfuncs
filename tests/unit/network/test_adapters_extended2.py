"""
Additional unit tests for the network adapters module to further increase coverage.
"""

from unittest.mock import patch

import pytest

from lionfuncs.network.adapters import (
    AnthropicAdapter,
    OpenAIAdapter,
    create_sdk_adapter,
)


class TestOpenAIAdapter:
    """Additional tests for the OpenAIAdapter class."""

    @pytest.mark.asyncio
    async def test_openai_adapter_reuse_client(self):
        """Test that _get_client reuses an existing client."""
        adapter = OpenAIAdapter(api_key="test_api_key")

        # Mock the AsyncOpenAI import
        with patch("openai.AsyncOpenAI") as mock_openai:
            # First call should create a new client
            client1 = await adapter._get_client()
            assert client1 == mock_openai.return_value
            mock_openai.assert_called_once()

            # Second call should reuse the existing client
            mock_openai.reset_mock()
            client2 = await adapter._get_client()
            assert client2 == client1
            mock_openai.assert_not_called()


class TestAnthropicAdapter:
    """Additional tests for the AnthropicAdapter class."""

    @pytest.mark.asyncio
    async def test_anthropic_adapter_reuse_client(self):
        """Test that _get_client reuses an existing client."""
        adapter = AnthropicAdapter(api_key="test_api_key")

        # Mock the Anthropic import
        with patch("anthropic.Anthropic") as mock_anthropic:
            # First call should create a new client
            client1 = await adapter._get_client()
            assert client1 == mock_anthropic.return_value
            mock_anthropic.assert_called_once()

            # Second call should reuse the existing client
            mock_anthropic.reset_mock()
            client2 = await adapter._get_client()
            assert client2 == client1
            mock_anthropic.assert_not_called()


def test_create_sdk_adapter_case_insensitive():
    """Test that create_sdk_adapter is case-insensitive."""
    with patch("lionfuncs.network.adapters.OpenAIAdapter") as mock_openai_adapter:
        with patch(
            "lionfuncs.network.adapters.AnthropicAdapter"
        ) as mock_anthropic_adapter:
            # Test with uppercase provider name
            adapter = create_sdk_adapter(
                provider="OPENAI",
                api_key="test_api_key",
            )

            assert adapter == mock_openai_adapter.return_value
            mock_openai_adapter.assert_called_once_with(
                api_key="test_api_key",
            )

            # Test with mixed case provider name
            adapter = create_sdk_adapter(
                provider="AnThrOpIc",
                api_key="test_api_key",
            )

            assert adapter == mock_anthropic_adapter.return_value
            mock_anthropic_adapter.assert_called_once_with(
                api_key="test_api_key",
            )
