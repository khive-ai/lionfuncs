"""
Async API Client implementation.

This module provides the AsyncAPIClient class, which is a robust async
HTTP client for API interactions with proper resource management.
"""

import asyncio
import contextlib
import logging
from typing import Any, Optional, TypeVar

import httpx

from lionfuncs.errors import (
    APIClientError,
    APIConnectionError,
    APITimeoutError,
    AuthenticationError,
    RateLimitError,
    ResourceNotFoundError,
    ServerError,
)
from lionfuncs.network.resilience import CircuitBreaker, RetryConfig

T = TypeVar("T")
logger = logging.getLogger(__name__)


class AsyncAPIClient:
    """
    Generic async HTTP client for API interactions with proper resource management.

    This client handles session management, connection pooling, and proper
    resource cleanup. It implements the async context manager protocol for
    resource management.

    Example:
        ```python
        async with AsyncAPIClient(base_url="https://api.example.com") as client:
            response = await client.request("GET", "/endpoint")
        ```
    """

    def __init__(
        self,
        base_url: str,
        timeout: float = 10.0,
        headers: Optional[dict[str, str]] = None,
        auth: Optional[httpx.Auth] = None,
        client: Optional[httpx.AsyncClient] = None,
        circuit_breaker: Optional[CircuitBreaker] = None,
        retry_config: Optional[RetryConfig] = None,
        **client_kwargs,
    ):
        """
        Initialize the async API client.

        Args:
            base_url: The base URL for the API.
            timeout: The timeout for requests in seconds.
            headers: Default headers to include with every request.
            auth: Authentication to use for requests.
            client: An existing httpx.AsyncClient to use instead of creating a new one.
            circuit_breaker: Optional circuit breaker for resilience.
            retry_config: Optional retry configuration for resilience.
            **client_kwargs: Additional keyword arguments to pass to httpx.AsyncClient.
        """
        self.base_url = base_url
        self.timeout = timeout
        self.headers = headers or {}
        self.auth = auth
        self._client = client
        self._client_kwargs = client_kwargs
        self._session_lock = asyncio.Lock()
        self._closed = False
        self.circuit_breaker = circuit_breaker
        self.retry_config = retry_config

        logger.debug(
            f"Initialized AsyncAPIClient with base_url={base_url}, "
            f"timeout={timeout}, circuit_breaker={circuit_breaker is not None}, "
            f"retry_config={retry_config is not None}"
        )

    async def _get_client(self) -> httpx.AsyncClient:
        """
        Get or create the shared client session.

        Returns:
            The httpx.AsyncClient instance.

        Raises:
            RuntimeError: If the client is already closed.
        """
        if self._closed:
            raise RuntimeError("Client is closed")

        if self._client is not None:
            return self._client

        async with self._session_lock:
            if self._client is None:
                self._client = httpx.AsyncClient(
                    base_url=self.base_url,
                    timeout=self.timeout,
                    headers=self.headers,
                    auth=self.auth,
                    **self._client_kwargs,
                )
            return self._client

    async def close(self) -> None:
        """
        Close the client session and release resources.

        This method is idempotent and can be called multiple times.
        """
        if self._closed:
            return

        async with self._session_lock:
            if self._client is not None:
                await self._client.aclose()
                self._client = None
            self._closed = True

    async def __aenter__(self) -> "AsyncAPIClient":
        """
        Enter the async context manager.

        Returns:
            The AsyncAPIClient instance.
        """
        await self._get_client()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """
        Exit the async context manager and release resources.

        Args:
            exc_type: The exception type, if an exception was raised.
            exc_val: The exception value, if an exception was raised.
            exc_tb: The exception traceback, if an exception was raised.
        """
        await self.close()

    async def request(self, method: str, url: str, **kwargs) -> Any:
        """
        Make a request to the API.

        Args:
            method: The HTTP method to use.
            url: The URL to request.
            **kwargs: Additional keyword arguments to pass to httpx.AsyncClient.request.

        Returns:
            The parsed response data.

        Raises:
            APIConnectionError: If a connection error occurs.
            APITimeoutError: If the request times out.
            RateLimitError: If a rate limit is exceeded.
            AuthenticationError: If authentication fails.
            ResourceNotFoundError: If a resource is not found.
            ServerError: If a server error occurs.
            APIClientError: For other API client errors.
        """

        # Define the actual request function
        async def _make_request():
            client = await self._get_client()
            response = None

            try:
                response = await client.request(method, url, **kwargs)
                response.raise_for_status()
                return response.json()
            except httpx.ConnectError as e:
                logger.exception("Connection error")
                raise APIConnectionError(f"Connection error: {e!s}") from e
            except httpx.TimeoutException as e:
                logger.exception("Request timed out")
                raise APITimeoutError(f"Request timed out: {e!s}") from e
            except httpx.HTTPStatusError as e:
                status_code = e.response.status_code
                headers = dict(e.response.headers)
                response_content = e.response.text

                try:
                    response_data = e.response.json()
                    error_message = response_data.get("detail", str(e))
                except Exception:
                    error_message = response_content

                if status_code == 401:
                    logger.exception("Authentication error")
                    raise AuthenticationError(
                        f"Authentication error: {error_message}",
                        status_code=status_code,
                        response_content=response_content,
                    ) from e
                if status_code == 404:
                    logger.exception("Resource not found")
                    raise ResourceNotFoundError(
                        f"Resource not found: {error_message}",
                        status_code=status_code,
                        response_content=response_content,
                    ) from e
                if status_code == 429:
                    retry_after = None
                    if "Retry-After" in headers:
                        with contextlib.suppress(ValueError, TypeError):
                            retry_after = float(headers["Retry-After"])

                    logger.exception("Rate limit exceeded")
                    raise RateLimitError(
                        f"Rate limit exceeded: {error_message}",
                        status_code=status_code,
                        response_content=response_content,
                        retry_after=retry_after,
                    ) from e
                if 500 <= status_code < 600:
                    logger.exception("Server error")
                    raise ServerError(
                        f"Server error: {error_message}",
                        status_code=status_code,
                        response_content=response_content,
                    ) from e

                logger.exception("API error")
                raise APIClientError(
                    f"API error: {error_message}",
                    status_code=status_code,
                    response_content=response_content,
                ) from e
            except httpx.HTTPError as e:
                logger.exception("HTTP error")
                raise APIClientError(f"HTTP error: {e!s}") from e
            except Exception as e:
                logger.exception("Unexpected error")
                raise APIClientError(f"Unexpected error: {e!s}") from e
            finally:
                # Ensure response is properly released if coroutine is cancelled
                if (
                    response is not None
                    and hasattr(response, "close")
                    and not response.is_closed
                ):
                    response.close()

        # Apply resilience patterns if configured
        request_func = _make_request

        # Apply retry if configured
        if self.retry_config:
            from lionfuncs.network.resilience import retry_with_backoff

            async def request_func():
                return await retry_with_backoff(
                    _make_request, **self.retry_config.as_kwargs()
                )

        # Apply circuit breaker if configured
        if self.circuit_breaker:
            if self.retry_config:
                # If both are configured, apply circuit breaker to the retry-wrapped function
                return await self.circuit_breaker.execute(request_func)
            # If only circuit breaker is configured, apply it directly
            return await self.circuit_breaker.execute(_make_request)

        if self.retry_config:
            # If only retry is configured, call the retry-wrapped function
            return await request_func()

        # If no resilience patterns are configured, call the request function directly
        return await _make_request()

    async def call(self, request: dict[str, Any], **kwargs) -> Any:
        """
        Make a call to the API using the ResourceClient protocol.

        This method is part of the ResourceClient protocol and provides
        a generic way to make API calls.

        Args:
            request: The request parameters.
            **kwargs: Additional keyword arguments for the request.

        Returns:
            The parsed response data.
        """
        method = request.pop("method", "GET").upper()
        url = request.pop("url", "/")
        params = request.pop("params", None)
        json_data = request.pop("json", None)
        data = request.pop("data", None)

        # Merge any remaining request parameters with kwargs
        merged_kwargs = {**request, **kwargs}

        if params is not None:
            merged_kwargs["params"] = params
        if json_data is not None:
            merged_kwargs["json"] = json_data
        if data is not None:
            merged_kwargs["data"] = data

        return await self.request(method, url, **merged_kwargs)
