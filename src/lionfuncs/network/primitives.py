"""
Network primitives for API interactions.

This module provides primitives for API interactions, including endpoint configuration,
header factories, and rate limiting.
"""

import logging
import time
from typing import Any, Callable, Literal, Optional, TypeVar, Union

from pydantic import BaseModel, Field

from lionfuncs.concurrency import Lock

T = TypeVar("T")
logger = logging.getLogger(__name__)

# Auth types supported by HeaderFactory
AUTH_TYPES = Literal["bearer", "x-api-key"]


class HeaderFactory:
    """Utility for creating authentication and content headers."""

    @staticmethod
    def get_content_type_header(
        content_type: str = "application/json",
    ) -> dict[str, str]:
        """
        Get content type header.

        Args:
            content_type: The content type to use.

        Returns:
            A dictionary with the Content-Type header.
        """
        return {"Content-Type": content_type}

    @staticmethod
    def get_bearer_auth_header(api_key: str) -> dict[str, str]:
        """
        Get Bearer authentication header.

        Args:
            api_key: The API key to use.

        Returns:
            A dictionary with the Authorization header.
        """
        return {"Authorization": f"Bearer {api_key}"}

    @staticmethod
    def get_x_api_key_header(api_key: str) -> dict[str, str]:
        """
        Get X-API-Key header.

        Args:
            api_key: The API key to use.

        Returns:
            A dictionary with the x-api-key header.
        """
        return {"x-api-key": api_key}

    @staticmethod
    def get_header(
        auth_type: AUTH_TYPES,
        content_type: str = "application/json",
        api_key: Optional[str] = None,
        default_headers: Optional[dict[str, str]] = None,
    ) -> dict[str, str]:
        """
        Get headers for API requests.

        Args:
            auth_type: The authentication type to use.
            content_type: The content type to use.
            api_key: The API key to use.
            default_headers: Default headers to include.

        Returns:
            A dictionary with the headers.

        Raises:
            ValueError: If API key is required but not provided, or if auth type is unsupported.
        """
        if not api_key:
            raise ValueError("API key is required for authentication")

        headers = HeaderFactory.get_content_type_header(content_type)
        if auth_type == "bearer":
            headers.update(HeaderFactory.get_bearer_auth_header(api_key))
        elif auth_type == "x-api-key":
            headers.update(HeaderFactory.get_x_api_key_header(api_key))
        else:
            raise ValueError(f"Unsupported auth type: {auth_type}")

        if default_headers:
            headers.update(default_headers)
        return headers


class EndpointConfig(BaseModel):
    """Configuration for an API endpoint."""

    name: str
    provider: str
    transport_type: Literal["http", "sdk"] = "http"
    base_url: Optional[str] = None
    endpoint: str
    endpoint_params: Optional[list[str]] = None
    method: str = "POST"
    params: dict[str, str] = Field(default_factory=dict)
    content_type: str = "application/json"
    auth_type: AUTH_TYPES = "bearer"
    default_headers: dict[str, str] = Field(default_factory=dict)
    api_key: Optional[str] = None
    timeout: int = 300
    max_retries: int = 3
    kwargs: dict[str, Any] = Field(default_factory=dict)
    client_kwargs: dict[str, Any] = Field(default_factory=dict)
    oai_compatible: bool = False

    @property
    def full_url(self) -> str:
        """
        Get the full URL for the endpoint.

        Returns:
            The full URL with base URL and endpoint path.
        """
        if not self.endpoint_params:
            return f"{self.base_url}/{self.endpoint}"
        return f"{self.base_url}/{self.endpoint.format(**self.params)}"

    def update(self, **kwargs) -> None:
        """
        Update the config with new values.

        Args:
            **kwargs: The values to update.
        """
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)
            else:
                # Add to kwargs dict if not a direct attribute
                self.kwargs[key] = value


