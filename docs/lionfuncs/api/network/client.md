---
title: "lionfuncs.network.client"
---

# lionfuncs.network.client

The `network.client` module provides the `AsyncAPIClient` class, which is a
robust async HTTP client for API interactions with proper resource management.

## Classes

### AsyncAPIClient

```python
class AsyncAPIClient
```

Generic async HTTP client for API interactions with proper resource management.

This client handles session management, connection pooling, and proper resource
cleanup. It implements the async context manager protocol for resource
management.

#### Constructor

```python
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
)
```

- **base_url** (`str`): The base URL for the API.
- **timeout** (`float`, optional): The timeout for requests in seconds. Defaults
  to `10.0`.
- **headers** (`Optional[dict[str, str]]`, optional): Default headers to include
  with every request. Defaults to `None`.
- **auth** (`Optional[httpx.Auth]`, optional): Authentication to use for
  requests. Defaults to `None`.
- **client** (`Optional[httpx.AsyncClient]`, optional): An existing
  httpx.AsyncClient to use instead of creating a new one. Defaults to `None`.
- **circuit_breaker** (`Optional[CircuitBreaker]`, optional): Optional circuit
  breaker for resilience. Defaults to `None`.
- **retry_config** (`Optional[RetryConfig]`, optional): Optional retry
  configuration for resilience. Defaults to `None`.
- **\*\*client_kwargs**: Additional keyword arguments to pass to
  httpx.AsyncClient.

#### Methods

##### close

```python
async def close(self) -> None
```

Close the client session and release resources.

This method is idempotent and can be called multiple times.

##### request

```python
async def request(self, method: str, url: str, **kwargs) -> Any
```

Make a request to the API.

- **method** (`str`): The HTTP method to use.
- **url** (`str`): The URL to request.
- **\*\*kwargs**: Additional keyword arguments to pass to
  httpx.AsyncClient.request.

**Returns**:

- `Any`: The parsed response data.

**Raises**:

- `APIConnectionError`: If a connection error occurs.
- `APITimeoutError`: If the request times out.
- `RateLimitError`: If a rate limit is exceeded.
- `AuthenticationError`: If authentication fails.
- `ResourceNotFoundError`: If a resource is not found.
- `ServerError`: If a server error occurs.
- `APIClientError`: For other API client errors.

##### call

```python
async def call(self, request: dict[str, Any], **kwargs) -> Any
```

Make a call to the API using the ResourceClient protocol.

This method is part of the ResourceClient protocol and provides a generic way to
make API calls.

- **request** (`dict[str, Any]`): The request parameters.
- **\*\*kwargs**: Additional keyword arguments for the request.

**Returns**:

- `Any`: The parsed response data.

#### Context Manager

`AsyncAPIClient` implements the async context manager protocol (`__aenter__` and
`__aexit__`), allowing it to be used with `async with`:

```python
async with AsyncAPIClient(base_url="https://api.example.com") as client:
    response = await client.request("GET", "/endpoint")
```

#### Examples

##### Basic Usage

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

##### Using the call Method

```python
import asyncio
from lionfuncs.network import AsyncAPIClient

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

##### With Resilience Patterns

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

##### Error Handling

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

## Implementation Details

### HTTP Client

`AsyncAPIClient` uses [httpx](https://www.python-httpx.org/) as its underlying
HTTP client. httpx is a fully featured HTTP client for Python 3, which provides
sync and async APIs, and support for HTTP/1.1 and HTTP/2.

### Resource Management

The client properly manages resources by:

1. Creating a shared httpx.AsyncClient instance when needed
2. Properly closing the client when the context manager exits
3. Ensuring that responses are properly closed, even if the coroutine is
   cancelled

### Resilience Patterns

The client can be configured with resilience patterns:

1. **Circuit Breaker**: Prevents repeated calls to a failing service
2. **Retry with Backoff**: Automatically retries failed requests with
   exponential backoff

These patterns can be used individually or together. When both are used, the
circuit breaker wraps the retry logic.

### Error Mapping

The client maps HTTP errors to specific exception types from `lionfuncs.errors`:

| HTTP Status | Exception               |
| ----------- | ----------------------- |
| 401, 403    | `AuthenticationError`   |
| 404         | `ResourceNotFoundError` |
| 429         | `RateLimitError`        |
| 5xx         | `ServerError`           |
| Other       | `APIClientError`        |

Connection errors are mapped to `APIConnectionError`, and timeouts to
`APITimeoutError`.
