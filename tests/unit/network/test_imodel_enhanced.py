"""
Enhanced unit tests for the iModel class to increase coverage.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from pydantic import BaseModel

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


class TestIModelEnhanced:
    """Enhanced test cases for the iModel class."""

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
        mock_config.default_request_kwargs = {"timeout": 30.0}
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
        mock_config.default_request_kwargs = {"model": "gpt-4"}
        mock_endpoint.config = mock_config

        return mock_endpoint, mock_adapter

    @pytest.mark.asyncio
    async def test_invoke_http_with_pydantic_model(self, mock_executor, mock_http_endpoint):
        """Test invoke method with a Pydantic model as request_payload."""
        mock_endpoint, mock_client = mock_http_endpoint
        model = iModel(endpoint=mock_endpoint, executor=mock_executor)

        # Mock the client's request method
        mock_client.request = AsyncMock(return_value={"result": "success"})

        # Mock the executor's submit_task method
        mock_event = MagicMock(spec=NetworkRequestEvent)
        mock_executor.submit_task.return_value = mock_event

        # Create a Pydantic model for the request payload
        class CompletionRequest(BaseModel):
            prompt: str
            max_tokens: int = 100
            temperature: float = 0.7

        request = CompletionRequest(prompt="Hello, world!")

        # Call invoke with the Pydantic model
        result = await model.invoke(
            request_payload=request,
            http_path="v1/completions",
            http_method="POST",
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
        assert "payload" in call_args
        assert call_args["payload"]["prompt"] == "Hello, world!"
        assert call_args["payload"]["max_tokens"] == 100
        assert call_args["payload"]["temperature"] == 0.7

    @pytest.mark.asyncio
    async def test_invoke_http_with_get_method(self, mock_executor, mock_http_endpoint):
        """Test invoke method with HTTP GET method."""
        mock_endpoint, mock_client = mock_http_endpoint
        model = iModel(endpoint=mock_endpoint, executor=mock_executor)

        # Mock the client's request method
        mock_client.request = AsyncMock(return_value={"result": "success"})

        # Mock the executor's submit_task method
        mock_event = MagicMock(spec=NetworkRequestEvent)
        mock_executor.submit_task.return_value = mock_event

        # Call invoke with GET method
        result = await model.invoke(
            request_payload={"query": "test", "limit": 10},
            http_path="v1/search",
            http_method="GET",
        )

        # Verify the result
        assert result == mock_event

        # Verify that endpoint.get_client was called
        mock_endpoint.get_client.assert_called_once()

        # Verify that executor.submit_task was called with correct parameters
        mock_executor.submit_task.assert_called_once()
        call_args = mock_executor.submit_task.call_args[1]
        assert callable(call_args["api_call_coroutine"])
        assert call_args["endpoint_url"] == "https://api.example.com/v1/search"
        assert call_args["method"] == "GET"
        
        # For GET requests, payload should be in params, not json
        api_coro = call_args["api_call_coroutine"]
        mock_client.request.reset_mock()
        await api_coro()
        mock_client.request.assert_called_once()
        client_call_args = mock_client.request.call_args[1]
        assert "params" in client_call_args
        assert client_call_args["params"] == {"query": "test", "limit": 10}
        assert "json" not in client_call_args or client_call_args["json"] is None

    @pytest.mark.asyncio
    async def test_invoke_http_with_default_request_kwargs(self, mock_executor, mock_http_endpoint):
        """Test invoke method with default_request_kwargs from endpoint config."""
        mock_endpoint, mock_client = mock_http_endpoint
        model = iModel(endpoint=mock_endpoint, executor=mock_executor)

        # Mock the client's request method
        mock_client.request = AsyncMock(return_value={"result": "success"})

        # Call invoke
        await model.invoke(
            request_payload={"prompt": "Hello"},
            http_path="v1/completions",
        )

        # Execute the api_call_coroutine to verify default_request_kwargs are used
        call_args = mock_executor.submit_task.call_args[1]
        api_call_coroutine = call_args["api_call_coroutine"]
        
        mock_client.request.reset_mock()
        await api_call_coroutine()
        
        # Verify that request was called with the default timeout from config
        mock_client.request.assert_called_once()
        client_call_args = mock_client.request.call_args[1]
        assert client_call_args["timeout"] == 30.0

    @pytest.mark.asyncio
    async def test_invoke_sdk_with_non_dict_payload(self, mock_executor, mock_sdk_endpoint):
        """Test invoke method with SDK transport and non-dict payload."""
        mock_endpoint, mock_adapter = mock_sdk_endpoint
        model = iModel(endpoint=mock_endpoint, executor=mock_executor)

        # Mock the adapter's call method
        mock_adapter.call = AsyncMock(return_value={"result": "success"})

        # Mock the executor's submit_task method
        mock_event = MagicMock(spec=NetworkRequestEvent)
        mock_executor.submit_task.return_value = mock_event

        # Call invoke with a non-dict payload (string)
        with patch("lionfuncs.network.imodel.logger") as mock_logger:
            result = await model.invoke(
                request_payload="This is a raw text prompt",
                sdk_method_name="completions.create",
            )

        # Verify that a warning was logged
        mock_logger.warning.assert_called_once()
        assert "Non-dict request_payload for SDK call" in mock_logger.warning.call_args[0][0]

        # Verify the result
        assert result == mock_event

    @pytest.mark.asyncio
    async def test_invoke_with_unsupported_transport_type(self, mock_executor):
        """Test invoke method with unsupported transport type."""
        # Create a mock endpoint with an unsupported transport type
        mock_endpoint = MagicMock(spec=Endpoint)
        mock_client = MagicMock()
        mock_endpoint.get_client = AsyncMock(return_value=mock_client)
        # Configure the endpoint's config with an unsupported transport type
        mock_config = MagicMock(spec=ServiceEndpointConfig)
        mock_config.name = "test-invalid-endpoint"
        mock_config.transport_type = "invalid"  # Invalid transport type
        # Need to add default_request_kwargs to avoid AttributeError
        mock_config.default_request_kwargs = {}
        mock_endpoint.config = mock_config

        model = iModel(endpoint=mock_endpoint, executor=mock_executor)

        # Call invoke should raise TypeError
        with pytest.raises(TypeError, match="Unsupported transport_type"):
            await model.invoke(
                request_payload={"prompt": "Hello"},
            )

    @pytest.mark.asyncio
    async def test_invoke_http_client_without_request_method(self, mock_executor, mock_http_endpoint):
        """Test invoke method with HTTP client that doesn't have a request method."""
        mock_endpoint, mock_client = mock_http_endpoint
        
        # Remove the request method from the client
        delattr(mock_client, "request")
        
        model = iModel(endpoint=mock_endpoint, executor=mock_executor)

        # Call invoke should raise TypeError
        with pytest.raises(TypeError, match="HTTP client does not have a 'request' method"):
            await model.invoke(
                request_payload={"prompt": "Hello"},
                http_path="v1/completions",
            )

    @pytest.mark.asyncio
    async def test_invoke_sdk_adapter_without_call_method(self, mock_executor, mock_sdk_endpoint):
        """Test invoke method with SDK adapter that doesn't have a call method."""
        mock_endpoint, mock_adapter = mock_sdk_endpoint
        
        # Remove the call method from the adapter
        delattr(mock_adapter, "call")
        
        model = iModel(endpoint=mock_endpoint, executor=mock_executor)

        # Call invoke should raise TypeError
        with pytest.raises(TypeError, match="SDK client does not have a 'call' method"):
            await model.invoke(
                request_payload={"messages": [{"role": "user", "content": "Hello"}]},
                sdk_method_name="chat.completions.create",
            )

    @pytest.mark.asyncio
    async def test_acompletion_sdk(self, mock_executor, mock_sdk_endpoint):
        """Test acompletion method with SDK transport."""
        mock_endpoint, _ = mock_sdk_endpoint
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
        assert call_args["sdk_method_name"] == "completions.create"
        assert call_args["num_api_tokens_needed"] == 10
        assert call_args["metadata"]["model_name"] == "gpt-4"

    @pytest.mark.asyncio
    async def test_invoke_with_unexpected_error(self, mock_executor, mock_http_endpoint):
        """Test invoke method with an unexpected error."""
        mock_endpoint, mock_client = mock_http_endpoint
        model = iModel(endpoint=mock_endpoint, executor=mock_executor)

        # Mock the client's request method to raise an unexpected error
        unexpected_error = RuntimeError("Unexpected error")
        mock_client.request = AsyncMock(side_effect=unexpected_error)

        # Mock the executor's submit_task method
        mock_event = MagicMock(spec=NetworkRequestEvent)
        mock_executor.submit_task.return_value = mock_event

        # Call invoke
        result = await model.invoke(
            request_payload={"prompt": "Hello"},
            http_path="v1/completions",
        )

        # Verify the result
        assert result == mock_event

        # Execute the api_call_coroutine to verify error handling
        call_args = mock_executor.submit_task.call_args[1]
        api_call_coroutine = call_args["api_call_coroutine"]

        # The unexpected error should be propagated
        with pytest.raises(RuntimeError, match="Unexpected error"):
            await api_call_coroutine()