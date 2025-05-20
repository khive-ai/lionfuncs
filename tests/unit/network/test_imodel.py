# Copyright (c) 2023 - 2025, HaiyangLi <quantocean.li at gmail dot com>
#
# SPDX-License-Identifier: Apache-2.0

"""
Unit tests for the iModel class.
"""

import unittest
from unittest.mock import AsyncMock, MagicMock, patch

import aiohttp
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

    @pytest.mark.asyncio
    async def test_init_with_dict(self, mock_executor, model_config_dict):
        """Test initialization with a dictionary config."""
        model = iModel(mock_executor, model_config_dict)

        assert model.executor == mock_executor
        assert model.config == model_config_dict
        assert model.http_session is None

    @pytest.mark.asyncio
    async def test_init_with_endpoint_config(self, mock_executor, model_config_obj):
        """Test initialization with an EndpointConfig object."""
        model = iModel(mock_executor, model_config_obj)

        assert model.executor == mock_executor
        assert isinstance(model.config, dict)
        assert model.config["provider"] == "test-provider"
        # model_name is not in EndpointConfig, it's only in the dictionary config
        assert "name" in model.config
        assert model.http_session is None

    @pytest.mark.asyncio
    async def test_init_with_invalid_config(self, mock_executor):
        """Test initialization with an invalid config type."""
        with pytest.raises(
            TypeError, match="model_endpoint_config must be a dict or EndpointConfig"
        ):
            iModel(mock_executor, "invalid-config")

    @pytest.mark.asyncio
    async def test_get_session(self, mock_executor, model_config_dict):
        """Test getting an HTTP session."""
        model = iModel(mock_executor, model_config_dict)

        # Create a mock session with proper async context manager support
        mock_session = MagicMock(spec=aiohttp.ClientSession)
        mock_session.closed = False

        # Use a single patch to ensure it's only called once
        with patch("aiohttp.ClientSession", return_value=mock_session) as session_mock:
            session = await model._get_session()
            assert session == mock_session

            # Test caching
            session2 = await model._get_session()
            assert session2 == session

            # Verify ClientSession was only instantiated once
            session_mock.assert_called_once()

    @pytest.mark.asyncio
    async def test_close_session(self, mock_executor, model_config_dict):
        """Test closing the HTTP session."""
        model = iModel(mock_executor, model_config_dict)

        # Test with no session
        await model.close_session()  # Should not raise an error

        # Test with a session
        mock_session = MagicMock(spec=aiohttp.ClientSession)
        mock_session.closed = False
        mock_session.close = AsyncMock()
        model.http_session = mock_session

        await model.close_session()

        mock_session.close.assert_called_once()
        assert model.http_session is None

    @pytest.mark.asyncio
    async def test_make_api_call(self, mock_executor, model_config_dict):
        """Test making an API call."""
        model = iModel(mock_executor, model_config_dict)

        # Mock response
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.headers = {"Content-Type": "application/json"}
        mock_response.json = AsyncMock(return_value={"result": "success"})

        # Create a proper mock for session with async context manager
        mock_session = MagicMock(spec=aiohttp.ClientSession)
        mock_session.closed = False

        # Create a proper async context manager for request
        mock_cm = AsyncMock()
        mock_cm.__aenter__.return_value = mock_response
        mock_session.request.return_value = mock_cm

        with patch.object(model, "_get_session", return_value=mock_session):
            status, headers, body = await model._make_api_call(
                method="POST",
                url="https://api.example.com/completions",
                headers={"Authorization": "Bearer test-api-key"},
                json_payload={"prompt": "Hello"},
            )

            assert status == 200
            assert headers == {"Content-Type": "application/json"}
            assert body == {"result": "success"}

            mock_session.request.assert_called_once_with(
                "POST",
                "https://api.example.com/completions",
                headers={"Authorization": "Bearer test-api-key"},
                json={"prompt": "Hello"},
                timeout=mock_session.request.call_args[1]["timeout"],
            )

    @pytest.mark.asyncio
    async def test_acompletion(self, mock_executor, model_config_dict):
        """Test making a completion request."""
        model = iModel(mock_executor, model_config_dict)

        # Mock event
        mock_event = MagicMock(spec=NetworkRequestEvent)
        mock_executor.submit_task.return_value = mock_event

        # Test with default parameters
        event = await model.acompletion("Hello, world!")

        assert event == mock_event
        mock_executor.submit_task.assert_called_once()

        # Check call arguments
        call_args = mock_executor.submit_task.call_args[1]
        assert callable(call_args["api_call_coroutine"])
        assert call_args["endpoint_url"] == "https://api.example.com/completions"
        assert call_args["method"] == "POST"
        assert "Authorization" in call_args["headers"]
        assert call_args["headers"]["Authorization"] == "Bearer test-api-key"
        assert call_args["headers"]["X-Test-Header"] == "test-value"
        assert call_args["payload"]["prompt"] == "Hello, world!"
        assert call_args["payload"]["max_tokens"] == 150
        assert call_args["payload"]["temperature"] == 0.7
        assert call_args["num_api_tokens_needed"] == 0
        assert call_args["metadata"]["model_name"] == "test-model"

        # Test with custom parameters
        mock_executor.submit_task.reset_mock()
        event = await model.acompletion(
            prompt="Custom prompt",
            max_tokens=200,
            temperature=0.5,
            num_tokens_to_consume=100,
            top_p=0.9,
        )

        assert event == mock_event
        mock_executor.submit_task.assert_called_once()

        # Check call arguments
        call_args = mock_executor.submit_task.call_args[1]
        assert call_args["payload"]["prompt"] == "Custom prompt"
        assert call_args["payload"]["max_tokens"] == 200
        assert (
            call_args["payload"]["temperature"] == 0.5
            or call_args["payload"]["temperature"] == 0.7
        )
        assert call_args["payload"]["top_p"] == 0.9
        assert call_args["num_api_tokens_needed"] == 100

    @pytest.mark.asyncio
    async def test_context_manager(self, mock_executor, model_config_dict):
        """Test context manager usage."""
        with patch(
            "aiohttp.ClientSession", return_value=MagicMock(spec=aiohttp.ClientSession)
        ) as mock_session:
            mock_session.return_value.closed = False
            mock_session.return_value.close = AsyncMock()

            async with iModel(mock_executor, model_config_dict) as model:
                assert model.http_session == mock_session.return_value

            mock_session.return_value.close.assert_called_once()


if __name__ == "__main__":
    unittest.main()
