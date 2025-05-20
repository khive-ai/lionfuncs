---
title: "lionfuncs.network.primitives"
---

# lionfuncs.network.primitives

The `network.primitives` module provides network primitives for API
interactions, including endpoint configuration, header factories, and rate
limiting.

## Classes

### HeaderFactory

```python
class HeaderFactory
```

Utility for creating authentication and content headers.

#### Static Methods

##### get_content_type_header

```python
@staticmethod
def get_content_type_header(
    content_type: str = "application/json",
) -> dict[str, str]
```

Get content type header.

- **content_type** (`str`, optional): The content type to use. Defaults to
  `"application/json"`.

**Returns**:

- `dict[str, str]`: A dictionary with the Content-Type header.

##### get_bearer_auth_header

```python
@staticmethod
def get_bearer_auth_header(api_key: str) -> dict[str, str]
```

Get Bearer authentication header.

- **api_key** (`str`): The API key to use.

**Returns**:

- `dict[str, str]`: A dictionary with the Authorization header.

##### get_x_api_key_header

```python
@staticmethod
def get_x_api_key_header(api_key: str) -> dict[str, str]
```

Get X-API-Key header.

- **api_key** (`str`): The API key to use.

**Returns**:

- `dict[str, str]`: A dictionary with the x-api-key header.

##### get_header

```python
@staticmethod
def get_header(
    auth_type: AUTH_TYPES,
    content_type: str = "application/json",
    api_key: Optional[str] = None,
    default_headers: Optional[dict[str, str]] = None,
) -> dict[str, str]
```

Get headers for API requests.

- **auth_type** (`AUTH_TYPES`): The authentication type to use ("bearer" or
  "x-api-key").
- **content_type** (`str`, optional): The content type to use. Defaults to
  `"application/json"`.
- **api_key** (`Optional[str]`, optional): The API key to use. Defaults to
  `None`.
- **default_headers** (`Optional[dict[str, str]]`, optional): Default headers to
  include. Defaults to `None`.

**Returns**:

- `dict[str, str]`: A dictionary with the headers.

**Raises**:

- `ValueError`: If API key is required but not provided, or if auth type is
  unsupported.

#### Example

```python
from lionfuncs.network import HeaderFactory

# Get content type header
content_headers = HeaderFactory.get_content_type_header("application/json")
print(f"Content headers: {content_headers}")

# Get Bearer auth header
auth_headers = HeaderFactory.get_bearer_auth_header("your-api-key")
print(f"Auth headers: {auth_headers}")

# Get combined headers
headers = HeaderFactory.get_header(
    auth_type="bearer",
    content_type="application/json",
    api_key="your-api-key",
    default_headers={"User-Agent": "lionfuncs/0.1.0"}
)
print(f"Combined headers: {headers}")
```

### EndpointConfig

```python
class EndpointConfig(BaseModel)
```

Configuration for an API endpoint.

#### Attributes

- **name** (`str`): The name of the endpoint.
- **provider** (`str`): The provider name.
- **transport_type** (`Literal["http", "sdk"]`): The transport type. Default:
  `"http"`.
- **base_url** (`Optional[str]`): The base URL for the API. Default: `None`.
- **endpoint** (`str`): The endpoint path.
- **endpoint_params** (`Optional[list[str]]`): Parameters for the endpoint path.
  Default: `None`.
- **method** (`str`): The HTTP method. Default: `"POST"`.
- **params** (`dict[str, str]`): Query parameters. Default: `{}`.
- **content_type** (`str`): The content type. Default: `"application/json"`.
- **auth_type** (`AUTH_TYPES`): The authentication type. Default: `"bearer"`.
- **default_headers** (`dict[str, str]`): Default headers. Default: `{}`.
- **api_key** (`Optional[str]`): The API key. Default: `None`.
- **timeout** (`int`): The timeout in seconds. Default: `300`.
- **max_retries** (`int`): The maximum number of retries. Default: `3`.
- **kwargs** (`dict[str, Any]`): Additional keyword arguments. Default: `{}`.
- **client_kwargs** (`dict[str, Any]`): Additional keyword arguments for the
  client. Default: `{}`.

#### Properties

##### full_url

```python
@property
def full_url(self) -> str
```

