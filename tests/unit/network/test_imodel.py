# Copyright (c) 2023 - 2025, HaiyangLi <quantocean.li at gmail dot com>
#
# SPDX-License-Identifier: Apache-2.0

"""
Unit tests for the iModel class.
"""

import unittest
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from lionfuncs.network.events import NetworkRequestEvent
from lionfuncs.network.executor import Executor
from lionfuncs.network.imodel import iModel
from lionfuncs.network.primitives import EndpointConfig


class TestIModel:
    """Test cases for the iModel class."""

    @pytest.fixture
    def mock_executor(self):
        """Create a mock Executor for testing."""
        mock = MagicMock(spec=Executor)
        mock.submit_task = AsyncMock()
        mock._is_running = True
        return mock

    @pytest.fixture
    def mock_endpoint(self):
        """Create a mock Endpoint for testing."""
        mock = MagicMock()
        # Create a mock config with the necessary attributes
        mock.config = MagicMock()
        mock.config.name = "test-endpoint"
        mock.config.transport_type = "http"
        mock.config.default_request_kwargs = {}
        mock.config.http_config = MagicMock()
        mock.config.http_config.method = "POST"
        mock.config.base_url = "https://api.example.com"
        mock.get_client = AsyncMock()
        return mock

    @pytest.fixture
    def model_config_dict(self):
        """Create a model config dictionary for testing."""
        return {
            "provider": "test-provider",
            "model_name": "test-model",
            "base_url": "https://api.example.com",
            "endpoint": "completions",
            "method": "POST",
            "api_key": "test-api-key",
            "timeout": 30,
            "default_headers": {"X-Test-Header": "test-value"},
            "kwargs": {"temperature": 0.7},
        }

    @pytest.fixture
    def model_config_obj(self, model_config_dict):
        """Create a model config EndpointConfig object for testing."""
        # Add required 'name' field for EndpointConfig
        config_dict = model_config_dict.copy()
        config_dict["name"] = "test-endpoint"
        return EndpointConfig(**config_dict)
        return EndpointConfig(**config_dict)

    @pytest.mark.asyncio
    async def test_init(self, mock_executor, mock_endpoint):
        """Test initialization with an Endpoint instance."""
        model = iModel(mock_endpoint, mock_executor)

        assert model.executor == mock_executor
        assert model.endpoint == mock_endpoint

    @pytest.mark.asyncio
    async def test_invoke_http(self, mock_executor, mock_endpoint):
        """Test invoking an HTTP endpoint."""
        model = iModel(mock_endpoint, mock_executor)

        # Configure the mock endpoint for HTTP transport
        mock_endpoint.config.transport_type = "http"
        mock_client = AsyncMock()
        mock_endpoint.get_client.return_value = mock_client
        mock_client.request.return_value = {"result": "success"}

        # Set up the executor to return a mock event
        mock_event = MagicMock()
        mock_executor.submit_task.return_value = mock_event

        # Test invoking the endpoint
        result = await model.invoke(
            request_payload={"prompt": "Hello"},
            http_path="completions",
            http_method="POST",
        )

        # Verify the result
        assert result == mock_event
        mock_executor.submit_task.assert_called_once()

    @pytest.mark.asyncio
    async def test_invoke_sdk(self, mock_executor, mock_endpoint):
        """Test invoking an SDK endpoint."""
        model = iModel(mock_endpoint, mock_executor)

        # Configure the mock endpoint for SDK transport
        mock_endpoint.config.transport_type = "sdk"
        mock_endpoint.config.sdk_config = MagicMock()
        mock_endpoint.config.sdk_config.sdk_provider_name = "test-provider"
        mock_endpoint.config.sdk_config.default_sdk_method_name = "completions.create"

        mock_client = AsyncMock()
        mock_endpoint.get_client.return_value = mock_client
        mock_client.call.return_value = {"result": "success"}

        # Set up the executor to return a mock event
        mock_event = MagicMock()
        mock_executor.submit_task.return_value = mock_event

        # Test invoking the endpoint
        result = await model.invoke(
            request_payload={"prompt": "Hello"}, sdk_method_name="completions.create"
        )

        # Verify the result
        assert result == mock_event
        mock_executor.submit_task.assert_called_once()

    @pytest.mark.asyncio
    async def test_acompletion(self, mock_executor, mock_endpoint):
        """Test making a completion request."""
        model = iModel(mock_endpoint, mock_executor)

        # Configure the mock endpoint
        mock_endpoint.config.transport_type = "http"

        # Mock event
        mock_event = MagicMock(spec=NetworkRequestEvent)
        mock_executor.submit_task.return_value = mock_event

        # Create a spy for the invoke method
        with patch.object(
            model, "invoke", AsyncMock(return_value=mock_event)
        ) as mock_invoke:
            # Test with default parameters
            event = await model.acompletion("Hello, world!")

            # Verify the result
            assert event == mock_event
            mock_invoke.assert_called_once()

            # Check call arguments
            call_args = mock_invoke.call_args[1]
            assert call_args["request_payload"]["prompt"] == "Hello, world!"
            assert call_args["request_payload"]["max_tokens"] == 150
            assert call_args["request_payload"]["temperature"] == 0.7

            # Test with custom parameters
            mock_invoke.reset_mock()
            event = await model.acompletion(
                prompt="Custom prompt",
                max_tokens=200,
                temperature=0.5,
                num_tokens_to_consume=100,
                top_p=0.9,
            )

            # Verify the result
            assert event == mock_event
            mock_invoke.assert_called_once()

            # Check call arguments
            call_args = mock_invoke.call_args[1]
            assert call_args["request_payload"]["prompt"] == "Custom prompt"
            assert call_args["request_payload"]["max_tokens"] == 200
            assert call_args["request_payload"]["temperature"] == 0.5
            assert call_args["request_payload"]["top_p"] == 0.9
            assert call_args["num_api_tokens_needed"] == 100

    @pytest.mark.asyncio
    async def test_context_manager(self, mock_executor, mock_endpoint):
        """Test context manager usage."""
        # Set up the mock endpoint's __aenter__ and __aexit__ methods
        mock_endpoint.__aenter__ = AsyncMock(return_value=mock_endpoint)
        mock_endpoint.__aexit__ = AsyncMock()

        async with iModel(mock_endpoint, mock_executor) as model:
            assert model.endpoint == mock_endpoint

        # Verify __aexit__ was called
        mock_endpoint.__aexit__.assert_called_once()


if __name__ == "__main__":
    unittest.main()
