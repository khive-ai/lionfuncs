---
title: "lionfuncs.network.resilience"
---

# lionfuncs.network.resilience

The `network.resilience` module provides resilience patterns for API clients,
including the circuit breaker pattern and retry with exponential backoff.

## Classes

### CircuitState

```python
class CircuitState(Enum)
```

Enum for circuit breaker states.

#### Values

- `CLOSED`: Normal operation, requests are allowed.
- `OPEN`: Failing state, requests are rejected.
- `HALF_OPEN`: Testing if service has recovered, limited requests are allowed.

### CircuitBreaker

```python
class CircuitBreaker
```

Circuit breaker pattern implementation for preventing calls to failing services.

The circuit breaker pattern prevents repeated calls to a failing service, based
on the principle of "fail fast" for better system resilience. When a service
fails repeatedly, the circuit opens and rejects requests for a period of time,
then transitions to a half-open state to test if the service has recovered.

#### Constructor

```python
def __init__(
    self,
    failure_threshold: int = 5,
    recovery_time: float = 30.0,
    half_open_max_calls: int = 1,
    excluded_exceptions: Optional[set[type[Exception]]] = None,
    name: str = "default",
)
```

- **failure_threshold** (`int`, optional): Number of failures before opening the
  circuit. Defaults to `5`.
- **recovery_time** (`float`, optional): Time in seconds to wait before
  transitioning to half-open. Defaults to `30.0`.
- **half_open_max_calls** (`int`, optional): Maximum number of calls allowed in
  half-open state. Defaults to `1`.
- **excluded_exceptions** (`Optional[set[type[Exception]]]`, optional): Set of
  exception types that should not count as failures. Defaults to `None`.
- **name** (`str`, optional): Name of the circuit breaker for logging and
  metrics. Defaults to `"default"`.

#### Properties

- **metrics** (`dict[str, Any]`): Get circuit breaker metrics.

#### Methods

##### execute

```python
async def execute(
    self, func: Callable[..., Awaitable[T]], *args: Any, **kwargs: Any
) -> T
```

Execute a coroutine with circuit breaker protection.

- **func** (`Callable[..., Awaitable[T]]`): The coroutine function to execute.
- **\*args** (`Any`): Positional arguments for the function.
- **\*\*kwargs** (`Any`): Keyword arguments for the function.

**Returns**:

- `T`: The result of the function execution.

**Raises**:

- `CircuitBreakerOpenError`: If the circuit is open.
- `Exception`: Any exception raised by the function.

#### Example

```python
import asyncio
from lionfuncs.network import CircuitBreaker
from lionfuncs.errors import CircuitBreakerOpenError

async def api_call(succeed: bool = True):
    if not succeed:
        raise ValueError("API call failed")
    return "API response"

async def main():
    # Create a circuit breaker with a failure threshold of 3
    # and a recovery time of 5 seconds
    breaker = CircuitBreaker(
        failure_threshold=3,
        recovery_time=5.0,
        name="api-circuit-breaker"
    )

    # Make some failing calls
    for i in range(5):
        try:
            result = await breaker.execute(api_call, succeed=False)
            print(f"Call {i+1} succeeded: {result}")
        except CircuitBreakerOpenError as e:
            print(f"Call {i+1} rejected: {e}")
        except Exception as e:
            print(f"Call {i+1} failed: {e}")

    # Wait for recovery time
    print("Waiting for recovery...")
    await asyncio.sleep(5)

    # Try again
    try:
        result = await breaker.execute(api_call, succeed=True)
        print(f"Call after recovery succeeded: {result}")
    except CircuitBreakerOpenError as e:
        print(f"Call after recovery rejected: {e}")
    except Exception as e:
        print(f"Call after recovery failed: {e}")

    # Check metrics
    print(f"Circuit breaker metrics: {breaker.metrics}")

asyncio.run(main())
```

### RetryConfig

```python
class RetryConfig
```

Configuration for retry behavior.

#### Constructor

```python
def __init__(
    self,
    max_retries: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 60.0,
    backoff_factor: float = 2.0,
    jitter: bool = True,
    jitter_factor: float = 0.2,
    retry_exceptions: tuple[type[Exception], ...] = (Exception,),
    exclude_exceptions: tuple[type[Exception], ...] = (),
)
```

- **max_retries** (`int`, optional): Maximum number of retry attempts. Defaults
  to `3`.
- **base_delay** (`float`, optional): Initial delay between retries in seconds.
  Defaults to `1.0`.
- **max_delay** (`float`, optional): Maximum delay between retries in seconds.
  Defaults to `60.0`.
- **backoff_factor** (`float`, optional): Multiplier applied to delay after each
  retry. Defaults to `2.0`.
- **jitter** (`bool`, optional): Whether to add randomness to delay timings.
  Defaults to `True`.
- **jitter_factor** (`float`, optional): How much randomness to add as a
  percentage. Defaults to `0.2`.
- **retry_exceptions** (`tuple[type[Exception], ...]`, optional): Tuple of
  exception types that should trigger retry. Defaults to `(Exception,)`.
