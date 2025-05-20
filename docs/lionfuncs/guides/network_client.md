---
title: "Network Client Guide"
---

# Network Client Guide

This guide covers how to use the `lionfuncs.network` module for making HTTP
requests, handling resilience patterns, and working with SDK adapters.

## Introduction

The `lionfuncs.network` module provides a robust set of tools for interacting
with APIs and web services. At its core is the `AsyncAPIClient`, a powerful
async HTTP client built on top of `httpx`. The module also includes resilience
patterns like circuit breaker and retry with backoff, adapters for third-party
SDKs, and components for managing rate-limited API calls like `Executor`,
`NetworkRequestEvent`, and `iModel`.

> **Note:** For detailed information on using the new `Executor` and `iModel`
> components, see the [Network Executor Usage Guide](network_executor_usage.md).

## Making HTTP Requests with AsyncAPIClient

The `AsyncAPIClient` is a generic async HTTP client for API interactions with
proper resource management.

### Basic Usage

```python
import asyncio
from lionfuncs.network import AsyncAPIClient

async def main():
    # Create a client
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

asyncio.run(main())
```

### Request Options

The `request` method supports all the options provided by
`httpx.AsyncClient.request`:

```python
async def main():
    async with AsyncAPIClient(base_url="https://api.example.com") as client:
        # GET request with query parameters
        response = await client.request(
            "GET",
            "/users",
            params={"role": "admin", "active": "true"}
        )
        print(f"Admin users: {response}")

        # POST request with form data
        response = await client.request(
            "POST",
            "/login",
            data={"username": "john", "password": "secret"}
        )
        print(f"Login response: {response}")

        # PUT request with JSON data
        response = await client.request(
            "PUT",
            "/users/123",
            json={"name": "John Smith", "email": "john.smith@example.com"}
        )
        print(f"Updated user: {response}")

        # DELETE request
        response = await client.request("DELETE", "/users/123")
        print(f"Delete response: {response}")

        # Request with custom headers
        response = await client.request(
            "GET",
            "/protected",
            headers={"Authorization": "Bearer token123"}
        )
        print(f"Protected resource: {response}")

        # Request with timeout
        response = await client.request(
            "GET",
            "/slow-endpoint",
            timeout=30.0  # 30 seconds timeout
        )
        print(f"Slow endpoint response: {response}")

asyncio.run(main())
```

### Using the call Method

The `call` method provides an alternative interface for making requests:

```python
async def main():
    async with AsyncAPIClient(base_url="https://api.example.com") as client:
        # Using the call method with a request dictionary
        response = await client.call({
            "method": "GET",
            "url": "/products",
            "params": {"category": "electronics"}
        })
        print(f"Products: {response}")

        # POST request with the call method
        response = await client.call({
            "method": "POST",
            "url": "/orders",
            "json": {
                "product_id": 123,
                "quantity": 1
            }
        })
        print(f"Order created: {response}")

asyncio.run(main())
```

### Error Handling

The `AsyncAPIClient` maps HTTP errors to specific exception types from
`lionfuncs.errors`:

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
    ServerError
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

## Resilience Patterns

The `lionfuncs.network` module provides resilience patterns to make your API
calls more robust.

### Circuit Breaker Pattern

The circuit breaker pattern prevents repeated calls to a failing service:

```python
import asyncio
from lionfuncs.network import AsyncAPIClient, circuit_breaker
from lionfuncs.errors import CircuitBreakerOpenError

@circuit_breaker(
    failure_threshold=3,     # Open after 3 failures
    recovery_time=10.0,      # Wait 10 seconds before trying again
    name="api-circuit-breaker"
)
async def fetch_data(client, endpoint):
    return await client.request("GET", endpoint)

async def main():
    async with AsyncAPIClient(base_url="https://api.example.com") as client:
        for i in range(10):
            try:
                data = await fetch_data(client, "/data")
                print(f"Data: {data}")
            except CircuitBreakerOpenError as e:
                print(f"Circuit is open: {e}")
            except Exception as e:
                print(f"Error: {e}")

            await asyncio.sleep(1)

asyncio.run(main())
```

### Retry with Backoff Pattern

The retry with backoff pattern automatically retries failed requests with
exponential backoff:

