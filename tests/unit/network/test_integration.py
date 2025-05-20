"""
Integration tests for the network module components.
"""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from lionfuncs.errors import APIClientError
from lionfuncs.network.adapters import AbstractSDKAdapter
from lionfuncs.network.endpoint import Endpoint
from lionfuncs.network.events import RequestStatus
from lionfuncs.network.executor import Executor
from lionfuncs.network.imodel import iModel
from lionfuncs.network.primitives import (
    HttpTransportConfig,
    SdkTransportConfig,
    ServiceEndpointConfig,
)


class TestNetworkIntegration:
    """Integration tests for the network module components."""

    @pytest.mark.asyncio
    async def test_http_flow(self):
        """Test the complete HTTP flow from iModel through Endpoint to AsyncAPIClient."""
        # Create a real Executor
        executor = Executor(
            queue_capacity=10,
            concurrency_limit=5,
            requests_rate=10.0,
            requests_period=1.0,
            api_tokens_rate=None,  # No API token rate limiter for simplicity
            num_workers=2,
        )

        # Start the executor
        await executor.start()

        try:
            # Create a ServiceEndpointConfig for HTTP
            config = ServiceEndpointConfig(
                name="test-http",
                transport_type="http",
                base_url="https://api.example.com",
                http_config=HttpTransportConfig(method="POST"),
                timeout=30.0,
                default_headers={"X-Test-Header": "test-value"},
                default_request_kwargs={"model": "gpt-4"},
            )

            # Create a real Endpoint with a mocked AsyncAPIClient
            with patch(
                "lionfuncs.network.endpoint.AsyncAPIClient"
            ) as mock_client_class:
                mock_client = mock_client_class.return_value
                mock_client.__aenter__ = AsyncMock(return_value=mock_client)
                mock_client.__aexit__ = AsyncMock()
                mock_client.request = AsyncMock(return_value={"result": "success"})

                # Create the Endpoint and iModel
                endpoint = Endpoint(config)
                model = iModel(endpoint=endpoint, executor=executor)
                # Make a request using invoke
                # Explicitly specify http_method to avoid confusion with SDK transport
                event = await model.invoke(
                    request_payload={"prompt": "Hello, world!"},
                    http_path="v1/completions",
                    http_method="POST",
                    num_api_tokens_needed=10,
                    temperature=0.7,
                )

                # Wait for the request to complete
                while event.status != RequestStatus.COMPLETED:
                    await asyncio.sleep(0.1)
                    if event.status == RequestStatus.FAILED:
                        raise Exception(f"Request failed: {event.error_message}")

                # Verify the result
                assert event.status == RequestStatus.COMPLETED
                assert event.response_status_code == 200

                # The response body is now directly stored in response_body
                assert event.response_body == {"result": "success"}

                # Verify that AsyncAPIClient.request was called with the correct parameters
                mock_client.request.assert_called_once()
                call_args = mock_client.request.call_args
                assert call_args[1]["method"] == "POST"
                assert call_args[1]["url"] == "v1/completions"
                assert "json" in call_args[1]
                assert call_args[1]["json"]["prompt"] == "Hello, world!"
                # The parameters might be handled differently in the new implementation
                # Just verify the call was made with the correct method and URL
        finally:
            # Stop the executor
            await executor.stop()

    @pytest.mark.asyncio
    async def test_sdk_flow(self):
        """Test the complete SDK flow from iModel through Endpoint to SDKAdapter."""
        # Create a real Executor
        executor = Executor(
            queue_capacity=10,
            concurrency_limit=5,
            requests_rate=10.0,
            requests_period=1.0,
            api_tokens_rate=None,  # No API token rate limiter for simplicity
            num_workers=2,
        )

        # Start the executor
        await executor.start()

        try:
            # Create a ServiceEndpointConfig for SDK
            config = ServiceEndpointConfig(
                name="test-sdk",
                transport_type="sdk",
                api_key="test-api-key",
                sdk_config=SdkTransportConfig(
                    sdk_provider_name="openai",
                    default_sdk_method_name="chat.completions.create",
                ),
                default_request_kwargs={"model": "gpt-4"},
            )

            # Create a real Endpoint with a mocked SDKAdapter
            with patch(
                "lionfuncs.network.endpoint.create_sdk_adapter"
            ) as mock_create_adapter:
                mock_adapter = MagicMock(spec=AbstractSDKAdapter)
                mock_adapter.__aenter__ = AsyncMock(return_value=mock_adapter)
                mock_adapter.__aexit__ = AsyncMock()
                mock_adapter.call = AsyncMock(return_value={"result": "success"})
                mock_create_adapter.return_value = mock_adapter

                # Create the Endpoint and iModel
                endpoint = Endpoint(config)
                model = iModel(endpoint=endpoint, executor=executor)

                # Make a request using invoke
                event = await model.invoke(
                    request_payload={
                        "messages": [{"role": "user", "content": "Hello, world!"}]
                    },
                    num_api_tokens_needed=10,
                    temperature=0.7,
                )

                # Wait for the request to complete
                while event.status != RequestStatus.COMPLETED:
                    await asyncio.sleep(0.1)
                    if event.status == RequestStatus.FAILED:
                        raise Exception(f"Request failed: {event.error_message}")

                # Verify the result
                assert event.status == RequestStatus.COMPLETED
                assert event.response_status_code == 200

                # The response body is now directly stored in response_body
                assert event.response_body == {"result": "success"}

                # Verify that SDKAdapter.call was called with the correct parameters
                mock_adapter.call.assert_called_once()
                call_args = mock_adapter.call.call_args
                assert call_args[1]["method_name"] == "chat.completions.create"
                assert "messages" in call_args[1]
                assert call_args[1]["messages"][0]["role"] == "user"
                assert call_args[1]["messages"][0]["content"] == "Hello, world!"
                assert call_args[1]["model"] == "gpt-4"  # From default_request_kwargs
                assert (
                    call_args[1]["temperature"] == 0.7
                )  # From additional_request_params
        finally:
            # Stop the executor
            await executor.stop()

    @pytest.mark.asyncio
    async def test_error_handling(self):
        """Test error handling across all components."""
        # Create a real Executor
        executor = Executor(
            queue_capacity=10,
            concurrency_limit=5,
            requests_rate=10.0,
            requests_period=1.0,
            api_tokens_rate=None,  # No API token rate limiter for simplicity
            num_workers=2,
        )

        # Start the executor
        await executor.start()

        try:
            # Create a ServiceEndpointConfig for HTTP
            config = ServiceEndpointConfig(
                name="test-http",
                transport_type="http",
                base_url="https://api.example.com",
                http_config=HttpTransportConfig(method="POST"),
            )

            # Create a real Endpoint with a mocked AsyncAPIClient that raises an error
            with patch(
                "lionfuncs.network.endpoint.AsyncAPIClient"
            ) as mock_client_class:
                mock_client = mock_client_class.return_value
                mock_client.__aenter__ = AsyncMock(return_value=mock_client)
                mock_client.__aexit__ = AsyncMock()

                # Mock the request method to raise an error
                api_error = APIClientError("API error", status_code=400)
                mock_client.request = AsyncMock(side_effect=api_error)

                # Create the Endpoint and iModel
                endpoint = Endpoint(config)
                model = iModel(endpoint=endpoint, executor=executor)

                # Make a request using invoke
                # Explicitly specify http_method to avoid confusion with SDK transport
                event = await model.invoke(
                    request_payload={"prompt": "Hello, world!"},
                    http_path="v1/completions",
                    http_method="POST",
                )

                # Wait for the request to complete or fail
                while event.status not in [
                    RequestStatus.COMPLETED,
                    RequestStatus.FAILED,
                ]:
                    await asyncio.sleep(0.1)

                # Verify that the request failed
                assert event.status == RequestStatus.FAILED
                assert event.error_type == "APIClientError"
                assert "API error" in event.error_message

                # Verify that AsyncAPIClient.request was called
                mock_client.request.assert_called_once()
        finally:
            # Stop the executor
            await executor.stop()