Get the full URL for the endpoint.

**Returns**:

- `str`: The full URL with base URL and endpoint path.

#### Methods

##### update

```python
def update(self, **kwargs) -> None
```

Update the config with new values.

- **\*\*kwargs**: The values to update.

#### Example

```python
from lionfuncs.network import EndpointConfig

# Create an endpoint configuration
config = EndpointConfig(
    name="get_users",
    provider="example",
    base_url="https://api.example.com",
    endpoint="users",
    method="GET",
    auth_type="bearer",
    api_key="your-api-key"
)

# Get the full URL
print(f"Full URL: {config.full_url}")

# Update the configuration
config.update(
    method="POST",
    endpoint="users/create",
    content_type="application/json"
)
print(f"Updated URL: {config.full_url}")
```

### Endpoint

```python
class Endpoint
```

API endpoint for making requests.

This class represents an API endpoint and provides methods for making requests
to that endpoint.

#### Constructor

```python
def __init__(
    self,
    config: Union[dict[str, Any], EndpointConfig],
    **kwargs,
)
```

- **config** (`Union[dict[str, Any], EndpointConfig]`): The endpoint
  configuration.
- **\*\*kwargs**: Additional keyword arguments to update the configuration.

**Raises**:

- `TypeError`: If config is not a dict or EndpointConfig.

#### Methods

##### create_payload

```python
def create_payload(
    self,
    request: Union[dict[str, Any], BaseModel],
    extra_headers: Optional[dict[str, str]] = None,
    **kwargs,
) -> tuple[dict[str, Any], dict[str, str]]
```

Create payload and headers for a request.

- **request** (`Union[dict[str, Any], BaseModel]`): The request parameters or
  model.
- **extra_headers** (`Optional[dict[str, str]]`, optional): Additional headers
  to include. Defaults to `None`.
- **\*\*kwargs**: Additional keyword arguments for the request.

**Returns**:

- `tuple[dict[str, Any], dict[str, str]]`: A tuple of (payload, headers).

#### Example

```python
from lionfuncs.network import Endpoint, EndpointConfig

# Create an endpoint configuration
config = EndpointConfig(
    name="get_users",
    provider="example",
    base_url="https://api.example.com",
    endpoint="users",
    method="GET",
    auth_type="bearer",
    api_key="your-api-key"
)

# Create an endpoint
endpoint = Endpoint(config)

# Create payload and headers for a request
request = {"limit": 10, "offset": 0}
payload, headers = endpoint.create_payload(
    request,
    extra_headers={"X-Request-ID": "123"}
)
print(f"Payload: {payload}")
print(f"Headers: {headers}")
```

### TokenBucketRateLimiter

```python
class TokenBucketRateLimiter
```

Rate limiter using the token bucket algorithm.

The token bucket algorithm allows for controlled bursts of requests while
maintaining a long-term rate limit. Tokens are added to the bucket at a constant
rate, and each request consumes one or more tokens. If the bucket is empty,
requests must wait until enough tokens are available.

#### Constructor

```python
def __init__(
    self,
    rate: float,
    period: float = 1.0,
    max_tokens: Optional[float] = None,
    initial_tokens: Optional[float] = None,
)
```

- **rate** (`float`): Maximum number of tokens per period.
- **period** (`float`, optional): Time period in seconds. Defaults to `1.0`.
- **max_tokens** (`Optional[float]`, optional): Maximum token bucket capacity
  (defaults to rate). Defaults to `None`.
- **initial_tokens** (`Optional[float]`, optional): Initial token count
  (defaults to max_tokens). Defaults to `None`.

#### Methods

##### acquire

```python
async def acquire(self, tokens: float = 1.0) -> float
```

Acquire tokens from the bucket.

- **tokens** (`float`, optional): Number of tokens to acquire. Defaults to
  `1.0`.

**Returns**:

- `float`: Wait time in seconds before tokens are available. Returns 0.0 if
  tokens are immediately available.

##### execute

```python
async def execute(self, func: Callable[..., Any], *args: Any, **kwargs: Any) -> Any
```

Execute a coroutine with rate limiting.