class Endpoint:
    """
    API endpoint for making requests.

    This class represents an API endpoint and provides methods for making requests
    to that endpoint.
    """

    def __init__(
        self,
        config: Union[dict[str, Any], EndpointConfig],
        **kwargs,
    ):
        """
        Initialize the endpoint.

        Args:
            config: The endpoint configuration.
            **kwargs: Additional keyword arguments to update the configuration.
        """
        if isinstance(config, dict):
            self.config = EndpointConfig(**config, **kwargs)
        elif isinstance(config, EndpointConfig):
            self.config = config.model_copy()
            self.config.update(**kwargs)
        else:
            raise TypeError("config must be a dict or EndpointConfig")

        logger.debug(
            f"Initialized Endpoint with provider={self.config.provider}, "
            f"endpoint={self.config.endpoint}"
        )

    def create_payload(
        self,
        request: Union[dict[str, Any], BaseModel],
        extra_headers: Optional[dict[str, str]] = None,
        **kwargs,
    ) -> tuple[dict[str, Any], dict[str, str]]:
        """
        Create payload and headers for a request.

        Args:
            request: The request parameters or model.
            extra_headers: Additional headers to include.
            **kwargs: Additional keyword arguments for the request.

        Returns:
            A tuple of (payload, headers).
        """
        headers = HeaderFactory.get_header(
            auth_type=self.config.auth_type,
            content_type=self.config.content_type,
            api_key=self.config.api_key,
            default_headers=self.config.default_headers,
        )
        if extra_headers:
            headers.update(extra_headers)

        request_dict = (
            request
            if isinstance(request, dict)
            else request.model_dump(exclude_none=True)
        )
        params = self.config.kwargs.copy()

        # First update params with the request data
        params.update(request_dict)

        # Then handle any additional kwargs
        if kwargs:
            params.update(kwargs)

        return (params, headers)


def match_endpoint(
    provider: str,
    endpoint: str,
    **kwargs,
) -> Optional[Endpoint]:
    """
    Match an endpoint by provider and endpoint name.

    Args:
        provider: The provider name.
        endpoint: The endpoint name.
        **kwargs: Additional keyword arguments for the endpoint.

    Returns:
        An Endpoint instance, or None if no match is found.
    """
    # This is a simplified version that would need to be expanded
    # with actual endpoint configurations for different providers
    config = {
        "name": f"{provider}_{endpoint}",
        "provider": provider,
        "endpoint": endpoint,
        **kwargs,
    }
    return Endpoint(config)


class TokenBucketRateLimiter:
    """
    Rate limiter using the token bucket algorithm.

    The token bucket algorithm allows for controlled bursts of requests
    while maintaining a long-term rate limit. Tokens are added to the
    bucket at a constant rate, and each request consumes one or more tokens.
    If the bucket is empty, requests must wait until enough tokens are
    available.
    """

    def __init__(
        self,
        rate: float,
        period: float = 1.0,
        max_tokens: Optional[float] = None,
        initial_tokens: Optional[float] = None,
    ):
        """
        Initialize the rate limiter.

        Args:
            rate: Maximum number of tokens per period.
            period: Time period in seconds.
            max_tokens: Maximum token bucket capacity (defaults to rate).
            initial_tokens: Initial token count (defaults to max_tokens).
        """
        self.rate = rate
        self.period = period
        self.max_tokens = max_tokens if max_tokens is not None else rate
        self.tokens = initial_tokens if initial_tokens is not None else self.max_tokens
        self.last_refill = time.monotonic()
        self._lock = Lock()  # Using our own Lock implementation

        logger.debug(
            f"Initialized TokenBucketRateLimiter with rate={rate}, "
            f"period={period}, max_tokens={self.max_tokens}, "
            f"initial_tokens={self.tokens}"
        )

    async def _refill(self) -> None:
        """
        Refill tokens based on elapsed time.

        This method calculates the number of tokens to add based on the
        time elapsed since the last refill, and adds them to the bucket
        up to the maximum capacity.
        """
        now = time.monotonic()
        elapsed = now - self.last_refill
        new_tokens = elapsed * (self.rate / self.period)

        if new_tokens > 0:
            self.tokens = min(self.tokens + new_tokens, self.max_tokens)
            self.last_refill = now
            logger.debug(
                f"Refilled {new_tokens:.2f} tokens, current tokens: {self.tokens:.2f}/{self.max_tokens}"
            )

    async def acquire(self, tokens: float = 1.0) -> float:
        """
        Acquire tokens from the bucket.

        Args:
            tokens: Number of tokens to acquire.

        Returns:
            Wait time in seconds before tokens are available.
            Returns 0.0 if tokens are immediately available.
        """
        async with self._lock:
            await self._refill()

            if self.tokens >= tokens:
                self.tokens -= tokens
                logger.debug(
                    f"Acquired {tokens} tokens, remaining: {self.tokens:.2f}/{self.max_tokens}"
                )
                return 0.0

            # Calculate wait time until enough tokens are available
            deficit = tokens - self.tokens
            wait_time = deficit * self.period / self.rate

            logger.debug(
                f"Not enough tokens (requested: {tokens}, available: {self.tokens:.2f}/{self.max_tokens}), "
                f"wait time: {wait_time:.2f}s"
            )

            return wait_time

    async def execute(self, func: Callable[..., Any], *args: Any, **kwargs: Any) -> Any:
        """
        Execute a coroutine with rate limiting.

        Args:
            func: Async function to execute.
            *args: Positional arguments for func.
            **kwargs: Keyword arguments for func.
                tokens: Optional number of tokens to acquire (default: 1.0).
                        This will be removed from kwargs before calling func.

        Returns:
            Result from func.
        """
        # Extract tokens parameter if present, default to 1.0
        tokens = kwargs.pop("tokens", 1.0)

        # Acquire tokens (waiting if necessary)
        wait_time = await self.acquire(tokens)

        if wait_time > 0:
            logger.debug(f"Rate limited: waiting {wait_time:.2f}s before execution")
            import asyncio

            await asyncio.sleep(wait_time)

        logger.debug(f"Executing rate-limited function: {func.__name__}")
        return await func(*args, **kwargs)


