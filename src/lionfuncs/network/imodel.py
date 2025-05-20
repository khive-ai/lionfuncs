# Copyright (c) 2023 - 2025, HaiyangLi <quantocean.li at gmail dot com>
#
# SPDX-License-Identifier: Apache-2.0

"""
iModel class for interacting with API models using the Executor.

This module provides the iModel class, which uses the Executor for making
rate-limited API calls to model endpoints.
"""

import logging
from typing import Any, Optional, Union

import aiohttp

from lionfuncs.network.events import NetworkRequestEvent
from lionfuncs.network.executor import Executor
from lionfuncs.network.primitives import EndpointConfig

logger = logging.getLogger(__name__)


class iModel:
    """
    Client for interacting with API models using the Executor.

    The iModel class provides methods for making API calls to model endpoints,
    using the Executor for rate limiting and concurrency control.
    """

    def __init__(
        self,
        executor: Executor,
        model_endpoint_config: Union[dict[str, Any], EndpointConfig],
    ):
        """
        Initialize the iModel.

        Args:
            executor: An instance of Executor for making API calls.
            model_endpoint_config: Configuration for the model endpoint,
                                  either as a dictionary or EndpointConfig.
        """
        self.executor = executor

        if isinstance(model_endpoint_config, dict):
            self.config = model_endpoint_config
        elif isinstance(model_endpoint_config, EndpointConfig):
            self.config = model_endpoint_config.model_dump()
        else:
            raise TypeError("model_endpoint_config must be a dict or EndpointConfig")

        self.http_session: Optional[aiohttp.ClientSession] = None

        logger.debug(
            f"Initialized iModel with endpoint: {self.config.get('endpoint', 'unknown')}, "
            f"provider: {self.config.get('provider', 'unknown')}"
        )

    async def _get_session(self) -> aiohttp.ClientSession:
        """
        Get or create an HTTP session.

        Returns:
            An aiohttp.ClientSession instance.
        """
        if self.http_session is None or self.http_session.closed:
            self.http_session = aiohttp.ClientSession()
        return self.http_session

    async def close_session(self) -> None:
        """Close the HTTP session if it exists."""
        if self.http_session and not self.http_session.closed:
            await self.http_session.close()
            self.http_session = None

    async def _make_api_call(
        self,
        method: str,
        url: str,
        headers: dict[str, str],
        json_payload: Optional[dict[str, Any]] = None,
        timeout: Optional[float] = None,
    ) -> tuple[int, dict[str, str], Any]:
        """
        Make an API call using the HTTP session.

        Args:
            method: HTTP method (e.g., "GET", "POST").
            url: URL to call.
            headers: Request headers.
            json_payload: JSON payload for the request.
            timeout: Request timeout in seconds.

        Returns:
            A tuple of (status_code, headers, body).

        Raises:
            aiohttp.ClientError: If the request fails.
        """
        session = await self._get_session()
        timeout_obj = aiohttp.ClientTimeout(
            total=timeout or self.config.get("timeout", 300)
        )

        async with session.request(
            method, url, headers=headers, json=json_payload, timeout=timeout_obj
        ) as response:
            response_body = await response.json()
            return response.status, dict(response.headers), response_body

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
        base_url = self.config.get("base_url", "")
        endpoint = self.config.get("endpoint", "completions")
        endpoint_url = f"{base_url}/{endpoint}"

        method = self.config.get("method", "POST")
        api_key = self.config.get("api_key", "")

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        }

        # Add any additional headers from config
        headers.update(self.config.get("default_headers", {}))

        payload = {
            "prompt": prompt,
            "max_tokens": max_tokens,
            "temperature": temperature,
            **kwargs,
        }

        # Add any additional parameters from config
        payload.update(self.config.get("kwargs", {}))

        # Create a coroutine factory for the API call
        async def api_call_coro():
            return await self._make_api_call(
                method=method, url=endpoint_url, headers=headers, json_payload=payload
            )

        # Submit the task to the executor
        request_event = await self.executor.submit_task(
            api_call_coroutine=api_call_coro,
            endpoint_url=endpoint_url,
            method=method,
            headers=headers,
            payload=payload,
            num_api_tokens_needed=num_tokens_to_consume,
            metadata={"model_name": self.config.get("model_name", "unknown")},
        )

        return request_event

    async def __aenter__(self) -> "iModel":
        """Enter async context manager."""
        await self._get_session()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Exit async context manager."""
        await self.close_session()