- **func** (`Callable[..., Any]`): Async function to execute.
- **\*args** (`Any`): Positional arguments for func.
- **\*\*kwargs** (`Any`): Keyword arguments for func. tokens: Optional number of
  tokens to acquire (default: 1.0). This will be removed from kwargs before
  calling func.

**Returns**:

- `Any`: Result from func.

#### Example

```python
import asyncio
from lionfuncs.network import TokenBucketRateLimiter

async def api_call(i: int):
    print(f"API call {i}")
    await asyncio.sleep(0.1)  # Simulate API call
    return f"Result {i}"

async def main():
    # Create a rate limiter with 5 requests per second
    rate_limiter = TokenBucketRateLimiter(rate=5, period=1.0)

    # Execute 10 API calls with rate limiting
    tasks = []
    for i in range(10):
        # Option 1: Use execute method
        task = asyncio.create_task(
            rate_limiter.execute(api_call, i)
        )
        tasks.append(task)

    # Wait for all tasks to complete
    results = await asyncio.gather(*tasks)
    print(f"Results: {results}")

    # Option 2: Use acquire method directly
    for i in range(10, 20):
        # Acquire tokens (waiting if necessary)
        wait_time = await rate_limiter.acquire(tokens=1.0)
        if wait_time > 0:
            print(f"Rate limited: waiting {wait_time:.2f}s before call {i}")
            await asyncio.sleep(wait_time)

        # Make the API call
        result = await api_call(i)
        print(f"Result: {result}")

asyncio.run(main())
```

### EndpointRateLimiter

```python
class EndpointRateLimiter
```

Rate limiter that manages multiple endpoints with different rate limits.

This class maintains separate rate limiters for different API endpoints,
allowing for fine-grained control over rate limiting.

#### Constructor

```python
def __init__(self, default_rate: float = 10.0, default_period: float = 1.0)
```

- **default_rate** (`float`, optional): Default rate for unknown endpoints.
  Defaults to `10.0`.
- **default_period** (`float`, optional): Default period for unknown endpoints.
  Defaults to `1.0`.

#### Methods

##### get_limiter

```python
def get_limiter(self, endpoint: str) -> TokenBucketRateLimiter
```

Get or create a rate limiter for the endpoint.

- **endpoint** (`str`): API endpoint identifier.

**Returns**:

- `TokenBucketRateLimiter`: The rate limiter for the specified endpoint.

##### execute

```python
async def execute(
    self,
    endpoint: str,
    func: Callable[..., Any],
    *args: Any,
    **kwargs: Any,
) -> Any
```

Execute a coroutine with endpoint-specific rate limiting.

- **endpoint** (`str`): API endpoint identifier.
- **func** (`Callable[..., Any]`): Async function to execute.
- **\*args** (`Any`): Positional arguments for func.
- **\*\*kwargs** (`Any`): Keyword arguments for func. tokens: Optional number of
  tokens to acquire (default: 1.0).

**Returns**:

- `Any`: Result from func.

##### update_rate_limit

```python
async def update_rate_limit(
    self,
    endpoint: str,
    rate: Optional[float] = None,
    period: Optional[float] = None,
    max_tokens: Optional[float] = None,
    reset_tokens: bool = False,
) -> None
```

Update the rate limit parameters for an endpoint.

- **endpoint** (`str`): API endpoint identifier.
- **rate** (`Optional[float]`, optional): New maximum operations per period (if
  None, keep current). Defaults to `None`.
- **period** (`Optional[float]`, optional): New time period in seconds (if None,
  keep current). Defaults to `None`.
- **max_tokens** (`Optional[float]`, optional): New maximum token capacity (if
  None, keep current). Defaults to `None`.
- **reset_tokens** (`bool`, optional): If True, reset current tokens to
  max_tokens. Defaults to `False`.

#### Example