```python
import asyncio
from lionfuncs.network import AsyncAPIClient, with_retry
from lionfuncs.errors import APITimeoutError, AuthenticationError

@with_retry(
    max_retries=3,           # Maximum number of retries
    base_delay=1.0,          # Initial delay between retries
    backoff_factor=2.0,      # Factor to increase delay with each retry
    retry_exceptions=(APITimeoutError, ConnectionError),  # Exceptions to retry
    exclude_exceptions=(AuthenticationError,)  # Exceptions not to retry
)
async def fetch_data(client, endpoint):
    return await client.request("GET", endpoint)

async def main():
    async with AsyncAPIClient(base_url="https://api.example.com") as client:
        try:
            data = await fetch_data(client, "/data")
            print(f"Data: {data}")
        except Exception as e:
            print(f"Failed after retries: {e}")

asyncio.run(main())
```

### Combining Resilience Patterns

You can combine the circuit breaker and retry patterns for more robust
resilience:

```python
import asyncio
from lionfuncs.network import AsyncAPIClient, circuit_breaker, with_retry
from lionfuncs.errors import CircuitBreakerOpenError

# Apply both patterns - circuit breaker wraps retry
@circuit_breaker(
    failure_threshold=3,
    recovery_time=10.0,
    name="api-circuit-breaker"
)
@with_retry(
    max_retries=3,
    base_delay=1.0,
    backoff_factor=2.0
)
async def fetch_data(client, endpoint):
    return await client.request("GET", endpoint)

async def main():
    async with AsyncAPIClient(base_url="https://api.example.com") as client:
        try:
            data = await fetch_data(client, "/data")
            print(f"Data: {data}")
        except CircuitBreakerOpenError as e:
            print(f"Circuit is open: {e}")
        except Exception as e:
            print(f"Failed after retries: {e}")

asyncio.run(main())
```

### Using CircuitBreaker and RetryConfig Directly

You can also use the `CircuitBreaker` and `RetryConfig` classes directly with
the `AsyncAPIClient`:

```python
import asyncio
from lionfuncs.network import AsyncAPIClient, CircuitBreaker, RetryConfig

async def main():
    # Create resilience configurations
    circuit_breaker = CircuitBreaker(
        failure_threshold=3,
        recovery_time=10.0,
        name="api-circuit-breaker"
    )

    retry_config = RetryConfig(
        max_retries=3,
        base_delay=1.0,
        backoff_factor=2.0,
        jitter=True
    )

    # Create a client with resilience patterns
    async with AsyncAPIClient(
        base_url="https://api.example.com",
        circuit_breaker=circuit_breaker,
        retry_config=retry_config
    ) as client:
        try:
            # This request will automatically use the circuit breaker and retry logic
            response = await client.request("GET", "/data")
            print(f"Data: {response}")
        except Exception as e:
            print(f"Failed to fetch data: {e}")

asyncio.run(main())
```

## SDK Adapters

The `lionfuncs.network` module provides adapters for third-party SDKs, allowing
you to use them with a consistent interface.

### Using OpenAI Adapter

```python
import asyncio
import os
from lionfuncs.network import OpenAIAdapter

async def main():
    # Get API key from environment variable
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        print("OPENAI_API_KEY environment variable not set")
        return

    # Create an OpenAI adapter
    adapter = OpenAIAdapter(api_key=api_key)

    # Use the adapter
    async with adapter as sdk:
        try:
            # Call the chat completions API
            response = await sdk.call(
                "chat.completions.create",
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "You are a helpful assistant."},
                    {"role": "user", "content": "Hello, world!"}
                ]
            )
            print(f"OpenAI response: {response}")
        except Exception as e:
            print(f"Error calling OpenAI API: {e}")

asyncio.run(main())
```

### Using Anthropic Adapter

```python
import asyncio
import os
from lionfuncs.network import AnthropicAdapter

async def main():
    # Get API key from environment variable
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        print("ANTHROPIC_API_KEY environment variable not set")
        return

    # Create an Anthropic adapter
    adapter = AnthropicAdapter(api_key=api_key)

    # Use the adapter
    async with adapter as sdk:
        try:
            # Call the messages API
            response = await sdk.call(
                "messages.create",
                model="claude-3-sonnet-20240229",
                messages=[
                    {"role": "user", "content": "Hello, world!"}
                ],
                max_tokens=1000
            )
            print(f"Anthropic response: {response}")
        except Exception as e:
            print(f"Error calling Anthropic API: {e}")

asyncio.run(main())
```

### Using the Factory Function

You can use the `create_sdk_adapter` factory function to create adapters:

