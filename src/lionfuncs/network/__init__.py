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
from .endpoint import Endpoint
from .events import NetworkRequestEvent, RequestStatus
from .executor import Executor
from .imodel import iModel
from .primitives import AdaptiveRateLimiter
from .primitives import Endpoint as OldEndpoint  # Renamed to avoid conflict
from .primitives import (
    EndpointConfig,
    EndpointRateLimiter,
    HeaderFactory,
    HttpTransportConfig,
    SdkTransportConfig,
    ServiceEndpointConfig,
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
    "OldEndpoint",  # Renamed to avoid conflict
    "Endpoint",  # New Endpoint class
    "ServiceEndpointConfig",  # New config model
    "HttpTransportConfig",  # New HTTP config model
    "SdkTransportConfig",  # New SDK config model
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
    # Events
    "NetworkRequestEvent",
    "RequestStatus",
    # Executor
    "Executor",
    # iModel
    "iModel",
]
