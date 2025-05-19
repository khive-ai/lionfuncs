---
title: "Resilience Patterns Guide"
---

# Resilience Patterns Guide

This guide covers how to use the resilience patterns provided by the
`lionfuncs.network.resilience` module to build robust and fault-tolerant
applications.

## Introduction

When building applications that interact with external services, it's important
to implement resilience patterns to handle failures gracefully. The
`lionfuncs.network.resilience` module provides implementations of common
resilience patterns, including:

- **Circuit Breaker**: Prevents repeated calls to failing services
- **Retry with Backoff**: Automatically retries failed operations with
  exponential backoff

These patterns can be used individually or combined to create robust
applications that can handle transient failures and service outages.

## Circuit Breaker Pattern

The circuit breaker pattern prevents repeated calls to a failing service, based
on the principle of "fail fast" for better system resilience. When a service
fails repeatedly, the circuit opens and rejects requests for a period of time,
then transitions to a half-open state to test if the service has recovered.

### Basic Usage

```python
import asyncio
from lionfuncs.network.resilience import CircuitBreaker
from lionfuncs.errors import CircuitBreakerOpenError

# Create a circuit breaker
breaker = CircuitBreaker(
    failure_threshold=3,     # Open after 3 failures
    recovery_time=10.0,      # Wait 10 seconds before trying again
    half_open_max_calls=1,   # Allow 1 test call in half-open state
    name="api-circuit-breaker"
)

async def call_external_service(param):
    # Simulate an external service call
    if param % 3 == 0:
        raise ConnectionError("Service unavailable")
    return f"Result for {param}"

async def main():
    for i in range(10):
        try:
            # Execute with circuit breaker protection
            result = await breaker.execute(call_external_service, i)
            print(f"Call {i} succeeded: {result}")
        except CircuitBreakerOpenError as e:
            print(f"Circuit is open: {e}")
        except Exception as e:
            print(f"Call {i} failed: {e}")

        await asyncio.sleep(1)

asyncio.run(main())
```

### Using the Circuit Breaker Decorator

For a more elegant approach, you can use the `@circuit_breaker` decorator:

```python
import asyncio
from lionfuncs.network.resilience import circuit_breaker
from lionfuncs.errors import CircuitBreakerOpenError

@circuit_breaker(
    failure_threshold=3,
    recovery_time=10.0,
    name="api-service"
)
async def call_external_service(param):
    # Simulate an external service call
    if param % 3 == 0:
        raise ConnectionError("Service unavailable")
    return f"Result for {param}"

async def main():
    for i in range(10):
        try:
            result = await call_external_service(i)
            print(f"Call {i} succeeded: {result}")
        except CircuitBreakerOpenError as e:
            print(f"Circuit is open: {e}")
        except Exception as e:
            print(f"Call {i} failed: {e}")

        await asyncio.sleep(1)

asyncio.run(main())
```

### Circuit Breaker States

The circuit breaker has three states:

1. **CLOSED**: Normal operation, requests are allowed through.
2. **OPEN**: The service is failing, requests are rejected without being
   attempted.
3. **HALF-OPEN**: After the recovery time has elapsed, a limited number of test
   requests are allowed through to check if the service has recovered.

### Excluding Certain Exceptions

You can configure the circuit breaker to ignore certain types of exceptions:

```python
from lionfuncs.network.resilience import circuit_breaker
from lionfuncs.errors import AuthenticationError

@circuit_breaker(
    failure_threshold=3,
    recovery_time=10.0,
    excluded_exceptions={AuthenticationError}
)
async def call_external_service(token, param):
    if not token:
        raise AuthenticationError("Invalid token")
    if param % 3 == 0:
        raise ConnectionError("Service unavailable")
    return f"Result for {param}"
```

In this example, `AuthenticationError` exceptions won't count toward the failure
threshold.

## Retry with Backoff Pattern

The retry with backoff pattern automatically retries failed operations with
exponential backoff, which helps to avoid overwhelming a recovering service.

### Basic Usage

```python
import asyncio
import random
from lionfuncs.network.resilience import retry_with_backoff

async def flaky_service(param):
    # Simulate a service that sometimes fails
    if random.random() < 0.7:
        raise ConnectionError("Service temporarily unavailable")
    return f"Result for {param}"

async def main():
    try:
        # Retry the function with backoff
        result = await retry_with_backoff(
            flaky_service,
            42,  # param for flaky_service
            max_retries=5,
            base_delay=1.0,
            backoff_factor=2.0,
            jitter=True
        )
        print(f"Success: {result}")
    except Exception as e:
        print(f"Failed after retries: {e}")

asyncio.run(main())
```

### Using the Retry Decorator

For a more elegant approach, you can use the `@with_retry` decorator:

```python
import asyncio
import random
from lionfuncs.network.resilience import with_retry

@with_retry(
    max_retries=5,
    base_delay=1.0,
    backoff_factor=2.0,
    jitter=True
)
async def flaky_service(param):
    # Simulate a service that sometimes fails
    if random.random() < 0.7:
        raise ConnectionError("Service temporarily unavailable")
    return f"Result for {param}"

async def main():
    try:
        result = await flaky_service(42)
        print(f"Success: {result}")
    except Exception as e:
        print(f"Failed after retries: {e}")

asyncio.run(main())
```

### Configuring Retry Behavior

The retry mechanism can be configured with several parameters:

- `max_retries`: Maximum number of retry attempts
- `base_delay`: Initial delay between retries in seconds
- `max_delay`: Maximum delay between retries in seconds
- `backoff_factor`: Factor to increase delay with each retry
- `jitter`: Whether to add randomness to delay timings
- `jitter_factor`: How much randomness to add as a percentage
- `retry_exceptions`: Tuple of exception types that should trigger retry
- `exclude_exceptions`: Tuple of exception types that should not be retried