```python
import asyncio
import os
from lionfuncs.network import create_sdk_adapter

async def main():
    # Get API keys from environment variables
    openai_api_key = os.environ.get("OPENAI_API_KEY")
    anthropic_api_key = os.environ.get("ANTHROPIC_API_KEY")

    # Create adapters using the factory function
    if openai_api_key:
        openai_adapter = create_sdk_adapter("openai", openai_api_key)
        async with openai_adapter as sdk:
            response = await sdk.call(
                "chat.completions.create",
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "You are a helpful assistant."},
                    {"role": "user", "content": "Hello from OpenAI!"}
                ]
            )
            print(f"OpenAI response: {response}")

    if anthropic_api_key:
        anthropic_adapter = create_sdk_adapter("anthropic", anthropic_api_key)
        async with anthropic_adapter as sdk:
            response = await sdk.call(
                "messages.create",
                model="claude-3-sonnet-20240229",
                messages=[
                    {"role": "user", "content": "Hello from Anthropic!"}
                ],
                max_tokens=1000
            )
            print(f"Anthropic response: {response}")

asyncio.run(main())
```

## Rate Limiting

The `lionfuncs.network` module provides rate limiters to control the rate of API
calls.

### Using TokenBucketRateLimiter

```python
import asyncio
from lionfuncs.network import AsyncAPIClient, TokenBucketRateLimiter

async def main():
    # Create a rate limiter with 5 requests per second
    rate_limiter = TokenBucketRateLimiter(rate=5, period=1.0)

    # Create an API client
    async with AsyncAPIClient(base_url="https://api.example.com") as client:
        # Make 10 API calls with rate limiting
        for i in range(10):
            # Execute the request with rate limiting
            response = await rate_limiter.execute(
                client.request,
                "GET",
                f"/items/{i}",
                tokens=1.0  # Consume 1 token from the rate limiter
            )
            print(f"Response {i}: {response}")

asyncio.run(main())
```

### Using EndpointRateLimiter

```python
import asyncio
from lionfuncs.network import AsyncAPIClient, EndpointRateLimiter

async def main():
    # Create an endpoint rate limiter
    rate_limiter = EndpointRateLimiter(default_rate=10.0)

    # Update rate limits for specific endpoints
    await rate_limiter.update_rate_limit("users", rate=5.0)
    await rate_limiter.update_rate_limit("orders", rate=2.0)

    # Create an API client
    async with AsyncAPIClient(base_url="https://api.example.com") as client:
        # Make API calls to different endpoints
        for i in range(5):
            # Call the users endpoint (rate limit: 5 per second)
            users_response = await rate_limiter.execute(
                "users",
                client.request,
                "GET",
                "/users"
            )
            print(f"Users response {i}: {users_response}")

            # Call the orders endpoint (rate limit: 2 per second)
            orders_response = await rate_limiter.execute(
                "orders",
                client.request,
                "GET",
                "/orders"
            )
            print(f"Orders response {i}: {orders_response}")

asyncio.run(main())
```

### Using AdaptiveRateLimiter

```python
import asyncio
from lionfuncs.network import AsyncAPIClient, AdaptiveRateLimiter

async def main():
    # Create an adaptive rate limiter
    rate_limiter = AdaptiveRateLimiter(
        initial_rate=10.0,
        safety_factor=0.8,
        min_rate=1.0
    )

    # Create an API client
    async with AsyncAPIClient(base_url="https://api.example.com") as client:
        for i in range(5):
            # Execute API call with rate limiting
            response = await rate_limiter.execute(
                client.request,
                "GET",
                "/users",
                tokens=1.0
            )

            # Update rate limiter based on response headers
            if hasattr(response, "headers"):
                rate_limiter.update_from_headers(response.headers)

            print(f"Response {i}: {response}")

asyncio.run(main())
```

## Endpoints and Header Factories

The `lionfuncs.network` module provides utilities for working with endpoints and
headers.

### Using Endpoint and EndpointConfig

```python
import asyncio
from lionfuncs.network import AsyncAPIClient, Endpoint, EndpointConfig

async def main():
    # Create an endpoint configuration
    endpoint_config = EndpointConfig(
        name="get_users",
        provider="example",
        base_url="https://api.example.com",
        endpoint="users",
        method="GET",
        auth_type="bearer",
        api_key="your-api-key"
    )

    # Create an endpoint
    endpoint = Endpoint(endpoint_config)

    # Create payload and headers for a request
    request = {"limit": 10, "offset": 0}
    payload, headers = endpoint.create_payload(
        request,
        extra_headers={"X-Request-ID": "123"}
    )

    # Create an API client
    async with AsyncAPIClient(base_url="https://api.example.com") as client:
        # Make the request
        response = await client.request(
            endpoint_config.method,
            endpoint_config.endpoint,
            params=payload,
            headers=headers
        )
        print(f"Response: {response}")

asyncio.run(main())
```

### Using HeaderFactory

