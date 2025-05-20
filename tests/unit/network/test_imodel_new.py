"""
Unit tests for the refactored iModel class.
"""

from unittest.mock import AsyncMock, MagicMock

import pytest

from lionfuncs.errors import APIClientError, LionSDKError
from lionfuncs.network.adapters import AbstractSDKAdapter
from lionfuncs.network.client import AsyncAPIClient
from lionfuncs.network.endpoint import Endpoint
from lionfuncs.network.events import NetworkRequestEvent
from lionfuncs.network.executor import Executor
from lionfuncs.network.imodel import iModel
from lionfuncs.network.primitives import (
    HttpTransportConfig,
    SdkTransportConfig,
    ServiceEndpointConfig,
)


class TestIModelNew:
    """Test cases for the refactored iModel class."""

    @pytest.fixture
    def mock_executor(self):
        """Create a mock Executor for testing."""
        mock = MagicMock(spec=Executor)
        mock.submit_task = AsyncMock()
        mock._is_running = True
        return mock

    @pytest.fixture
    def mock_http_endpoint(self):
        """Create a mock Endpoint with HTTP transport for testing."""
        mock_endpoint = MagicMock(spec=Endpoint)
        mock_client = MagicMock(spec=AsyncAPIClient)
        mock_endpoint.get_client = AsyncMock(return_value=mock_client)

        # Configure the endpoint's config
        mock_config = MagicMock(spec=ServiceEndpointConfig)
        mock_config.name = "test-http-endpoint"
        mock_config.transport_type = "http"
        mock_config.base_url = "https://api.example.com"
        mock_config.http_config = MagicMock(spec=HttpTransportConfig)
        mock_config.http_config.method = "POST"
        mock_config.sdk_config = None
        mock_config.default_request_kwargs = {}
        mock_endpoint.config = mock_config

        return mock_endpoint, mock_client

    @pytest.fixture
    def mock_sdk_endpoint(self):
        """Create a mock Endpoint with SDK transport for testing."""
        mock_endpoint = MagicMock(spec=Endpoint)
        mock_adapter = MagicMock(spec=AbstractSDKAdapter)
        mock_endpoint.get_client = AsyncMock(return_value=mock_adapter)

        # Configure the endpoint's config
        mock_config = MagicMock(spec=ServiceEndpointConfig)
        mock_config.name = "test-sdk-endpoint"
        mock_config.transport_type = "sdk"
        mock_config.base_url = None
        mock_config.http_config = None
        mock_config.sdk_config = MagicMock(spec=SdkTransportConfig)
        mock_config.sdk_config.sdk_provider_name = "openai"
        mock_config.sdk_config.default_sdk_method_name = "chat.completions.create"
        mock_config.default_request_kwargs = {}
        mock_endpoint.config = mock_config

        return mock_endpoint, mock_adapter

    @pytest.mark.asyncio
    async def test_init(self, mock_executor, mock_http_endpoint):
        """Test initialization."""
        mock_endpoint, _ = mock_http_endpoint
        model = iModel(endpoint=mock_endpoint, executor=mock_executor)

        assert model.endpoint == mock_endpoint
        assert model.executor == mock_executor

    @pytest.mark.asyncio
    async def test_invoke_http(self, mock_executor, mock_http_endpoint):
        """Test invoke method with HTTP transport."""
        mock_endpoint, mock_client = mock_http_endpoint
        model = iModel(endpoint=mock_endpoint, executor=mock_executor)

        # Mock the client's request method
        mock_client.request = AsyncMock(return_value={"result": "success"})

        # Mock the executor's submit_task method
        mock_event = MagicMock(spec=NetworkRequestEvent)
        mock_executor.submit_task.return_value = mock_event

        # Call invoke with HTTP parameters
        result = await model.invoke(
            request_payload={"prompt": "Hello"},
            http_path="v1/completions",
            http_method="POST",
            num_api_tokens_needed=10,
            metadata={"model": "gpt-4"},
        )

        # Verify the result
        assert result == mock_event

        # Verify that endpoint.get_client was called
        mock_endpoint.get_client.assert_called_once()

        # Verify that executor.submit_task was called with correct parameters
        mock_executor.submit_task.assert_called_once()
        call_args = mock_executor.submit_task.call_args[1]
        assert callable(call_args["api_call_coroutine"])
        assert call_args["endpoint_url"] == "https://api.example.com/v1/completions"
        assert call_args["method"] == "POST"
        assert call_args["num_api_tokens_needed"] == 10
        assert "endpoint_name" in call_args["metadata"]
        assert call_args["metadata"]["endpoint_name"] == "test-http-endpoint"
        assert call_args["metadata"]["model"] == "gpt-4"

    @pytest.mark.asyncio
    async def test_invoke_sdk(self, mock_executor, mock_sdk_endpoint):
        """Test invoke method with SDK transport."""
        mock_endpoint, mock_adapter = mock_sdk_endpoint
        model = iModel(endpoint=mock_endpoint, executor=mock_executor)

        # Mock the adapter's call method
        mock_adapter.call = AsyncMock(return_value={"result": "success"})

        # Mock the executor's submit_task method
        mock_event = MagicMock(spec=NetworkRequestEvent)
        mock_executor.submit_task.return_value = mock_event

        # Call invoke with SDK parameters
        result = await model.invoke(
            request_payload={"messages": [{"role": "user", "content": "Hello"}]},
            sdk_method_name="chat.completions.create",
            num_api_tokens_needed=10,
            metadata={"model": "gpt-4"},
        )

        # Verify the result
        assert result == mock_event

        # Verify that endpoint.get_client was called
        mock_endpoint.get_client.assert_called_once()

        # Verify that executor.submit_task was called with correct parameters
        mock_executor.submit_task.assert_called_once()
        call_args = mock_executor.submit_task.call_args[1]
        assert callable(call_args["api_call_coroutine"])
        assert call_args["endpoint_url"] == "sdk://openai/chat.completions.create"
        assert call_args["method"] == "SDK_CALL"
        assert call_args["num_api_tokens_needed"] == 10
        assert "endpoint_name" in call_args["metadata"]
        assert call_args["metadata"]["endpoint_name"] == "test-sdk-endpoint"
        assert call_args["metadata"]["model"] == "gpt-4"

    @pytest.mark.asyncio
    async def test_invoke_http_error_handling(self, mock_executor, mock_http_endpoint):
        """Test invoke method error handling with HTTP transport."""
        mock_endpoint, mock_client = mock_http_endpoint
        model = iModel(endpoint=mock_endpoint, executor=mock_executor)

        # Mock the client's request method to raise an error
        api_error = APIClientError("API error", status_code=400)
        mock_client.request = AsyncMock(side_effect=api_error)

        # Mock the executor's submit_task method
        mock_event = MagicMock(spec=NetworkRequestEvent)
        mock_executor.submit_task.return_value = mock_event

        # Call invoke
        result = await model.invoke(
            request_payload={"prompt": "Hello"}, http_path="v1/completions"
        )

        # Verify the result
        assert result == mock_event

        # Verify that endpoint.get_client was called
        mock_endpoint.get_client.assert_called_once()

        # Verify that executor.submit_task was called
        mock_executor.submit_task.assert_called_once()

        # Execute the api_call_coroutine to verify error handling
        call_args = mock_executor.submit_task.call_args[1]
        api_call_coroutine = call_args["api_call_coroutine"]

        with pytest.raises(APIClientError):
            await api_call_coroutine()

    @pytest.mark.asyncio
    async def test_invoke_sdk_error_handling(self, mock_executor, mock_sdk_endpoint):
        """Test invoke method error handling with SDK transport."""
        mock_endpoint, mock_adapter = mock_sdk_endpoint
        model = iModel(endpoint=mock_endpoint, executor=mock_executor)

        # Mock the adapter's call method to raise an error
        sdk_error = LionSDKError("SDK error")
        mock_adapter.call = AsyncMock(side_effect=sdk_error)

        # Mock the executor's submit_task method
        mock_event = MagicMock(spec=NetworkRequestEvent)
        mock_executor.submit_task.return_value = mock_event

        # Call invoke
        result = await model.invoke(
            request_payload={"messages": [{"role": "user", "content": "Hello"}]},
            sdk_method_name="chat.completions.create",
        )

        # Verify the result
        assert result == mock_event

        # Verify that endpoint.get_client was called
        mock_endpoint.get_client.assert_called_once()

        # Verify that executor.submit_task was called
        mock_executor.submit_task.assert_called_once()

        # Execute the api_call_coroutine to verify error handling
        call_args = mock_executor.submit_task.call_args[1]
        api_call_coroutine = call_args["api_call_coroutine"]

        with pytest.raises(LionSDKError):
            await api_call_coroutine()

    @pytest.mark.asyncio
    async def test_acompletion_http(self, mock_executor, mock_http_endpoint):
        """Test acompletion method with HTTP transport."""
        mock_endpoint, _ = mock_http_endpoint
        model = iModel(endpoint=mock_endpoint, executor=mock_executor)

        # Mock the invoke method
        model.invoke = AsyncMock()
        mock_event = MagicMock(spec=NetworkRequestEvent)
        model.invoke.return_value = mock_event

        # Call acompletion
        result = await model.acompletion(
            prompt="Hello, world!",
            max_tokens=100,
            temperature=0.7,
            num_tokens_to_consume=10,
            model="gpt-4",
        )

        # Verify the result
        assert result == mock_event

        # Verify that invoke was called with correct parameters
        model.invoke.assert_called_once()
        call_args = model.invoke.call_args[1]
        assert isinstance(call_args["request_payload"], dict)
        assert call_args["request_payload"]["prompt"] == "Hello, world!"
        assert call_args["request_payload"]["max_tokens"] == 100
        assert call_args["request_payload"]["temperature"] == 0.7
        assert call_args["request_payload"]["model"] == "gpt-4"
        assert call_args["http_path"] == "completions"
        assert call_args["http_method"] == "POST"
        assert call_args["num_api_tokens_needed"] == 10
        assert call_args["metadata"]["model_name"] == "gpt-4"

    @pytest.mark.asyncio
    async def test_context_manager(self, mock_executor, mock_http_endpoint):
        """Test context manager usage."""
        mock_endpoint, _ = mock_http_endpoint
        mock_endpoint.__aenter__ = AsyncMock(return_value=mock_endpoint)
        mock_endpoint.__aexit__ = AsyncMock()

        async with iModel(endpoint=mock_endpoint, executor=mock_executor) as model:
            assert model.endpoint == mock_endpoint
            mock_endpoint.__aenter__.assert_called_once()

        mock_endpoint.__aexit__.assert_called_once()
