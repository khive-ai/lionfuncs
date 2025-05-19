"""
Network module for lionfuncs.

This module provides utilities for making HTTP requests, handling resilience patterns,
and adapting to different SDK interfaces.
"""

from .adapters import (
    AbstractSDKAdapter,
    AnthropicAdapter,
    OpenAIAdapter,
    create_sdk_adapter,
)
from .client import AsyncAPIClient
from .primitives import (
    AdaptiveRateLimiter,
    Endpoint,
    EndpointConfig,
    EndpointRateLimiter,
    HeaderFactory,
    TokenBucketRateLimiter,
    match_endpoint,
)
from .resilience import CircuitBreaker, RetryConfig, circuit_breaker, with_retry

__all__ = [
    # Client
    "AsyncAPIClient",
    # Resilience
    "circuit_breaker",
    "with_retry",
    "CircuitBreaker",
    "RetryConfig",
    # Primitives
    "EndpointConfig",
    "Endpoint",
    "HeaderFactory",
    "TokenBucketRateLimiter",
    "EndpointRateLimiter",
    "AdaptiveRateLimiter",
    "match_endpoint",
    # Adapters
    "AbstractSDKAdapter",
    "OpenAIAdapter",
    "AnthropicAdapter",
    "create_sdk_adapter",
]
