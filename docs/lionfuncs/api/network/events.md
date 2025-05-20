---
title: "lionfuncs.network.events"
---

# lionfuncs.network.events

The `events` module provides classes for tracking the lifecycle of API requests,
including status, timing, and result information.

## Classes

### RequestStatus

```python
class RequestStatus(str, Enum)
```

An enumeration of possible states for a network request.

#### Values

| Value        | Description                                                      |
| ------------ | ---------------------------------------------------------------- |
| `PENDING`    | Initial state before queueing (event created, not yet submitted) |
| `QUEUED`     | Task is in the WorkQueue                                         |
| `PROCESSING` | Task picked by worker, waiting for limits/capacity               |
| `CALLING`    | API call is in flight                                            |
| `COMPLETED`  | API call finished successfully                                   |
| `FAILED`     | API call failed                                                  |
| `CANCELLED`  | Task was cancelled                                               |

### NetworkRequestEvent

```python
@dataclass
class NetworkRequestEvent
```

Event class for tracking the lifecycle of a network request. This class
maintains the state, timing, and result information for an API request as it
progresses through the execution pipeline.

#### Attributes

| Name                    | Type                          | Description                                          |
| ----------------------- | ----------------------------- | ---------------------------------------------------- |
| `request_id`            | `str`                         | Unique identifier for the request (e.g., UUID)       |
| `created_at`            | `datetime.datetime`           | When the event was created                           |
| `updated_at`            | `datetime.datetime`           | When the event was last updated                      |
| `status`                | `RequestStatus`               | Current status of the request                        |
| `endpoint_url`          | `Optional[str]`               | URL of the API endpoint                              |
| `method`                | `Optional[str]`               | HTTP method (e.g., "GET", "POST")                    |
| `headers`               | `Optional[dict[str, Any]]`    | Request headers                                      |
| `payload`               | `Optional[Any]`               | Request payload/body                                 |
| `num_api_tokens_needed` | `int`                         | Number of API-specific tokens this call will consume |
| `response_status_code`  | `Optional[int]`               | HTTP status code of the response                     |
| `response_headers`      | `Optional[dict[str, Any]]`    | Response headers                                     |
| `response_body`         | `Optional[Any]`               | Response body                                        |
| `error_type`            | `Optional[str]`               | Type of error if the request failed                  |
| `error_message`         | `Optional[str]`               | Error message if the request failed                  |
| `error_details`         | `Optional[str]`               | Detailed error information (e.g., traceback)         |
| `queued_at`             | `Optional[datetime.datetime]` | When the request was queued                          |
| `processing_started_at` | `Optional[datetime.datetime]` | When processing started                              |
| `call_started_at`       | `Optional[datetime.datetime]` | When the API call started                            |
| `completed_at`          | `Optional[datetime.datetime]` | When the request completed (or failed/cancelled)     |
| `logs`                  | `list[str]`                   | Log messages for the request                         |
| `metadata`              | `dict[str, Any]`              | Custom metadata for the request                      |

#### Methods

##### update_status

```python
def update_status(self, new_status: RequestStatus) -> None
```

Update the status of the request and record the timestamp.

**Parameters:**

- `new_status`: The new status to set.

**Example:**

```python
event.update_status(RequestStatus.PROCESSING)
```

##### set_result

```python
def set_result(self, status_code: int, headers: Optional[dict], body: Optional[Any]) -> None
```

Set the result of the request and update status to COMPLETED.

**Parameters:**

- `status_code`: HTTP status code of the response.
- `headers`: Response headers.
- `body`: Response body.

**Example:**

```python
event.set_result(200, {"Content-Type": "application/json"}, {"success": True})
```

##### set_error

```python
def set_error(self, exception: Exception) -> None
```

Set error information for the request and update status to FAILED.

**Parameters:**

- `exception`: The exception that occurred.

**Example:**

```python
try:
    # API call
except Exception as e:
    event.set_error(e)
```

##### add_log

```python
def add_log(self, message: str) -> None
```

Add a log message to the request's log.

**Parameters:**

- `message`: The message to add.

**Example:**

```python
event.add_log("Waiting for rate limit token")
```

## Usage Example

```python
import asyncio
from lionfuncs.network.events import NetworkRequestEvent, RequestStatus
from lionfuncs.network.executor import Executor

async def main():
    # Create an executor
    async with Executor(
        concurrency_limit=5,
        requests_rate=10,
        requests_period=1.0
    ) as executor:
        # Define an API call coroutine
        async def api_call():
            # Simulate API call
            await asyncio.sleep(0.5)
            return 200, {"Content-Type": "application/json"}, {"data": "example"}

        # Submit the task to the executor
        event = await executor.submit_task(
            api_call_coroutine=api_call,
            endpoint_url="https://api.example.com/data",
            method="GET",
            num_api_tokens_needed=1
        )

        # Wait for the task to complete
        while event.status not in [RequestStatus.COMPLETED, RequestStatus.FAILED]:
            print(f"Current status: {event.status}")
            await asyncio.sleep(0.1)

        # Check the result
        if event.status == RequestStatus.COMPLETED:
            print(f"Success! Status code: {event.response_status_code}")
            print(f"Response body: {event.response_body}")
        else:
            print(f"Failed: {event.error_type} - {event.error_message}")

        # Print the logs
        print("\nRequest logs:")
        for log in event.logs:
            print(f"  {log}")

asyncio.run(main())
```
