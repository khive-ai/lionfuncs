"""
SDK adapters for API clients.

This module provides abstract interfaces and implementations for SDK adapters,
allowing the AsyncAPIClient to delegate calls to specific SDK implementations.
"""

import logging
from abc import ABC, abstractmethod
from typing import Any, Protocol, TypeVar, runtime_checkable

from lionfuncs.errors import LionSDKError

T = TypeVar("T")
logger = logging.getLogger(__name__)


@runtime_checkable
class AbstractSDKAdapter(Protocol):
    """
    Protocol defining the interface for SDK adapters.

    SDK adapters provide a consistent interface for interacting with different
    AI service SDKs (OpenAI, Anthropic, etc.) through a common API.
    """

    __slots__ = ()  # Make it a runtime checkable protocol

    async def call(self, method_name: str, **kwargs) -> Any:
        """
        Call a method on the SDK.

        Args:
            method_name: The name of the method to call.
            **kwargs: Additional keyword arguments for the method.

        Returns:
            The result of the method call.

        Raises:
            LionSDKError: If the SDK call fails.
        """
        ...

    async def close(self) -> None:
        """
        Close the SDK client and release resources.
        """
        ...

    async def __aenter__(self) -> "AbstractSDKAdapter":
        """
        Enter the async context manager.

        Returns:
            The adapter instance.
        """
        ...

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """
        Exit the async context manager and release resources.
        """
        ...


class BaseSDKAdapter(ABC):
    """
    Base class for SDK adapters.

    This class provides a common implementation for SDK adapters,
    handling resource management and error mapping.
    """

    def __init__(self, api_key: str, **kwargs):
        """
        Initialize the SDK adapter.

        Args:
            api_key: The API key for the service.
            **kwargs: Additional keyword arguments for the SDK client.
        """
        self.api_key = api_key
        self.client_kwargs = kwargs
        self._client = None
        self._closed = False
        logger.debug(f"Initialized {self.__class__.__name__}")

    async def __aenter__(self) -> "BaseSDKAdapter":
        """
        Enter the async context manager.

        Returns:
            The adapter instance.
        """
        await self._get_client()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """
        Exit the async context manager and release resources.
        """
        await self.close()

    async def close(self) -> None:
        """
        Close the SDK client and release resources.
        """
        if self._closed:
            return

        if self._client is not None and hasattr(self._client, "close"):
            if callable(getattr(self._client, "aclose", None)):
                await self._client.aclose()
            elif callable(getattr(self._client, "close", None)):
                self._client.close()

        self._client = None
        self._closed = True
        logger.debug(f"Closed {self.__class__.__name__}")

    @abstractmethod
    async def _get_client(self) -> Any:
        """
        Get or create the SDK client.

        Returns:
            The SDK client instance.

        Raises:
            RuntimeError: If the client is already closed.
        """
        pass

    @abstractmethod
    async def call(self, method_name: str, **kwargs) -> Any:
        """
        Call a method on the SDK.

        Args:
            method_name: The name of the method to call.
            **kwargs: Additional keyword arguments for the method.

        Returns:
            The result of the method call.

        Raises:
            LionSDKError: If the SDK call fails.
        """
        pass


class OpenAIAdapter(BaseSDKAdapter):
    """
    Adapter for the OpenAI API.

    This adapter provides a consistent interface for interacting with the
    OpenAI API through the official Python SDK.
    """

    async def _get_client(self) -> Any:
        """
        Get or create the OpenAI SDK client.

        Returns:
            The OpenAI SDK client instance.

        Raises:
            RuntimeError: If the client is already closed.
            ImportError: If the OpenAI SDK is not installed.
        """
        if self._closed:
            raise RuntimeError("Client is closed")

        if self._client is not None:
            return self._client

        try:
            from openai import AsyncOpenAI  # type: ignore[import]
        except ImportError:
            raise ImportError(
                "The OpenAI SDK is not installed. "
                "Please install it with `pip install openai`."
            )

        self._client = AsyncOpenAI(api_key=self.api_key, **self.client_kwargs)
        return self._client

    async def call(self, method_name: str, **kwargs) -> Any:
        """
        Call a method on the OpenAI SDK.

        Args:
            method_name: The name of the method to call (e.g., "chat.completions.create").
            **kwargs: Additional keyword arguments for the method.

        Returns:
            The result of the method call.

        Raises:
            LionSDKError: If the SDK call fails.
        """
        client = await self._get_client()

        try:
            # Parse the method path (e.g., "chat.completions.create")
            method_parts = method_name.split(".")
            obj = client

            # Navigate to the nested method
            for part in method_parts[:-1]:
                obj = getattr(obj, part)

            # Get the final method
            method = getattr(obj, method_parts[-1])

            # Call the method
            return await method(**kwargs)
        except Exception as e:
            logger.exception(f"OpenAI SDK call failed: {e}")
            raise LionSDKError(f"OpenAI SDK call failed: {e}") from e


class AnthropicAdapter(BaseSDKAdapter):
    """
    Adapter for the Anthropic API.

    This adapter provides a consistent interface for interacting with the
    Anthropic API through the official Python SDK.
    """

    async def _get_client(self) -> Any:
        """
        Get or create the Anthropic SDK client.

        Returns:
            The Anthropic SDK client instance.

        Raises:
            RuntimeError: If the client is already closed.
            ImportError: If the Anthropic SDK is not installed.
        """
        if self._closed:
            raise RuntimeError("Client is closed")

        if self._client is not None:
            return self._client

        try:
            import anthropic  # type: ignore[import]
        except ImportError:
            raise ImportError(
                "The Anthropic SDK is not installed. "
                "Please install it with `pip install anthropic`."
            )

        # Anthropic client might not have an async version, this is conceptual
        self._client = anthropic.Anthropic(api_key=self.api_key, **self.client_kwargs)
        return self._client

    async def call(self, method_name: str, **kwargs) -> Any:
        """
        Call a method on the Anthropic SDK.

        Args:
            method_name: The name of the method to call (e.g., "messages.create").
            **kwargs: Additional keyword arguments for the method.

        Returns:
            The result of the method call.

        Raises:
            LionSDKError: If the SDK call fails.
        """
        client = await self._get_client()

        try:
            # Parse the method path (e.g., "messages.create")
            method_parts = method_name.split(".")
            obj = client

            # Navigate to the nested method
            for part in method_parts[:-1]:
                obj = getattr(obj, part)

            # Get the final method
            method = getattr(obj, method_parts[-1])

            # Call the method - wrap in asyncio.to_thread if it's not async
            import asyncio

            if not asyncio.iscoroutinefunction(method):
                return await asyncio.to_thread(method, **kwargs)
            return await method(**kwargs)
        except Exception as e:
            logger.exception(f"Anthropic SDK call failed: {e}")
            raise LionSDKError(f"Anthropic SDK call failed: {e}") from e


def create_sdk_adapter(provider: str, api_key: str, **kwargs) -> AbstractSDKAdapter:
    """
    Create an SDK adapter for the specified provider.

    Args:
        provider: The provider name (e.g., "openai", "anthropic").
        api_key: The API key for the service.
        **kwargs: Additional keyword arguments for the SDK client.

    Returns:
        An SDK adapter instance.

    Raises:
        ValueError: If the provider is not supported.
    """
    provider = provider.lower()

    if provider == "openai":
        return OpenAIAdapter(api_key=api_key, **kwargs)
    elif provider == "anthropic":
        return AnthropicAdapter(api_key=api_key, **kwargs)
    else:
        raise ValueError(f"Unsupported provider: {provider}")
