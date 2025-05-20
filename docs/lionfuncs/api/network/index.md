---
title: "lionfuncs.network"
---

# lionfuncs.network

The `network` module provides utilities for making HTTP requests, handling
resilience patterns, and adapting to different SDK interfaces. It includes an
async HTTP client, circuit breaker and retry decorators, SDK adapters, and
network primitives.

## Submodules

- [**client**](client.md): Async HTTP client for API interactions.
- [**resilience**](resilience.md): Resilience patterns like circuit breaker and
  retry with backoff.
- [**adapters**](adapters.md): SDK adapters for third-party APIs.
- [**primitives**](primitives.md): Network primitives like rate limiters and
  endpoint configurations.
- [**endpoint**](endpoint.md): Endpoint class for managing API clients and
  adapters.
- [**events**](events.md): Event classes for tracking API request lifecycles.
- [**executor**](executor.md): Executor for managing and rate-limiting API
  calls.
- [**imodel**](imodel.md): Client for interacting with API models using the
  Executor.

## Components

The `network` module re-exports all components from its submodules, so you can
The `network` module re-exports all components from its submodules, so you can
import them directly from `lionfuncs.network`:

### From client

- [`AsyncAPIClient`](client.md#asyncapiclient): Generic async HTTP client for
  API interactions.

### From resilience

- [`@circuit_breaker`](resilience.md#circuit_breaker): Decorator for circuit
  breaker pattern.
- [`@with_retry`](resilience.md#with_retry): Decorator for retry with backoff.
- [`CircuitBreaker`](resilience.md#circuitbreaker): Class for implementing the
  circuit breaker pattern.
- [`RetryConfig`](resilience.md#retryconfig): Configuration for retry behavior.

### From adapters

- [`AbstractSDKAdapter`](adapters.md#abstractsdkadapter): Protocol defining the
  interface for SDK adapters.
- [`OpenAIAdapter`](adapters.md#openai-adapter): Adapter for the OpenAI API.
- [`AnthropicAdapter`](adapters.md#anthropic-adapter): Adapter for the Anthropic
  API.
- [`create_sdk_adapter`](adapters.md#create_sdk_adapter): Factory function for
  creating SDK adapters.

### From primitives

- [`HeaderFactory`](primitives.md#headerfactory): Utility for creating
  auth/content headers.
- [`EndpointConfig`](primitives.md#endpointconfig): Configuration for an API
  endpoint (legacy).
- [`ServiceEndpointConfig`](primitives.md#serviceendpointconfig): Comprehensive
  configuration for API endpoints.
- [`HttpTransportConfig`](primitives.md#httptransportconfig): Configuration for
  HTTP transport.
- [`SdkTransportConfig`](primitives.md#sdktransportconfig): Configuration for
  SDK transport.
- [`TokenBucketRateLimiter`](primitives.md#tokenbucketratelimiter): Rate limiter
  using the token bucket algorithm.
- [`EndpointRateLimiter`](primitives.md#endpointratelimiter): Rate limiter for
  different endpoints.
- [`AdaptiveRateLimiter`](primitives.md#adaptiveratelimiter): Rate limiter that
  adapts based on API response headers.
- [`match_endpoint`](primitives.md#match_endpoint): Function to select an
  `Endpoint` instance.

### From endpoint

- [`Endpoint`](endpoint.md#endpoint): Class for managing the creation,
  configuration, and lifecycle of API clients.

### From events

- [`NetworkRequestEvent`](events.md#networkrequestevent): Event class for
  tracking the lifecycle of a network request.
- [`RequestStatus`](events.md#requeststatus): Enum of possible states for a
  network request.

### From executor

- [`Executor`](executor.md#executor): Executor for managing and rate-limiting
  API calls.

### From imodel

- [`iModel`](imodel.md#imodel): Client for interacting with API models using the
  Executor.

## Installation

The network utilities are included in the base `lionfuncs` package:

```bash
pip install lionfuncs
```

For using specific SDK adapters, you may need to install the corresponding SDK
libraries:

```bash
# For OpenAI adapter
pip install openai

# For Anthropic adapter
pip install anthropic
```

## Usage Examples

### Making HTTP Requests

```python
import asyncio
from lionfuncs.network import AsyncAPIClient

async def main():
    # Create an API client
    async with AsyncAPIClient(
        base_url="https://api.example.com",
        timeout=10.0,
        headers={"User-Agent": "lionfuncs/0.1.0"}
    ) as client:
        # Make a GET request
        response = await client.request("GET", "/users")
        print(f"Users: {response}")

        # Make a POST request with JSON data
        response = await client.request(
            "POST",
            "/users",
            json={"name": "John Doe", "email": "john@example.com"}
        )
        print(f"Created user: {response}")

        # Using the call method with a request dictionary
        response = await client.call({
            "method": "GET",
            "url": "/products",
            "params": {"category": "electronics"}
        })
        print(f"Products: {response}")

asyncio.run(main())
```

### Using Resilience Patterns

```python
import asyncio
from lionfuncs.network import AsyncAPIClient, circuit_breaker, with_retry

# Apply resilience patterns with decorators
@circuit_breaker(failure_threshold=3, recovery_time=10.0)
@with_retry(max_retries=3, base_delay=1.0, backoff_factor=2.0)
async def fetch_data(client, endpoint):
    return await client.request("GET", endpoint)

async def main():
    async with AsyncAPIClient(base_url="https://api.example.com") as client:
        try:
            data = await fetch_data(client, "/data")
            print(f"Data: {data}")
        except Exception as e:
            print(f"Failed to fetch data: {e}")

asyncio.run(main())
```

### Using SDK Adapters

```python
import asyncio
import os
from lionfuncs.network import create_sdk_adapter

async def main():
    # Create an OpenAI adapter
    openai_api_key = os.environ.get("OPENAI_API_KEY")
    openai_adapter = create_sdk_adapter("openai", openai_api_key)

    # Use the adapter
    async with openai_adapter as adapter:
        response = await adapter.call(
            "chat.completions.create",
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": "Hello, world!"}
            ]
        )
        print(f"OpenAI response: {response}")

    # Create an Anthropic adapter
    anthropic_api_key = os.environ.get("ANTHROPIC_API_KEY")
    anthropic_adapter = create_sdk_adapter("anthropic", anthropic_api_key)

    # Use the adapter
    async with anthropic_adapter as adapter:
        response = await adapter.call(
            "messages.create",
            model="claude-3-sonnet-20240229",
            messages=[
                {"role": "user", "content": "Hello, world!"}
            ],
            max_tokens=1000
        )
        print(f"Anthropic response: {response}")

asyncio.run(main())
```

### Using Endpoints and Rate Limiters

```python
import asyncio
from lionfuncs.network import (
    AsyncAPIClient,
    Endpoint,
    EndpointConfig,
    TokenBucketRateLimiter
)

async def main():
    # Create a rate limiter
    rate_limiter = TokenBucketRateLimiter(rate=10, period=1.0)

    # Create an endpoint configuration
    endpoint_config = EndpointConfig(
        name="get_users",
        provider="example",
        base_url="https://api.example.com",
        endpoint="users",
        method="GET",
        auth_type="bearer",
        api_key="YOUR_API_KEY"
    )

    # Create an endpoint
    endpoint = Endpoint(endpoint_config)

    # Create an API client
    async with AsyncAPIClient(base_url="https://api.example.com") as client:
        # Use the rate limiter to execute a request
        response = await rate_limiter.execute(
            client.request,
            "GET",
            "/users",
            tokens=1  # Consume 1 token from the rate limiter
        )
        print(f"Users: {response}")

asyncio.run(main())
```

## Error Handling

The network functions raise various exceptions from `lionfuncs.errors`:

```python
import asyncio
from lionfuncs.network import AsyncAPIClient
from lionfuncs.errors import (
    APIClientError,
    APIConnectionError,
    APITimeoutError,
    RateLimitError,
    AuthenticationError,
    ResourceNotFoundError,
    ServerError,
    CircuitBreakerOpenError
)

async def main():
    async with AsyncAPIClient(base_url="https://api.example.com") as client:
        try:
            await client.request("GET", "/users")
        except APIConnectionError:
            print("Connection error")
        except APITimeoutError:
            print("Request timed out")
        except RateLimitError as e:
            print(f"Rate limit exceeded. Retry after: {e.retry_after}s")
        except AuthenticationError:
            print("Authentication failed")
        except ResourceNotFoundError:
            print("Resource not found")
        except ServerError:
            print("Server error")
        except APIClientError as e:
            print(f"API error: {e}")

asyncio.run(main())
```