```python
import asyncio
from lionfuncs.network import EndpointRateLimiter

async def api_call(endpoint: str, i: int):
    print(f"API call to {endpoint} {i}")
    await asyncio.sleep(0.1)  # Simulate API call
    return f"Result from {endpoint} {i}"

async def main():
    # Create an endpoint rate limiter
    rate_limiter = EndpointRateLimiter(default_rate=10.0)

    # Update rate limits for specific endpoints
    await rate_limiter.update_rate_limit("users", rate=5.0)
    await rate_limiter.update_rate_limit("orders", rate=2.0)

    # Execute API calls to different endpoints
    tasks = []

    # 10 calls to /users endpoint (rate limit: 5 per second)
    for i in range(10):
        task = asyncio.create_task(
            rate_limiter.execute("users", api_call, "users", i)
        )
        tasks.append(task)

    # 5 calls to /orders endpoint (rate limit: 2 per second)
    for i in range(5):
        task = asyncio.create_task(
            rate_limiter.execute("orders", api_call, "orders", i)
        )
        tasks.append(task)

    # Wait for all tasks to complete
    results = await asyncio.gather(*tasks)
    print(f"Results: {results}")

asyncio.run(main())
```

### AdaptiveRateLimiter

```python
class AdaptiveRateLimiter(TokenBucketRateLimiter)
```

Rate limiter that can adapt its limits based on API response headers.

This class extends TokenBucketRateLimiter to automatically adjust rate limits
based on response headers from API calls. It supports common rate limit header
patterns used by various APIs.

#### Constructor

```python
def __init__(
    self,
    initial_rate: float,
    initial_period: float = 1.0,
    max_tokens: Optional[float] = None,
    min_rate: float = 1.0,
    safety_factor: float = 0.9,
)
```

- **initial_rate** (`float`): Initial maximum operations per period.
- **initial_period** (`float`, optional): Initial time period in seconds.
  Defaults to `1.0`.
- **max_tokens** (`Optional[float]`, optional): Maximum token capacity (defaults
  to initial_rate). Defaults to `None`.
- **min_rate** (`float`, optional): Minimum rate to maintain even with strict
  API limits. Defaults to `1.0`.
- **safety_factor** (`float`, optional): Factor to multiply API limits by for
  safety margin. Defaults to `0.9`.

#### Methods

##### update_from_headers

```python
def update_from_headers(self, headers: dict[str, str]) -> None
```

Update rate limits based on API response headers.

Supports common header patterns:

- X-RateLimit-Limit, X-RateLimit-Remaining, X-RateLimit-Reset
- X-Rate-Limit-Limit, X-Rate-Limit-Remaining, X-Rate-Limit-Reset
- RateLimit-Limit, RateLimit-Remaining, RateLimit-Reset
- ratelimit-limit, ratelimit-remaining, ratelimit-reset
- X-RL-Limit, X-RL-Remaining, X-RL-Reset

- **headers** (`dict[str, str]`): Response headers from API.

#### Example

```python
import asyncio
from lionfuncs.network import AdaptiveRateLimiter, AsyncAPIClient

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

            print(f"Response: {response}")

asyncio.run(main())
```

## Functions

### match_endpoint

```python
def match_endpoint(
    provider: str,
    endpoint: str,
    **kwargs,
) -> Optional[Endpoint]
```

Match an endpoint by provider and endpoint name.

#### Parameters

- **provider** (`str`): The provider name.
- **endpoint** (`str`): The endpoint name.
- **\*\*kwargs**: Additional keyword arguments for the endpoint.

#### Returns

- `Optional[Endpoint]`: An Endpoint instance, or None if no match is found.

#### Example

```python
from lionfuncs.network import match_endpoint

# Match an endpoint
endpoint = match_endpoint(
    "openai",
    "chat.completions",
    base_url="https://api.openai.com/v1",
    api_key="your-api-key"
)

if endpoint:
    # Create payload and headers for a request
    payload, headers = endpoint.create_payload({
        "model": "gpt-3.5-turbo",
        "messages": [
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": "Hello, world!"}
        ]
    })
    print(f"Payload: {payload}")
    print(f"Headers: {headers}")
```

## Implementation Details

### Rate Limiting Algorithms

#### Token Bucket Algorithm

The `TokenBucketRateLimiter` implements the token bucket algorithm:

1. Tokens are added to the bucket at a constant rate (rate/period).
2. The bucket has a maximum capacity (max_tokens).
3. Each request consumes one or more tokens.
4. If the bucket is empty, requests must wait until enough tokens are available.

#### Adaptive Rate Limiting

The `AdaptiveRateLimiter` extends the token bucket algorithm to adapt to API
rate limits:

