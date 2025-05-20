"""
Unit tests for the network adapters module.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from lionfuncs.errors import LionSDKError
from lionfuncs.network.adapters import (
    AnthropicAdapter,
    BaseSDKAdapter,
    OpenAIAdapter,
    create_sdk_adapter,
)


class TestBaseSDKAdapter:
    """Tests for the BaseSDKAdapter class."""

    class MockSDKAdapter(BaseSDKAdapter):
        """Mock implementation of BaseSDKAdapter for testing."""

        async def _get_client(self):
            if self._closed:
                raise RuntimeError("Client is closed")

            if self._client is None:
                self._client = MagicMock()
                self._client.aclose = AsyncMock()  # Use AsyncMock for async methods

            return self._client

        async def call(self, method_name, **kwargs):
            await self._get_client()
            return f"Called {method_name} with {kwargs}"

    @pytest.mark.asyncio
    async def test_base_sdk_adapter_init(self):
        """Test BaseSDKAdapter initialization."""
        adapter = self.MockSDKAdapter(
            api_key="test_api_key",
            option1="value1",
            option2="value2",
        )

        assert adapter.api_key == "test_api_key"
        assert adapter.client_kwargs == {"option1": "value1", "option2": "value2"}
        assert adapter._client is None
        assert adapter._closed is False

    @pytest.mark.asyncio
    async def test_base_sdk_adapter_context_manager(self):
        """Test async context manager protocol."""
        async with self.MockSDKAdapter(api_key="test_api_key") as adapter:
            assert adapter._client is not None
            assert adapter._closed is False

        assert adapter._closed is True
        assert adapter._client is None

    @pytest.mark.asyncio
    async def test_base_sdk_adapter_close(self):
        """Test close method."""
        adapter = self.MockSDKAdapter(api_key="test_api_key")
        await adapter._get_client()  # Initialize client

        await adapter.close()

        assert adapter._closed is True
        assert adapter._client is None

        # Second call should do nothing
        await adapter.close()
        assert adapter._closed is True


class TestOpenAIAdapter:
    """Tests for the OpenAIAdapter class."""

    @pytest.mark.asyncio
    async def test_openai_adapter_get_client(self):
        """Test _get_client method."""
        # Create a mock for the openai module
        mock_openai_module = MagicMock()
        mock_openai_module.AsyncOpenAI = MagicMock()

        # Patch the import statement to return our mock module
        with patch.dict("sys.modules", {"openai": mock_openai_module}):
            adapter = OpenAIAdapter(api_key="test_api_key", organization="test_org")

            # Now we can call _get_client directly
            client = await adapter._get_client()

            # Verify the client was created correctly
            assert client is not None
            mock_openai_module.AsyncOpenAI.assert_called_once_with(
                api_key="test_api_key", organization="test_org"
            )

    @pytest.mark.asyncio
    async def test_openai_adapter_call(self):
        """Test call method."""
        # Create a mock client
        mock_client = MagicMock()
        chat_mock = MagicMock()
        completions_mock = MagicMock()
        create_mock = AsyncMock(return_value="test_response")

        chat_mock.completions = completions_mock
        completions_mock.create = create_mock
        mock_client.chat = chat_mock

        # Create the adapter and patch _get_client
        adapter = OpenAIAdapter(api_key="test_api_key")
        with patch.object(adapter, "_get_client", AsyncMock(return_value=mock_client)):
            # Call a nested method
            result = await adapter.call(
                "chat.completions.create",
                model="gpt-4",
                messages=[{"role": "user", "content": "Hello"}],
            )

            assert result == "test_response"
            create_mock.assert_called_once_with(
                model="gpt-4",
                messages=[{"role": "user", "content": "Hello"}],
            )

    @pytest.mark.asyncio
    async def test_openai_adapter_call_error(self):
        """Test call method with error."""
        # Create a mock client with an error
        mock_client = MagicMock()
        chat_mock = MagicMock()
        completions_mock = MagicMock()
        create_mock = AsyncMock(side_effect=Exception("API error"))

        chat_mock.completions = completions_mock
        completions_mock.create = create_mock
        mock_client.chat = chat_mock

        # Create the adapter and patch _get_client
        adapter = OpenAIAdapter(api_key="test_api_key")
        with patch.object(adapter, "_get_client", AsyncMock(return_value=mock_client)):
            with pytest.raises(LionSDKError) as excinfo:
                await adapter.call(
                    "chat.completions.create",
                    model="gpt-4",
                    messages=[{"role": "user", "content": "Hello"}],
                )

            assert "OpenAI SDK call failed: API error" in str(excinfo.value)


class TestAnthropicAdapter:
    """Tests for the AnthropicAdapter class."""

    @pytest.mark.asyncio
    async def test_anthropic_adapter_get_client(self):
        """Test _get_client method."""
        # Create a mock for the anthropic module
        mock_anthropic_module = MagicMock()
        mock_anthropic_module.Anthropic = MagicMock()

        # Patch the import statement to return our mock module
        with patch.dict("sys.modules", {"anthropic": mock_anthropic_module}):
            adapter = AnthropicAdapter(api_key="test_api_key", option1="value1")

            # Now we can call _get_client directly
            client = await adapter._get_client()

            # Verify the client was created correctly
            assert client is not None
            mock_anthropic_module.Anthropic.assert_called_once_with(
                api_key="test_api_key", option1="value1"
            )

    @pytest.mark.asyncio
    async def test_anthropic_adapter_call_sync_method(self):
        """Test call method with synchronous SDK method."""
        # Create a mock client
        mock_client = MagicMock()
        messages_mock = MagicMock()
        create_mock = MagicMock(return_value="test_response")

        messages_mock.create = create_mock
        mock_client.messages = messages_mock

        # Create the adapter and patch _get_client
        adapter = AnthropicAdapter(api_key="test_api_key")
        with patch.object(adapter, "_get_client", AsyncMock(return_value=mock_client)):
            # Mock asyncio.to_thread and asyncio.iscoroutinefunction
            with patch(
                "asyncio.to_thread", AsyncMock(return_value="test_response")
            ) as mock_to_thread:
                with patch("asyncio.iscoroutinefunction", return_value=False):
                    # Call a nested method
                    result = await adapter.call(
                        "messages.create",
                        model="claude-3-opus-20240229",
                        messages=[{"role": "user", "content": "Hello"}],
                    )

                    assert result == "test_response"
                    mock_to_thread.assert_called_once_with(
                        create_mock,
                        model="claude-3-opus-20240229",
                        messages=[{"role": "user", "content": "Hello"}],
                    )

    @pytest.mark.asyncio
    async def test_anthropic_adapter_call_async_method(self):
        """Test call method with asynchronous SDK method."""
        # Create a mock client
        mock_client = MagicMock()
        messages_mock = MagicMock()
        create_mock = AsyncMock(return_value="test_response")

        messages_mock.create = create_mock
        mock_client.messages = messages_mock

        # Create the adapter and patch _get_client
        adapter = AnthropicAdapter(api_key="test_api_key")
        with patch.object(adapter, "_get_client", AsyncMock(return_value=mock_client)):
            # Mock asyncio.iscoroutinefunction
            with patch("asyncio.iscoroutinefunction", return_value=True):
                # Call a nested method
                result = await adapter.call(
                    "messages.create",
                    model="claude-3-opus-20240229",
                    messages=[{"role": "user", "content": "Hello"}],
                )

                assert result == "test_response"
                create_mock.assert_called_once_with(
                    model="claude-3-opus-20240229",
                    messages=[{"role": "user", "content": "Hello"}],
                )

    @pytest.mark.asyncio
    async def test_anthropic_adapter_call_error(self):
        """Test call method with error."""
        # Create a mock client with an error
        mock_client = MagicMock()
        messages_mock = MagicMock()
        create_mock = MagicMock(side_effect=Exception("API error"))

        messages_mock.create = create_mock
        mock_client.messages = messages_mock

        # Create the adapter and patch _get_client
        adapter = AnthropicAdapter(api_key="test_api_key")
        with patch.object(adapter, "_get_client", AsyncMock(return_value=mock_client)):
            # Mock asyncio.to_thread and asyncio.iscoroutinefunction
            with patch(
                "asyncio.to_thread", AsyncMock(side_effect=Exception("API error"))
            ):
                with patch("asyncio.iscoroutinefunction", return_value=False):
                    with pytest.raises(LionSDKError) as excinfo:
                        await adapter.call(
                            "messages.create",
                            model="claude-3-opus-20240229",
                            messages=[{"role": "user", "content": "Hello"}],
                        )

                    assert "Anthropic SDK call failed: API error" in str(excinfo.value)


def test_create_sdk_adapter():
    """Test create_sdk_adapter function."""
    with patch("lionfuncs.network.adapters.OpenAIAdapter") as mock_openai_adapter:
        with patch(
            "lionfuncs.network.adapters.AnthropicAdapter"
        ) as mock_anthropic_adapter:
            # Test OpenAI adapter
            adapter = create_sdk_adapter(
                provider="openai",
                api_key="test_api_key",
                organization="test_org",
            )

            assert adapter == mock_openai_adapter.return_value
            mock_openai_adapter.assert_called_once_with(
                api_key="test_api_key",
                organization="test_org",
            )

            # Test Anthropic adapter
            adapter = create_sdk_adapter(
                provider="anthropic",
                api_key="test_api_key",
                option1="value1",
            )

            assert adapter == mock_anthropic_adapter.return_value
            mock_anthropic_adapter.assert_called_once_with(
                api_key="test_api_key",
                option1="value1",
            )

            # Test unsupported provider
            with pytest.raises(ValueError) as excinfo:
                create_sdk_adapter(
                    provider="unsupported",
                    api_key="test_api_key",
                )

            assert "Unsupported provider: unsupported" in str(excinfo.value)
