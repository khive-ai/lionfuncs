---
title: "lionfuncs.network.executor"
---

# lionfuncs.network.executor

The `executor` module provides the Executor class, which manages a queue of API
call tasks, enforces concurrency and rate limits, and tracks request lifecycles.

## Classes

### Executor

```python
class Executor
```

Executor for managing and rate-limiting API calls. The Executor manages a queue
of API call tasks, enforces concurrency and rate limits, and tracks request
lifecycles using NetworkRequestEvent objects.

#### Constructor

```python
def __init__(
    self,
    queue_capacity: int = 1000,
    concurrency_limit: int = 10,
    requests_rate: float = 10.0,
    requests_period: float = 1.0,
    requests_bucket_capacity: Optional[float] = None,
    api_tokens_rate: Optional[float] = None,
    api_tokens_period: float = 60.0,
    api_tokens_bucket_capacity: Optional[float] = None,
    num_workers: int = 5,
)
```

Initialize the Executor.

**Parameters:**

- `queue_capacity`: Max capacity of the internal task queue.
- `concurrency_limit`: Max number of concurrent API calls.
- `requests_rate`: Max requests for the requests_rate_limiter (e.g., 10
  requests).
- `requests_period`: Period in seconds for requests_rate (e.g., per 1 second).
- `requests_bucket_capacity`: Max capacity of the request token bucket. Defaults
  to requests_rate if None.
- `api_tokens_rate`: Max API tokens for the api_tokens_rate_limiter (e.g., 10000
  tokens). If None, this limiter is disabled.
- `api_tokens_period`: Period in seconds for api_tokens_rate (e.g., per 60
  seconds).
- `api_tokens_bucket_capacity`: Max capacity of the API token bucket. Defaults
  to api_tokens_rate if None.
- `num_workers`: Number of worker coroutines to process the queue.

#### Methods

##### submit_task

```python
async def submit_task(
    self,
    api_call_coroutine: Callable[[], Coroutine[Any, Any, Any]],
    endpoint_url: Optional[str] = None,
    method: Optional[str] = None,
    headers: Optional[dict[str, Any]] = None,
    payload: Optional[Any] = None,
    num_api_tokens_needed: int = 0,
    metadata: Optional[dict[str, Any]] = None,
) -> NetworkRequestEvent
```

Submit a new API call task to the executor.

**Parameters:**

- `api_call_coroutine`: A callable that returns a coroutine. The coroutine
  should perform the API call and return a tuple (status_code: int, headers:
  Dict, body: Any) or raise an exception.
- `endpoint_url`: URL of the API endpoint.
- `method`: HTTP method (e.g., "GET", "POST").
- `headers`: Request headers.
- `payload`: Request payload/body.
- `num_api_tokens_needed`: Number of API-specific tokens this call will consume.
- `metadata`: Optional dictionary for custom metadata on the event.

**Returns:**

- A NetworkRequestEvent instance tracking this task.

**Raises:**

- `RuntimeError`: If the executor is not running.

**Example:**

```python
async def api_call():
    # Make API call using aiohttp or similar
    async with aiohttp.ClientSession() as session:
        async with session.get("https://api.example.com/data") as response:
            body = await response.json()
            return response.status, dict(response.headers), body

event = await executor.submit_task(
    api_call_coroutine=api_call,
    endpoint_url="https://api.example.com/data",
    method="GET",
    num_api_tokens_needed=1
)
```

##### start

```python
async def start() -> None
```

Start the executor and its internal worker queue.

**Raises:**

- `RuntimeError`: If the executor is already running.

**Example:**

```python
await executor.start()
```

##### stop

```python
async def stop(graceful: bool = True) -> None
```

Stop the executor.

**Parameters:**

- `graceful`: If True, waits for the queue to empty and workers to finish. If
  False, attempts a more immediate shutdown (cancels tasks).

**Example:**

```python
# Graceful shutdown (default)
await executor.stop()

# Immediate shutdown
await executor.stop(graceful=False)
```

#### Context Manager

The Executor class supports the async context manager protocol, which
automatically starts the executor when entering the context and stops it when
exiting.

```python
async with Executor(concurrency_limit=5) as executor:
    # Use executor here
    event = await executor.submit_task(...)
```

## Internal Components

The Executor uses several internal components from lionfuncs:

- `WorkQueue`: Manages the queue of API call tasks and worker coroutines.
- `CapacityLimiter`: Limits the number of concurrent API calls.
- `TokenBucketRateLimiter`: Implements the token bucket algorithm for rate
  limiting.
- `NetworkRequestEvent`: Tracks the lifecycle of API requests.

## Usage Example

```python
import asyncio
import aiohttp
from lionfuncs.network.executor import Executor
from lionfuncs.network.events import NetworkRequestEvent, RequestStatus

async def main():
    # Create an executor with custom settings
    async with Executor(
        queue_capacity=500,
        concurrency_limit=5,
        requests_rate=10.0,
        requests_period=1.0,
        api_tokens_rate=10000.0,
        api_tokens_period=60.0,
        num_workers=3
    ) as executor:
        # Define an API call coroutine
        async def fetch_data():
            async with aiohttp.ClientSession() as session:
                async with session.get("https://api.example.com/data") as response:
                    body = await response.json()
                    return response.status, dict(response.headers), body

        # Submit multiple tasks
        events = []
        for i in range(10):
            event = await executor.submit_task(
                api_call_coroutine=fetch_data,
                endpoint_url="https://api.example.com/data",
                method="GET",
                num_api_tokens_needed=5,
                metadata={"task_id": i}
            )
            events.append(event)
            print(f"Submitted task {i}, request_id: {event.request_id}")

        # Wait for all tasks to complete
        while any(event.status not in [RequestStatus.COMPLETED, RequestStatus.FAILED] for event in events):
            await asyncio.sleep(0.1)

        # Process results
        for i, event in enumerate(events):
            if event.status == RequestStatus.COMPLETED:
                print(f"Task {i} completed with status code: {event.response_status_code}")
            else:
                print(f"Task {i} failed: {event.error_type} - {event.error_message}")

asyncio.run(main())
```

## Rate Limiting Behavior

The Executor implements two levels of rate limiting:

1. **Request Rate Limiting**: Limits the number of requests per time period
   (e.g., 10 requests per second).
2. **API Token Rate Limiting**: Limits the consumption of API-specific tokens
   (e.g., 10,000 tokens per minute).

Both rate limiters use the token bucket algorithm, which allows for bursts of
traffic up to the bucket capacity while maintaining the average rate over time.
When a rate limit is reached, the executor will wait for tokens to become
available before proceeding with the API call.

## Error Handling

The Executor catches exceptions raised by the API call coroutines and records
them in the corresponding NetworkRequestEvent. The event's status is set to
FAILED, and the error details are stored in the event's error_type,
error_message, and error_details fields.

## Concurrency Control

The Executor uses a CapacityLimiter to control the number of concurrent API
calls. This ensures that the system doesn't overwhelm the API provider with too
many simultaneous requests.