```python
import asyncio
from lionfuncs.network import AsyncAPIClient, HeaderFactory

async def main():
    # Create headers
    headers = HeaderFactory.get_header(
        auth_type="bearer",
        content_type="application/json",
        api_key="your-api-key",
        default_headers={"User-Agent": "lionfuncs/0.1.0"}
    )

    # Create an API client
    async with AsyncAPIClient(
        base_url="https://api.example.com",
        headers=headers
    ) as client:
        # Make a request
        response = await client.request("GET", "/users")
        print(f"Response: {response}")

asyncio.run(main())
```

## Combining with Other lionfuncs Modules

The network module can be combined with other `lionfuncs` modules for powerful
workflows.

### With async_utils

```python
import asyncio
from lionfuncs.network import AsyncAPIClient
from lionfuncs.async_utils import alcall

async def fetch_user(user_id):
    async with AsyncAPIClient(base_url="https://api.example.com") as client:
        return await client.request("GET", f"/users/{user_id}")

async def main():
    user_ids = list(range(1, 11))

    # Fetch multiple users in parallel
    users = await alcall(
        user_ids,
        fetch_user,
        max_concurrent=5,  # Limit concurrency
        num_retries=3,     # Retry failed requests
    )

    print(f"Fetched {len(users)} users")

asyncio.run(main())
```

### With file_system

```python
import asyncio
from lionfuncs.network import AsyncAPIClient
from lionfuncs.file_system import save_to_file

async def download_file(url, filename):
    async with AsyncAPIClient(base_url="https://api.example.com") as client:
        # Download the file
        response = await client.request("GET", url)

        # Save the file
        await save_to_file(
            response,
            "downloads",
            filename,
            file_exist_ok=True,
        )

        return f"downloads/{filename}"

async def main():
    # Download a file
    file_path = await download_file("/files/example.txt", "example.txt")
    print(f"Downloaded file to: {file_path}")

asyncio.run(main())
```

## Best Practices

1. **Use Async Context Manager**: Always use the `AsyncAPIClient` with the async
   context manager (`async with`) to ensure proper resource cleanup.
2. **Handle Errors**: Catch specific exceptions for different error types.
3. **Use Resilience Patterns**: Apply circuit breaker and retry patterns for
   robust API calls.
4. **Limit Concurrency**: Use rate limiters to control the rate of API calls.
5. **Reuse Clients**: Create a single client for multiple requests to the same
   API.
6. **Set Timeouts**: Always set appropriate timeouts for requests.
7. **Use SDK Adapters**: Use SDK adapters for third-party APIs to maintain a
   consistent interface.

## Advanced API Call Management with Executor and iModel

For more advanced API call management, especially when dealing with rate limits
and token-based APIs, the `lionfuncs.network` module provides the `Executor` and
`iModel` components:

- **Executor**: Manages a queue of API call tasks, enforces concurrency and rate
  limits, and tracks request lifecycles.
- **NetworkRequestEvent**: Tracks the lifecycle of API requests, including
  status, timing, and result information.
- **iModel**: Client for interacting with API models using the Executor.

Here's a brief example of using these components:

```python
import asyncio
from lionfuncs.network.executor import Executor
from lionfuncs.network.imodel import iModel
from lionfuncs.network.events import RequestStatus

async def main():
    # Create an executor with rate limiting
    async with Executor(
        concurrency_limit=5,
        requests_rate=10.0,
        requests_period=1.0,
        api_tokens_rate=10000.0,
        api_tokens_period=60.0
    ) as executor:
        # Create an iModel instance
        config = {
            "base_url": "https://api.openai.com/v1",
            "endpoint": "completions",
            "api_key": "your-api-key",
            "model_name": "gpt-3.5-turbo-instruct"
        }

        async with iModel(executor, config) as model:
            # Make a completion request
            event = await model.acompletion(
                prompt="Write a short poem about programming",
                max_tokens=150,
                temperature=0.7,
                num_tokens_to_consume=200  # Estimate of token usage
            )

            # Wait for completion
            while event.status not in [RequestStatus.COMPLETED, RequestStatus.FAILED]:
                await asyncio.sleep(0.1)

            # Process the result
            if event.status == RequestStatus.COMPLETED:
                print(f"Completion: {event.response_body}")
            else:
                print(f"Error: {event.error_message}")

asyncio.run(main())
```

For more detailed information on using these components, see the
[Network Executor Usage Guide](network_executor_usage.md).

## Conclusion

The `lionfuncs.network` module provides a robust set of tools for interacting
with APIs and web services. By combining the `AsyncAPIClient` with resilience
patterns, SDK adapters, rate limiters, and the advanced API call management
components (`Executor`, `NetworkRequestEvent`, and `iModel`), you can build
robust and efficient network clients for your applications.
