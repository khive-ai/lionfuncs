"""
Endpoint class for managing API clients and adapters.

This module provides the Endpoint class, which manages the creation, configuration,
and lifecycle of API clients (AsyncAPIClient or SDK Adapters) based on a
ServiceEndpointConfig.
"""

import asyncio
import logging
from typing import Optional, Union
from unittest.mock import AsyncMock

from lionfuncs.network.adapters import AbstractSDKAdapter, create_sdk_adapter
from lionfuncs.network.client import AsyncAPIClient
from lionfuncs.network.primitives import ServiceEndpointConfig

logger = logging.getLogger(__name__)


class Endpoint:
    """
    Manages the creation, configuration, and lifecycle of API clients
    (AsyncAPIClient or SDK Adapters) based on a ServiceEndpointConfig.
    It acts as a factory and context manager for these clients.
    """

    def __init__(self, config: ServiceEndpointConfig):
        """
        Initializes the Endpoint.

        Args:
            config: The configuration defining how to connect to the service.
        """
        self.config: ServiceEndpointConfig = config
        self._client_instance: Optional[Union[AsyncAPIClient, AbstractSDKAdapter]] = (
            None
        )
        self._lock = asyncio.Lock()  # Protects _client_instance creation
        self._closed = False

        logger.debug(
            f"Initialized Endpoint with name={self.config.name}, "
            f"transport_type={self.config.transport_type}"
        )

    async def _create_client(self) -> Union[AsyncAPIClient, AbstractSDKAdapter]:
        """
        Instantiates the appropriate client based on configuration.

        Returns:
            The created client instance (AsyncAPIClient or AbstractSDKAdapter).

        Raises:
            ValueError: If the transport_type is unsupported.
        """
        if self.config.transport_type == "http":
            logger.debug(f"Creating AsyncAPIClient for endpoint {self.config.name}")
            return AsyncAPIClient(
                base_url=self.config.base_url,  # Must be present due to validator
                timeout=self.config.timeout,
                headers=self.config.default_headers,
                **self.config.client_constructor_kwargs,
            )
        elif self.config.transport_type == "sdk":
            # sdk_config is guaranteed by validator
            sdk_conf = self.config.sdk_config
            logger.debug(
                f"Creating SDK adapter for endpoint {self.config.name} "
                f"with provider {sdk_conf.sdk_provider_name}"
            )
            return create_sdk_adapter(
                provider=sdk_conf.sdk_provider_name,
                api_key=self.config.api_key,  # api_key is passed to adapter factory
                **self.config.client_constructor_kwargs,
            )
        else:
            # This case should ideally be caught by Pydantic validation of transport_type
            raise ValueError(
                f"Unsupported transport_type: {self.config.transport_type}"
            )

    async def get_client(self) -> Union[AsyncAPIClient, AbstractSDKAdapter]:
        """
        Provides a configured and ready-to-use client instance.
        Manages singleton creation and enters client's async context if applicable.

        Returns:
            A configured client instance (AsyncAPIClient or AbstractSDKAdapter).

        Raises:
            RuntimeError: If the Endpoint is closed.
        """
        if self._closed:
            raise RuntimeError(f"Endpoint '{self.config.name}' is closed.")

        if self._client_instance is None:
            async with self._lock:
                if self._client_instance is None:  # Double-check after acquiring lock
                    self._client_instance = await self._create_client()
                    # If the created client is an async context manager, enter its context.
                    if hasattr(self._client_instance, "__aenter__"):
                        await self._client_instance.__aenter__()
                        logger.debug(
                            f"Entered async context for client in endpoint {self.config.name}"
                        )

        return self._client_instance

    async def close(self) -> None:
        """
        Closes the underlying client and marks the Endpoint as closed.

        This method is idempotent and can be called multiple times.
        """
        if self._closed:
            return

        async with self._lock:
            if self._client_instance:
                client_to_close = self._client_instance
                self._client_instance = (
                    None  # Clear instance before potentially slow close
                )

                logger.debug(f"Closing client for endpoint {self.config.name}")

                # Check for close method first
                if hasattr(client_to_close, "close"):
                    # Check if close is a coroutine function or an AsyncMock
                    close_method = getattr(client_to_close, "close")
                    if asyncio.iscoroutinefunction(close_method) or isinstance(
                        close_method, AsyncMock
                    ):
                        await close_method()
                    else:
                        close_method()  # Assuming synchronous close if not a coroutine
                # Then try to use __aexit__ if it exists and is not None
                # We need to be careful with __aexit__ because it might be None
                elif (
                    hasattr(client_to_close, "__aexit__")
                    and client_to_close.__aexit__ is not None
                ):
                    await client_to_close.__aexit__(None, None, None)

            self._closed = True
            logger.debug(f"Endpoint {self.config.name} closed")

    async def __aenter__(self) -> "Endpoint":
        """
        Enters the async context, ensuring the client is initialized.

        Returns:
            The Endpoint instance.
        """
        await self.get_client()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """
        Exits the async context, ensuring the client is closed.

        Args:
            exc_type: The exception type, if an exception was raised.
            exc_val: The exception value, if an exception was raised.
            exc_tb: The exception traceback, if an exception was raised.
        """
        await self.close()