class EndpointRateLimiter:
    """
    Rate limiter that manages multiple endpoints with different rate limits.

    This class maintains separate rate limiters for different API endpoints,
    allowing for fine-grained control over rate limiting.
    """

    def __init__(self, default_rate: float = 10.0, default_period: float = 1.0):
        """
        Initialize the endpoint rate limiter.

        Args:
            default_rate: Default rate for unknown endpoints.
            default_period: Default period for unknown endpoints.
        """
        self.default_rate = default_rate
        self.default_period = default_period
        self.limiters: dict[str, TokenBucketRateLimiter] = {}
        self._lock = Lock()  # Using our own Lock implementation

        logger.debug(
            f"Initialized EndpointRateLimiter with default_rate={default_rate}, "
            f"default_period={default_period}"
        )

    def get_limiter(self, endpoint: str) -> TokenBucketRateLimiter:
        """
        Get or create a rate limiter for the endpoint.

        Args:
            endpoint: API endpoint identifier.

        Returns:
            The rate limiter for the specified endpoint.
        """
        if endpoint not in self.limiters:
            logger.debug(f"Creating new rate limiter for endpoint: {endpoint}")
            self.limiters[endpoint] = TokenBucketRateLimiter(
                rate=self.default_rate, period=self.default_period
            )
        return self.limiters[endpoint]

    async def execute(
        self,
        endpoint: str,
        func: Callable[..., Any],
        *args: Any,
        **kwargs: Any,
    ) -> Any:
        """
        Execute a coroutine with endpoint-specific rate limiting.

        Args:
            endpoint: API endpoint identifier.
            func: Async function to execute.
            *args: Positional arguments for func.
            **kwargs: Keyword arguments for func.
                tokens: Optional number of tokens to acquire (default: 1.0).

        Returns:
            Result from func.
        """
        # Get the limiter for this endpoint
        limiter = self.get_limiter(endpoint)

        # Execute the function with the endpoint-specific limiter
        return await limiter.execute(func, *args, **kwargs)

    async def update_rate_limit(
        self,
        endpoint: str,
        rate: Optional[float] = None,
        period: Optional[float] = None,
        max_tokens: Optional[float] = None,
        reset_tokens: bool = False,
    ) -> None:
        """
        Update the rate limit parameters for an endpoint.

        Args:
            endpoint: API endpoint identifier.
            rate: New maximum operations per period (if None, keep current).
            period: New time period in seconds (if None, keep current).
            max_tokens: New maximum token capacity (if None, keep current).
            reset_tokens: If True, reset current tokens to max_tokens.
        """
        limiter = self.get_limiter(endpoint)

        async with self._lock:
            # Store original tokens value before any updates
            original_tokens = limiter.tokens

            # If not resetting tokens and rate will be reduced, reduce tokens proportionally
            if (
                not reset_tokens
                and rate is not None
                and rate < limiter.rate
                and original_tokens > 0
            ):
                # Reduce tokens proportionally to the rate reduction
                reduction_factor = rate / limiter.rate
                limiter.tokens = min(
                    original_tokens * reduction_factor, original_tokens
                )
                logger.debug(
                    f"Adjusted tokens for endpoint {endpoint}: {original_tokens} -> {limiter.tokens}"
                )

            # Update rate, period, and max_tokens
            if rate is not None:
                logger.debug(
                    f"Updating rate for endpoint {endpoint}: {limiter.rate} -> {rate}"
                )
                limiter.rate = rate

            if period is not None:
                logger.debug(
                    f"Updating period for endpoint {endpoint}: {limiter.period} -> {period}"
                )
                limiter.period = period

            if max_tokens is not None:
                logger.debug(
                    f"Updating max_tokens for endpoint {endpoint}: {limiter.max_tokens} -> {max_tokens}"
                )
                limiter.max_tokens = max_tokens

            # Reset tokens if requested
            if reset_tokens:
                logger.debug(
                    f"Resetting tokens for endpoint {endpoint}: {limiter.tokens} -> {limiter.max_tokens}"
                )
                limiter.tokens = limiter.max_tokens
                logger.debug(
                    f"Adjusted tokens for endpoint {endpoint}: {original_tokens} -> {limiter.tokens}"
                )