- **exclude_exceptions** (`tuple[type[Exception], ...]`, optional): Tuple of
  exception types that should not be retried. Defaults to `()`.

#### Methods

##### as_kwargs

```python
def as_kwargs(self) -> dict[str, Any]
```

Convert configuration to keyword arguments for retry_with_backoff.

**Returns**:

- `dict[str, Any]`: Dictionary of keyword arguments.

#### Example

```python
from lionfuncs.network import RetryConfig
from lionfuncs.errors import APITimeoutError, AuthenticationError

# Create a retry configuration
retry_config = RetryConfig(
    max_retries=5,
    base_delay=0.5,
    max_delay=30.0,
    backoff_factor=2.0,
    jitter=True,
    jitter_factor=0.1,
    retry_exceptions=(APITimeoutError, ConnectionError),
    exclude_exceptions=(AuthenticationError,)
)

# Convert to kwargs for retry_with_backoff
kwargs = retry_config.as_kwargs()
print(f"Retry kwargs: {kwargs}")
```

## Functions

### retry_with_backoff

```python
async def retry_with_backoff(
    func: Callable[..., Awaitable[T]],
    *args: Any,
    retry_exceptions: tuple[type[Exception], ...] = (Exception,),
    exclude_exceptions: tuple[type[Exception], ...] = (),
    max_retries: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 60.0,
    backoff_factor: float = 2.0,
    jitter: bool = True,
    jitter_factor: float = 0.2,
    **kwargs: Any,
) -> T
```

Retry an async function with exponential backoff.

#### Parameters

- **func** (`Callable[..., Awaitable[T]]`): The async function to retry.
- **\*args** (`Any`): Positional arguments for the function.
- **retry_exceptions** (`tuple[type[Exception], ...]`, optional): Tuple of
  exception types to retry. Defaults to `(Exception,)`.
- **exclude_exceptions** (`tuple[type[Exception], ...]`, optional): Tuple of
  exception types to not retry. Defaults to `()`.
- **max_retries** (`int`, optional): Maximum number of retries. Defaults to `3`.
- **base_delay** (`float`, optional): Initial delay between retries in seconds.
  Defaults to `1.0`.
- **max_delay** (`float`, optional): Maximum delay between retries in seconds.
  Defaults to `60.0`.
- **backoff_factor** (`float`, optional): Factor to increase delay with each
  retry. Defaults to `2.0`.
- **jitter** (`bool`, optional): Whether to add randomness to the delay.
  Defaults to `True`.
- **jitter_factor** (`float`, optional): How much randomness to add as a
  percentage. Defaults to `0.2`.
- **\*\*kwargs** (`Any`): Keyword arguments for the function.

#### Returns

- `T`: The result of the function execution.

#### Raises

- `Exception`: The last exception raised by the function after all retries.

#### Example

```python
import asyncio
import random
from lionfuncs.network import retry_with_backoff

async def flaky_api_call():
    # Simulate a flaky API that sometimes fails
    if random.random() < 0.7:
        raise ConnectionError("API connection failed")
    return "API response"

async def main():
    try:
        # Retry the flaky API call with exponential backoff
        result = await retry_with_backoff(
            flaky_api_call,
            max_retries=5,
            base_delay=0.5,
            backoff_factor=2.0,
            retry_exceptions=(ConnectionError,)
        )
        print(f"API call succeeded: {result}")
    except Exception as e:
        print(f"API call failed after retries: {e}")

asyncio.run(main())
```

## Decorators

### circuit_breaker

```python
def circuit_breaker(
    failure_threshold: int = 5,
    recovery_time: float = 30.0,
    half_open_max_calls: int = 1,
    excluded_exceptions: Optional[set[type[Exception]]] = None,
    name: Optional[str] = None,
) -> Callable[[Callable[..., Awaitable[T]]], Callable[..., Awaitable[T]]]
```

Decorator to apply circuit breaker pattern to an async function.

#### Parameters

- **failure_threshold** (`int`, optional): Number of failures before opening the
  circuit. Defaults to `5`.
- **recovery_time** (`float`, optional): Time in seconds to wait before
  transitioning to half-open. Defaults to `30.0`.
- **half_open_max_calls** (`int`, optional): Maximum number of calls allowed in
  half-open state. Defaults to `1`.
- **excluded_exceptions** (`Optional[set[type[Exception]]]`, optional): Set of
  exception types that should not count as failures. Defaults to `None`.
- **name** (`Optional[str]`, optional): Name of the circuit breaker for logging
  and metrics. Defaults to `None`.

#### Returns

- `Callable[[Callable[..., Awaitable[T]]], Callable[..., Awaitable[T]]]`: A
  decorator that applies circuit breaker pattern.

#### Example

```python
import asyncio
import random
from lionfuncs.network import circuit_breaker
from lionfuncs.errors import CircuitBreakerOpenError

@circuit_breaker(
    failure_threshold=3,
    recovery_time=5.0,
    name="api-circuit-breaker"
)
async def api_call():
    # Simulate a flaky API that sometimes fails
    if random.random() < 0.7:
        raise ConnectionError("API connection failed")
    return "API response"

async def main():
    # Make several calls to the protected function
    for i in range(10):
        try:
            result = await api_call()
            print(f"Call {i+1} succeeded: {result}")
        except CircuitBreakerOpenError as e:
            print(f"Call {i+1} rejected: {e}")
        except Exception as e:
            print(f"Call {i+1} failed: {e}")

        # Add a small delay between calls
        await asyncio.sleep(0.5)

asyncio.run(main())
```