### Using RetryConfig

For reusable retry configurations, you can use the `RetryConfig` class:

```python
import asyncio
from lionfuncs.network.resilience import RetryConfig, retry_with_backoff
from lionfuncs.errors import APITimeoutError, AuthenticationError

# Create a reusable configuration
retry_config = RetryConfig(
    max_retries=3,
    base_delay=1.0,
    backoff_factor=2.0,
    jitter=True,
    retry_exceptions=(APITimeoutError, ConnectionError),
    exclude_exceptions=(AuthenticationError,)
)

async def call_service(param):
    # Simulate a service call
    if param % 3 == 0:
        raise APITimeoutError("Service timeout")
    if param % 5 == 0:
        raise AuthenticationError("Invalid credentials")
    return f"Result for {param}"

async def main():
    for i in range(10):
        try:
            # Use the config to retry the function
            result = await retry_with_backoff(
                call_service,
                i,
                **retry_config.as_kwargs()
            )
            print(f"Call {i} succeeded: {result}")
        except Exception as e:
            print(f"Call {i} failed after retries: {e}")

asyncio.run(main())
```

## Combining Resilience Patterns

For maximum resilience, you can combine the circuit breaker and retry patterns.
The recommended approach is to apply the circuit breaker as the outer pattern
and retry as the inner pattern:

```python
import asyncio
import random
from lionfuncs.network.resilience import circuit_breaker, with_retry
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
    backoff_factor=2.0,
    jitter=True
)
async def call_external_service(param):
    # Simulate a flaky service
    if random.random() < 0.7:
        raise ConnectionError("Service temporarily unavailable")
    return f"Result for {param}"

async def main():
    for i in range(10):
        try:
            result = await call_external_service(i)
            print(f"Call {i} succeeded: {result}")
        except CircuitBreakerOpenError as e:
            print(f"Circuit is open: {e}")
        except Exception as e:
            print(f"Call {i} failed after retries: {e}")

        await asyncio.sleep(1)

asyncio.run(main())
```

This approach ensures that:

1. The function will be retried a few times if it fails
2. If it keeps failing despite retries, the circuit will open
3. While the circuit is open, no calls will be made, preventing further load on
   the failing service
4. After the recovery time, a test call will be allowed to check if the service
   has recovered

## Using with AsyncAPIClient

The resilience patterns can be used with the `AsyncAPIClient` from the
`lionfuncs.network` module:

```python
import asyncio
from lionfuncs.network import AsyncAPIClient, CircuitBreaker, RetryConfig
from lionfuncs.errors import CircuitBreakerOpenError

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
        except CircuitBreakerOpenError as e:
            print(f"Circuit is open: {e}")
        except Exception as e:
            print(f"Failed to fetch data: {e}")

asyncio.run(main())
```

## Advanced Usage

### Circuit Breaker Metrics

The `CircuitBreaker` class provides metrics to help monitor its behavior:

```python
import asyncio
from lionfuncs.network.resilience import CircuitBreaker

breaker = CircuitBreaker(name="api-circuit-breaker")

async def main():
    # ... use the circuit breaker ...

    # Get metrics
    metrics = breaker.metrics
    print(f"Success count: {metrics['success_count']}")
    print(f"Failure count: {metrics['failure_count']}")
    print(f"Rejected count: {metrics['rejected_count']}")

    # State changes history
    for change in metrics['state_changes']:
        print(f"State changed from {change['from']} to {change['to']} at {change['time']}")

asyncio.run(main())
```

### Custom Retry Logic

For more complex retry scenarios, you can create custom retry logic:

```python
import asyncio
import random
from lionfuncs.network.resilience import retry_with_backoff
from lionfuncs.errors import RateLimitError

async def call_rate_limited_api(param):
    # Simulate a rate-limited API
    if random.random() < 0.5:
        retry_after = random.uniform(1.0, 5.0)
        raise RateLimitError(f"Rate limit exceeded", retry_after=retry_after)
    return f"Result for {param}"

async def main():
    retry_count = 0
    max_retries = 5

    while True:
        try:
            result = await call_rate_limited_api(42)
            print(f"Success: {result}")
            break
        except RateLimitError as e:
            retry_count += 1
            if retry_count > max_retries:
                print(f"Failed after {max_retries} retries")
                break

            print(f"Rate limited, waiting for {e.retry_after} seconds")
            await asyncio.sleep(e.retry_after)
        except Exception as e:
            print(f"Unexpected error: {e}")
            break

asyncio.run(main())
```

## Best Practices

1. **Choose Appropriate Thresholds**: Set failure thresholds and retry counts
   based on the characteristics of the service you're calling.

2. **Use Jitter**: Always enable jitter for retry delays to prevent synchronized
   retries from multiple clients.

3. **Set Reasonable Timeouts**: Combine resilience patterns with appropriate
   timeouts to prevent long-running operations.

4. **Monitor Circuit State**: Log or expose metrics about circuit breaker state
   changes to help diagnose issues.

5. **Layer Resilience Patterns**: Apply circuit breaker as the outer layer and
   retry as the inner layer for maximum resilience.

6. **Exclude Non-Retryable Errors**: Configure retry and circuit breaker to
   exclude exceptions that won't benefit from retries (like authentication
   errors).

7. **Test Failure Scenarios**: Test your resilience patterns with simulated
   failures to ensure they behave as expected.

## Conclusion

The resilience patterns provided by `lionfuncs.network.resilience` help you
build robust applications that can handle transient failures and service
outages. By combining the circuit breaker and retry patterns, you can create
systems that degrade gracefully under failure conditions and recover
automatically when services become available again.
