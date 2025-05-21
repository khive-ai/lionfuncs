"""
Network module for lionfuncs.

This module provides utilities for making HTTP requests, handling resilience patterns,
and adapting to different SDK interfaces.
"""

from lionfuncs.network.adapters import (
    AbstractSDKAdapter,
    AnthropicAdapter,
    OpenAIAdapter,
    create_sdk_adapter,
)
from lionfuncs.network.client import AsyncAPIClient
from lionfuncs.network.endpoint import Endpoint
from lionfuncs.network.events import NetworkRequestEvent, RequestStatus
from lionfuncs.network.executor import Executor
from lionfuncs.network.imodel import iModel
from lionfuncs.network.primitives import (
    AdaptiveRateLimiter,
    EndpointConfig,
    EndpointRateLimiter,
    HeaderFactory,
    HttpTransportConfig,
    SdkTransportConfig,
    ServiceEndpointConfig,
    TokenBucketRateLimiter,
    match_endpoint,
)
from lionfuncs.network.resilience import (
    CircuitBreaker,
    RetryConfig,
    circuit_breaker,
    with_retry,
)

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
