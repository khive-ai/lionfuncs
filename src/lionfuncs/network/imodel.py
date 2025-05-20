# Copyright (c) 2023 - 2025, HaiyangLi <quantocean.li at gmail dot com>
#
# SPDX-License-Identifier: Apache-2.0

"""
iModel class for interacting with API models using the Executor.

This module provides the iModel class, which uses the Executor for making
rate-limited API calls to model endpoints via the Endpoint class.
"""

import logging
from typing import Any, Optional

from pydantic import BaseModel

from lionfuncs.errors import APIClientError, LionSDKError
from lionfuncs.network.endpoint import Endpoint
from lionfuncs.network.events import NetworkRequestEvent
from lionfuncs.network.executor import Executor

logger = logging.getLogger(__name__)


class iModel:
    """
    Orchestrates API interactions for a specific model or service endpoint.

    It uses an Endpoint to get a configured client/adapter and an Executor
    to manage the execution of API calls.
    """

    def __init__(
        self,
        endpoint: Endpoint,
        executor: Executor,
    ):
        """
        Initialize the iModel.

        Args:
            endpoint: A configured Endpoint instance providing access to the API client/adapter.
            executor: An Executor instance for managing API call execution.
        """
        self.endpoint = endpoint
        self.executor = executor

        logger.debug(f"Initialized iModel with Endpoint: {self.endpoint.config.name}")

    async def invoke(
        self,
        request_payload: Any,  # Can be a dict or Pydantic model
        num_api_tokens_needed: int = 0,
        http_path: Optional[str] = None,  # e.g., "v1/chat/completions"
        http_method: Optional[
            str
        ] = None,  # Overrides ServiceEndpointConfig.http_config.method
        sdk_method_name: Optional[str] = None,  # e.g., "chat.completions.create"
        # Additional kwargs to pass to AsyncAPIClient.request or SDKAdapter.call
        # These are merged with Endpoint's default_request_kwargs and the payload
        **additional_request_params: Any,
    ) -> NetworkRequestEvent:
        """
        Makes a generic call to the configured API endpoint.

        Args:
            request_payload: The primary payload for the request (dict or Pydantic model).
            num_api_tokens_needed: Estimated API tokens this call will consume.
            http_path: Specific path for HTTP requests (appended to Endpoint's base_url).
            http_method: HTTP method (e.g., "GET", "POST"). Overrides Endpoint default.
            sdk_method_name: Specific SDK method to call (e.g., "chat.completions.create").
            **additional_request_params: Further keyword arguments for the API call,
                                         merged with/overriding Endpoint's defaults and payload.
                                         Can include 'metadata' for NetworkRequestEvent.

        Returns:
            A NetworkRequestEvent tracking the request.
        """
        client = await self.endpoint.get_client()

        # Prepare the final set of arguments for the API call
        # Start with endpoint defaults, then merge payload, then call-specific overrides
        merged_call_args = self.endpoint.config.default_request_kwargs.copy()

        if isinstance(request_payload, BaseModel):
            payload_dict = request_payload.model_dump(exclude_none=True)
        elif isinstance(request_payload, dict):
            payload_dict = request_payload.copy()
        else:  # Assume it's a primitive or directly usable by SDK
            payload_dict = request_payload

        # --- Determine call type and prepare ---
        actual_api_call_coroutine = None
        event_endpoint_url_str: str = ""
        event_method_str: str = ""
        event_payload_to_log: Any = payload_dict

        # Check the transport type from the config to determine how to handle the client
        if self.endpoint.config.transport_type == "http":
            if (
                not self.endpoint.config.base_url
            ):  # Should be caught by ServiceEndpointConfig validation
                raise ValueError(
                    "base_url is required for HTTP transport in Endpoint config."
                )

            _http_method = (
                http_method
                or (
                    self.endpoint.config.http_config.method
                    if self.endpoint.config.http_config
                    else "POST"
                )
            ).upper()

            _path = (http_path or "").lstrip("/")
            event_endpoint_url_str = (
                f"{self.endpoint.config.base_url.rstrip('/')}/{_path}"
            )
            event_method_str = _http_method

            # Prepare kwargs for AsyncAPIClient.request
            client_request_kwargs = merged_call_args.copy()
            client_request_kwargs.update(
                additional_request_params
            )  # call_specific_kwargs override endpoint defaults

            if _http_method in [
                "POST",
                "PUT",
                "PATCH",
                "DELETE_WITH_BODY",
            ]:  # Assuming a convention for DELETE with body
                client_request_kwargs["json"] = payload_dict
            else:  # GET, standard DELETE
                client_request_kwargs["params"] = (
                    payload_dict  # payload becomes query params
                )

            # Ensure client has request method
            if not hasattr(client, "request") or not callable(client.request):
                raise TypeError(
                    f"HTTP client does not have a 'request' method: {type(client)}"
                )

            # Define a function instead of using lambda
            async def make_http_request():
                return await client.request(
                    method=_http_method, url=_path, **client_request_kwargs
                )

            actual_api_call_coroutine = make_http_request
            event_payload_to_log = client_request_kwargs.get(
                "json"
            ) or client_request_kwargs.get("params")

        elif self.endpoint.config.transport_type == "sdk":
            if (
                not self.endpoint.config.sdk_config
            ):  # Should be caught by ServiceEndpointConfig validation
                raise ValueError(
                    "sdk_config is required for SDK transport in Endpoint config."
                )

            # Ensure client has call method
            if not hasattr(client, "call") or not callable(client.call):
                raise TypeError(
                    f"SDK client does not have a 'call' method: {type(client)}"
                )

            _sdk_method_name = (
                sdk_method_name
                or self.endpoint.config.sdk_config.default_sdk_method_name
                or "call"
            )

            event_endpoint_url_str = f"sdk://{self.endpoint.config.sdk_config.sdk_provider_name}/{_sdk_method_name}"
            event_method_str = "SDK_CALL"

            # For SDKs, typically all data is passed as keyword arguments
            sdk_call_final_args = merged_call_args.copy()

            if isinstance(payload_dict, dict):  # If payload is a dict, merge it
                sdk_call_final_args.update(payload_dict)
            elif (
                payload_dict is not None
            ):  # If payload is not a dict but not None, log a warning
                logger.warning(
                    "Non-dict request_payload for SDK call might not be correctly passed unless SDK method expects a single positional arg."
                )

            sdk_call_final_args.update(additional_request_params)
            event_payload_to_log = sdk_call_final_args.copy()

            # Define a function instead of using lambda
            async def make_sdk_call():
                return await client.call(
                    method_name=_sdk_method_name, **sdk_call_final_args
                )

            actual_api_call_coroutine = make_sdk_call
        else:
            raise TypeError(
                f"Unsupported transport_type in Endpoint config: {self.endpoint.config.transport_type}"
            )

        # Wrapper for Executor: expects (status, headers, body) or exception
        async def adapted_executor_coroutine():
            try:
                response_body = await actual_api_call_coroutine()
                # Assuming success, provide a generic success status.
                # Headers might not be applicable/available for all SDK calls.
                return 200, {}, response_body
            except APIClientError as e:  # From AsyncAPIClient
                # Re-raise to be caught by Executor's worker, which will populate event
                logger.debug(f"iModel: APIClientError caught: {e}")
                raise
            except LionSDKError as e:  # From SDKAdapter
                logger.debug(f"iModel: LionSDKError caught: {e}")
                raise
            except Exception as e:  # Catchall for other unexpected errors
                logger.error(
                    f"iModel: Unexpected error during API call: {e}", exc_info=True
                )
                raise

        event_metadata = additional_request_params.get("metadata", {})
        event_metadata.update({"endpoint_name": self.endpoint.config.name})

        request_event = await self.executor.submit_task(
            api_call_coroutine=adapted_executor_coroutine,
            endpoint_url=event_endpoint_url_str,
            method=event_method_str,
            payload=event_payload_to_log,  # Log the prepared payload
            num_api_tokens_needed=num_api_tokens_needed,
            metadata=event_metadata,
        )

        return request_event

    async def acompletion(
        self,
        prompt: str,
        max_tokens: int = 150,
        temperature: float = 0.7,
        num_tokens_to_consume: int = 0,
        **kwargs,
    ) -> NetworkRequestEvent:
        """
        Make an asynchronous completion request.

        This is a backward-compatible wrapper around invoke() for the completion endpoint.

        Args:
            prompt: The prompt to complete.
            max_tokens: Maximum number of tokens to generate.
            temperature: Sampling temperature.
            num_tokens_to_consume: Number of API tokens this call will consume.
            **kwargs: Additional parameters for the completion request.

        Returns:
            A NetworkRequestEvent tracking the request.

        Raises:
            RuntimeError: If the executor is not running.
        """
        payload = {
            "prompt": prompt,
            "max_tokens": max_tokens,
            "temperature": temperature,
            **kwargs,
        }

        # For backward compatibility, determine if this is HTTP or SDK
        if self.endpoint.config.transport_type == "http":
            return await self.invoke(
                request_payload=payload,
                http_path="completions",  # Default completion endpoint
                http_method="POST",
                num_api_tokens_needed=num_tokens_to_consume,
                metadata={"model_name": kwargs.get("model", "unknown")},
            )
        else:  # SDK
            return await self.invoke(
                request_payload=payload,
                sdk_method_name="completions.create",  # Default for OpenAI-like SDKs
                num_api_tokens_needed=num_tokens_to_consume,
                metadata={"model_name": kwargs.get("model", "unknown")},
            )

    async def __aenter__(self) -> "iModel":
        """Enters the async context, ensuring its Endpoint's client is initialized."""
        await self.endpoint.__aenter__()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Exits the async context, ensuring its Endpoint's client is closed."""
        await self.endpoint.__aexit__(exc_type, exc_val, exc_tb)