### with_retry

```python
def with_retry(
    max_retries: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 60.0,
    backoff_factor: float = 2.0,
    jitter: bool = True,
    jitter_factor: float = 0.2,
    retry_exceptions: tuple[type[Exception], ...] = (Exception,),
    exclude_exceptions: tuple[type[Exception], ...] = (),
) -> Callable[[Callable[..., Awaitable[T]]], Callable[..., Awaitable[T]]]
```

Decorator to apply retry with backoff pattern to an async function.

#### Parameters

- **max_retries** (`int`, optional): Maximum number of retry attempts. Defaults
  to `3`.
- **base_delay** (`float`, optional): Initial delay between retries in seconds.
  Defaults to `1.0`.
- **max_delay** (`float`, optional): Maximum delay between retries in seconds.
  Defaults to `60.0`.
- **backoff_factor** (`float`, optional): Multiplier applied to delay after each
  retry. Defaults to `2.0`.
- **jitter** (`bool`, optional): Whether to add randomness to delay timings.
  Defaults to `True`.
- **jitter_factor** (`float`, optional): How much randomness to add as a
  percentage. Defaults to `0.2`.
- **retry_exceptions** (`tuple[type[Exception], ...]`, optional): Tuple of
  exception types that should trigger retry. Defaults to `(Exception,)`.
- **exclude_exceptions** (`tuple[type[Exception], ...]`, optional): Tuple of
  exception types that should not be retried. Defaults to `()`.

#### Returns

- `Callable[[Callable[..., Awaitable[T]]], Callable[..., Awaitable[T]]]`: A
  decorator that applies retry pattern.

#### Example

```python
import asyncio
import random
from lionfuncs.network import with_retry
from lionfuncs.errors import APITimeoutError, AuthenticationError

@with_retry(
    max_retries=5,
    base_delay=0.5,
    backoff_factor=2.0,
    retry_exceptions=(ConnectionError, APITimeoutError),
    exclude_exceptions=(AuthenticationError,)
)
async def api_call():
    # Simulate a flaky API that sometimes fails
    r = random.random()
    if r < 0.4:
        raise ConnectionError("API connection failed")
    elif r < 0.6:
        raise APITimeoutError("API request timed out")
    elif r < 0.7:
        raise AuthenticationError("Authentication failed")
    return "API response"

async def main():
    try:
        result = await api_call()
        print(f"API call succeeded: {result}")
    except Exception as e:
        print(f"API call failed after retries: {e}")

asyncio.run(main())
```

## Combining Resilience Patterns

The circuit breaker and retry patterns can be combined for more robust
resilience:

```python
import asyncio
import random
from lionfuncs.network import circuit_breaker, with_retry
from lionfuncs.errors import CircuitBreakerOpenError, APITimeoutError

# Apply both patterns - circuit breaker wraps retry
@circuit_breaker(
    failure_threshold=3,
    recovery_time=5.0,
    name="api-circuit-breaker"
)
@with_retry(
    max_retries=3,
    base_delay=0.5,
    backoff_factor=2.0,
    retry_exceptions=(ConnectionError, APITimeoutError)
)
async def api_call():
    # Simulate a flaky API that sometimes fails
    if random.random() < 0.7:
        raise ConnectionError("API connection failed")
    return "API response"

async def main():
    for i in range(10):
        try:
            result = await api_call()
            print(f"Call {i+1} succeeded: {result}")
        except CircuitBreakerOpenError as e:
            print(f"Call {i+1} rejected by circuit breaker: {e}")
        except Exception as e:
            print(f"Call {i+1} failed after retries: {e}")

        await asyncio.sleep(0.5)

asyncio.run(main())
```

## Implementation Details

### Circuit Breaker States

The circuit breaker has three states:

1. **CLOSED**: Normal operation, requests are allowed.
2. **OPEN**: Failing state, requests are rejected with
   `CircuitBreakerOpenError`.
3. **HALF_OPEN**: Testing if service has recovered, limited requests are
   allowed.

State transitions:

- CLOSED → OPEN: When failure count reaches `failure_threshold`.
- OPEN → HALF_OPEN: After `recovery_time` seconds.
- HALF_OPEN → CLOSED: On successful request.
- HALF_OPEN → OPEN: On failed request.

### Retry with Backoff Algorithm

The retry with backoff algorithm:

1. Try the operation.
2. If it fails with a retryable exception, wait for `base_delay` seconds.
3. Retry the operation.
4. If it fails again, wait for `base_delay * backoff_factor` seconds.
5. Continue retrying with increasing delays until `max_retries` is reached or
   `max_delay` is hit.
6. If `jitter` is enabled, add randomness to the delay to prevent thundering
   herd problems.