class AdaptiveRateLimiter(TokenBucketRateLimiter):
    """
    Rate limiter that can adapt its limits based on API response headers.

    This class extends TokenBucketRateLimiter to automatically adjust
    rate limits based on response headers from API calls. It supports
    common rate limit header patterns used by various APIs.
    """

    def __init__(
        self,
        initial_rate: float,
        initial_period: float = 1.0,
        max_tokens: Optional[float] = None,
        min_rate: float = 1.0,
        safety_factor: float = 0.9,
    ):
        """
        Initialize adaptive rate limiter.

        Args:
            initial_rate: Initial maximum operations per period.
            initial_period: Initial time period in seconds.
            max_tokens: Maximum token capacity (defaults to initial_rate).
            min_rate: Minimum rate to maintain even with strict API limits.
            safety_factor: Factor to multiply API limits by for safety margin.
        """
        super().__init__(
            rate=initial_rate, period=initial_period, max_tokens=max_tokens
        )
        self.min_rate = min_rate
        self.safety_factor = safety_factor

        logger.debug(
            f"Initialized AdaptiveRateLimiter with initial_rate={initial_rate}, "
            f"initial_period={initial_period}, min_rate={min_rate}, "
            f"safety_factor={safety_factor}"
        )

    def update_from_headers(self, headers: dict[str, str]) -> None:
        """
        Update rate limits based on API response headers.

        Supports common header patterns:
        - X-RateLimit-Limit, X-RateLimit-Remaining, X-RateLimit-Reset
        - X-Rate-Limit-Limit, X-Rate-Limit-Remaining, X-Rate-Limit-Reset
        - RateLimit-Limit, RateLimit-Remaining, RateLimit-Reset
        - ratelimit-limit, ratelimit-remaining, ratelimit-reset
        - X-RL-Limit, X-RL-Remaining, X-RL-Reset

        Args:
            headers: Response headers from API.
        """
        # Convert headers to lowercase for case-insensitive matching
        lower_headers = {k.lower(): v for k, v in headers.items()}

        # Look for rate limit info in headers
        limit = None
        remaining = None
        reset = None

        # Try different header patterns
        for prefix in ["x-ratelimit-", "x-rate-limit-", "ratelimit-", "x-rl-"]:
            if (
                f"{prefix}limit" in lower_headers
                and f"{prefix}remaining" in lower_headers
            ):
                try:
                    limit = int(lower_headers[f"{prefix}limit"])
                    remaining = int(lower_headers[f"{prefix}remaining"])

                    # Reset time can be in different formats
                    if f"{prefix}reset" in lower_headers:
                        reset_value = lower_headers[f"{prefix}reset"]
                        try:
                            # Try parsing as epoch timestamp
                            reset = float(reset_value)
                            # If it's a Unix timestamp (seconds since epoch), convert to relative time
                            now = time.time()
                            if reset > now:
                                reset = reset - now
                        except ValueError:
                            # If not a number, ignore
                            logger.warning(
                                f"Could not parse reset value: {reset_value}"
                            )
                            reset = 60.0  # Default to 60 seconds
                    else:
                        # Default reset time if not provided
                        reset = 60.0

                    logger.debug(
                        f"Found rate limit headers with prefix '{prefix}': "
                        f"limit={limit}, remaining={remaining}, reset={reset}"
                    )
                    break
                except (ValueError, TypeError) as e:
                    logger.warning(f"Error parsing rate limit headers: {e}")

        # Check for Retry-After header (simpler format used by some APIs)
        if "retry-after" in lower_headers and not (limit and remaining):
            try:
                retry_after = float(lower_headers["retry-after"])
                # Assume we're at the limit
                limit = 1
                remaining = 0
                reset = retry_after
                logger.debug(f"Found Retry-After header: {retry_after}s")
            except (ValueError, TypeError) as e:
                logger.warning(f"Error parsing Retry-After header: {e}")

        if limit and remaining is not None and reset:
            # Calculate new rate based on remaining calls and reset time
            time_until_reset = max(reset, 1.0)  # At least 1 second

            # Calculate new rate based on remaining calls and reset time
            new_rate = remaining / time_until_reset

            # Apply safety factor
            adjusted_rate = new_rate * self.safety_factor

            # Apply minimum rate
            final_rate = max(adjusted_rate, self.min_rate)

            logger.info(
                f"Adjusting rate limit based on headers: {final_rate:.2f} "
                f"requests per second (was: {self.rate:.2f})"
            )

            # Update the rate
            old_rate = self.rate
            self.rate = final_rate

            # If the rate was reduced, reduce tokens proportionally
            if final_rate < old_rate and self.tokens > 0:
                reduction_factor = final_rate / old_rate
                self.tokens = min(self.tokens * reduction_factor, self.tokens)
                logger.debug(
                    f"Adjusted tokens due to rate reduction: {self.tokens:.2f}/{self.max_tokens}"
                )