1. It parses rate limit headers from API responses.
2. It adjusts the rate based on the remaining calls and reset time.
3. It applies a safety factor to avoid hitting the limit.
4. It ensures the rate doesn't go below a minimum value.

### Header Patterns

The `AdaptiveRateLimiter` supports common rate limit header patterns:

- X-RateLimit-Limit, X-RateLimit-Remaining, X-RateLimit-Reset (GitHub, many
  others)
- X-Rate-Limit-Limit, X-Rate-Limit-Remaining, X-Rate-Limit-Reset (Twitter)
- RateLimit-Limit, RateLimit-Remaining, RateLimit-Reset (RFC 6585)
- ratelimit-limit, ratelimit-remaining, ratelimit-reset (lowercase variants)
- X-RL-Limit, X-RL-Remaining, X-RL-Reset (shorthand variants)
- Retry-After (simpler format used by some APIs)

### HttpTransportConfig

```python
class HttpTransportConfig(BaseModel)
```

Configuration for HTTP transport in ServiceEndpointConfig.

#### Attributes

- **method** (`str`): Default HTTP method if not overridden at call time.
  Default: `"POST"`.

### SdkTransportConfig

```python
class SdkTransportConfig(BaseModel)
```

Configuration for SDK transport in ServiceEndpointConfig.

#### Attributes

- **sdk_provider_name** (`str`): The name of the SDK provider (e.g., "openai",
  "anthropic").
- **default_sdk_method_name** (`Optional[str]`): Default SDK method to call if
  not specified in invoke(). Default: `None`.

### ServiceEndpointConfig

```python
class ServiceEndpointConfig(BaseModel)
```

Comprehensive configuration for API endpoints. This model provides a complete
configuration for the Endpoint class, supporting both HTTP and SDK transport
types.

#### Attributes

- **name** (`str`): User-defined name for this endpoint configuration (e.g.,
  'openai_chat_completions_gpt4').
- **transport_type** (`Literal["http", "sdk"]`): Specifies if direct HTTP or an
  SDK adapter is used.
- **api_key** (`Optional[str]`): API key. Can be set via env var or direct
  value. Default: `None`.
- **base_url** (`Optional[str]`): Base URL for HTTP calls or if required by an
  SDK. Default: `None`.
- **timeout** (`float`): Default request timeout in seconds. Default: `60.0`.
- **default_headers** (`dict[str, str]`): Default headers for HTTP requests.
  Default: `{}`.
- **client_constructor_kwargs** (`dict[str, Any]`): Keyword arguments passed
  directly to the constructor of AsyncAPIClient or the specific SDK client.
  Default: `{}`.
- **http_config** (`Optional[HttpTransportConfig]`): Configuration specific to
  HTTP transport. Default: `None`.
- **sdk_config** (`Optional[SdkTransportConfig]`): Configuration specific to SDK
  transport. Default: `None`.
- **default_request_kwargs** (`dict[str, Any]`): Default keyword arguments to be
  included in every request made through this endpoint. Default: `{}`.

#### Validation

The model performs validation after initialization to ensure:

1. For HTTP transport, http_config is provided (or a default is created) and
   base_url is required.
2. For SDK transport, sdk_config is required.

#### Example

```python
from lionfuncs.network.primitives import ServiceEndpointConfig, HttpTransportConfig, SdkTransportConfig

# HTTP transport configuration
http_config = ServiceEndpointConfig(
    name="openai_chat",
    transport_type="http",
    base_url="https://api.openai.com/v1",
    api_key="your-api-key",
    timeout=30.0,
    default_headers={"User-Agent": "lionfuncs/0.1.0"},
    http_config=HttpTransportConfig(method="POST"),
    default_request_kwargs={"model": "gpt-4"}
)

# SDK transport configuration
sdk_config = ServiceEndpointConfig(
    name="openai_sdk",
    transport_type="sdk",
    api_key="your-api-key",
    sdk_config=SdkTransportConfig(
        sdk_provider_name="openai",
        default_sdk_method_name="chat.completions.create"
    ),
    client_constructor_kwargs={"organization": "your-org-id"},
    default_request_kwargs={"model": "gpt-4"}
)
```
