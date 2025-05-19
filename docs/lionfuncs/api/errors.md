---
title: "lionfuncs.errors"
---

# lionfuncs.errors

The `errors` module provides custom exception classes for the `lionfuncs`
package. These exceptions are used throughout the package to provide specific
error information and maintain a consistent error handling approach.

## Exception Hierarchy

```
LionError
├── LionFileError
├── LionNetworkError
│   ├── APIClientError
│   │   ├── APIConnectionError
│   │   ├── APITimeoutError
│   │   ├── RateLimitError
│   │   ├── AuthenticationError
│   │   ├── ResourceNotFoundError
│   │   └── ServerError
│   └── CircuitBreakerOpenError
├── LionConcurrencyError
│   └── QueueStateError
└── LionSDKError
```

## Base Exceptions

### LionError

```python
class LionError(Exception)
```

Base exception for all lionfuncs errors. All other exceptions in the package
inherit from this class.

#### Example

```python
from lionfuncs.errors import LionError

def some_function():
    raise LionError("Something went wrong")

try:
    some_function()
except LionError as e:
    print(f"Caught a LionError: {e}")
```

## File System Exceptions

### LionFileError

```python
class LionFileError(LionError)
```

Exception raised for file system operation errors, such as file not found,
permission denied, or other I/O errors.

#### Example

```python
from lionfuncs.errors import LionFileError
from lionfuncs.file_system import read_file
import asyncio

async def read_nonexistent_file():
    try:
        await read_file("nonexistent.txt")
    except LionFileError as e:
        print(f"File error: {e}")

asyncio.run(read_nonexistent_file())
# Output: File error: File not found: nonexistent.txt
```

## Network Exceptions

### LionNetworkError

```python
class LionNetworkError(LionError)
```

Base exception for network operation errors, such as connection issues or
non-HTTP errors.

#### Example

```python
from lionfuncs.errors import LionNetworkError

def network_operation():
    raise LionNetworkError("Network connection failed")

try:
    network_operation()
except LionNetworkError as e:
    print(f"Network error: {e}")
```

### APIClientError

```python
class APIClientError(LionNetworkError)
```

Base exception for HTTP client errors from AsyncAPIClient.

#### Parameters

- **message** (`str`): The error message.
- **status_code** (`int | None`, optional): The HTTP status code. Defaults to
  `None`.
- **response_content** (`str | bytes | None`, optional): The response content.
  Defaults to `None`.

#### Example

```python
from lionfuncs.errors import APIClientError

def api_operation():
    raise APIClientError("API request failed", status_code=400, response_content="Bad request")

try:
    api_operation()
except APIClientError as e:
    print(f"API error: {e}")
    print(f"Status code: {e.status_code}")
    print(f"Response content: {e.response_content}")
```

### APIConnectionError

```python
class APIConnectionError(APIClientError)
```

Exception raised when the client cannot connect to the server.

### APITimeoutError

```python
class APITimeoutError(APIClientError)
```

Exception raised when a request times out.

### RateLimitError

```python
class RateLimitError(APIClientError)
```

Exception raised for 429 status codes, indicating rate limiting.

#### Parameters

- **message** (`str`, optional): The error message. Defaults to "Rate limit
  exceeded".
- **retry_after** (`int | None`, optional): The time in seconds to wait before
  retrying. Defaults to `None`.
- **\*\*kwargs**: Additional keyword arguments to pass to the parent class.

#### Example

```python
from lionfuncs.errors import RateLimitError

def rate_limited_operation():
    raise RateLimitError(retry_after=60)

try:
    rate_limited_operation()
except RateLimitError as e:
    print(f"Rate limit error: {e}")
    print(f"Retry after: {e.retry_after} seconds")
```

### AuthenticationError

```python
class AuthenticationError(APIClientError)
```

Exception raised for 401/403 status codes, indicating
authentication/authorization issues.

### ResourceNotFoundError

```python
class ResourceNotFoundError(APIClientError)
```

Exception raised for 404 status codes.

### ServerError

```python
class ServerError(APIClientError)
```

Exception raised for 5xx status codes.

### CircuitBreakerOpenError

```python
class CircuitBreakerOpenError(LionNetworkError)
```

Exception raised when an operation is blocked by an open circuit breaker.

#### Parameters

- **message** (`str`): The error message.
- **retry_after** (`float | None`, optional): The time in seconds to wait before
  retrying. Defaults to `None`.

#### Example

```python
from lionfuncs.errors import CircuitBreakerOpenError

def circuit_breaker_operation():
    raise CircuitBreakerOpenError("Circuit breaker is open", retry_after=30.0)

try:
    circuit_breaker_operation()
except CircuitBreakerOpenError as e:
    print(f"Circuit breaker error: {e}")
    if e.retry_after is not None:
        print(f"Retry after: {e.retry_after} seconds")
```

## Concurrency Exceptions

### LionConcurrencyError

```python
class LionConcurrencyError(LionError)
```

Base exception for concurrency primitive errors.

### QueueStateError

```python
class QueueStateError(LionConcurrencyError)
```

Exception raised for invalid operations on a queue given its current state.

#### Parameters

- **message** (`str`): The error message.
- **current_state** (`str | None`, optional): The current state of the queue.
  Defaults to `None`.

#### Example

```python
from lionfuncs.errors import QueueStateError
from lionfuncs.concurrency import BoundedQueue, QueueStatus
import asyncio

async def queue_operation():
    queue = BoundedQueue(maxsize=10)
    try:
        # Try to get an item from a queue that hasn't been started
        await queue.get()
    except QueueStateError as e:
        print(f"Queue error: {e}")
        if e.current_state:
            print(f"Current state: {e.current_state}")

asyncio.run(queue_operation())
# Output: Queue error: Cannot get items when queue is idle (Current State: idle)
```

## SDK Exceptions

### LionSDKError

```python
class LionSDKError(LionError)
```

Base exception for errors originating from SDK interactions. Specific SDK errors
should inherit from this class (e.g., `OpenAISDKError`, `AnthropicSDKError`).

#### Parameters

- **message** (`str`): The error message.
- **original_exception** (`Exception | None`, optional): The original exception
  that was caught. Defaults to `None`.

#### Example

```python
from lionfuncs.errors import LionSDKError

def sdk_operation():
    try:
        # Some SDK operation
        raise ValueError("SDK-specific error")
    except ValueError as e:
        raise LionSDKError("Error in SDK operation", original_exception=e)

try:
    sdk_operation()
except LionSDKError as e:
    print(f"SDK error: {e}")
    if e.original_exception:
        print(f"Original exception: {e.original_exception}")
```