class HttpTransportConfig(BaseModel):
    """Configuration for HTTP transport in ServiceEndpointConfig."""

    method: str = "POST"  # Default HTTP method if not overridden at call time


class SdkTransportConfig(BaseModel):
    """Configuration for SDK transport in ServiceEndpointConfig."""

    sdk_provider_name: str  # e.g., "openai", "anthropic" (maps to adapter factory)
    default_sdk_method_name: Optional[str] = (
        None  # Default SDK method to call if not specified in invoke()
    )


class ServiceEndpointConfig(BaseModel):
    """
    Comprehensive configuration for API endpoints.

    This model provides a complete configuration for the Endpoint class,
    supporting both HTTP and SDK transport types.
    """

    name: str = Field(
        description="User-defined name for this endpoint configuration, e.g., 'openai_chat_completions_gpt4'"
    )
    transport_type: Literal["http", "sdk"] = Field(
        description="Specifies if direct HTTP or an SDK adapter is used."
    )

    # Common fields for both transport types
    api_key: Optional[str] = Field(
        None, description="API key. Can be set via env var or direct value."
    )
    base_url: Optional[str] = Field(
        None, description="Base URL for HTTP calls or if required by an SDK."
    )
    timeout: float = Field(60.0, description="Default request timeout in seconds.")

    # Headers for HTTP transport, can also be used by some SDKs if they accept custom headers.
    default_headers: dict[str, str] = Field(
        default_factory=dict, description="Default headers for HTTP requests."
    )

    # Keyword arguments passed directly to the constructor of AsyncAPIClient or the specific SDK client.
    # For AsyncAPIClient, this can include 'auth', 'event_hooks', etc.
    # For SDKs, this includes any specific init params for that SDK (e.g., 'organization' for OpenAI).
    client_constructor_kwargs: dict[str, Any] = Field(default_factory=dict)

    # Specific configuration block for HTTP transport
    http_config: Optional[HttpTransportConfig] = Field(
        None, description="Configuration specific to HTTP transport."
    )

    # Specific configuration block for SDK transport
    sdk_config: Optional[SdkTransportConfig] = Field(
        None, description="Configuration specific to SDK transport."
    )

    # Default keyword arguments to be included in every request made through this endpoint.
    # These can be overridden by call-specific arguments in iModel.invoke().
    # For HTTP, these might be default query params or JSON body elements.
    # For SDK, these are default parameters for the SDK method call.
    default_request_kwargs: dict[str, Any] = Field(default_factory=dict)

    def model_post_init(self, __context):
        """Validate transport-specific configuration after initialization."""
        if self.transport_type == "http" and self.http_config is None:
            # Default HttpTransportConfig if not provided
            self.http_config = HttpTransportConfig()

        if self.transport_type == "sdk" and self.sdk_config is None:
            raise ValueError("sdk_config must be provided for SDK transport type.")

        if self.transport_type == "http" and not self.base_url:
            raise ValueError("base_url must be provided for HTTP transport type.")

    model_config = {
        "extra": "forbid"  # Disallow extra fields not defined in the model
    }
