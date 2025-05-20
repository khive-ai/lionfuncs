---
title: "Technical Design Specification: Network Executor and iModel Refactor"
by: khive-architect
created: 2025-05-20
updated: 2025-05-20
version: 1.0
doc_type: TDS
output_subdir: tds
description: >
  Technical Design Specification for the new lionfuncs.network.executor.Executor class,
  the NetworkRequestEvent, and the refactoring of iModel to use the Executor.
date: 2025-05-20
author: "@khive-architect"
status: "Draft"
issue_url: "https://github.com/khive-ai/lionfuncs/issues/17"
research_report_url: ".khive/reports/rr/RR-17.md"
---

# Guidance

**Purpose**\
Lay out an **implementation-ready** blueprint for a new library component and
refactoring existing ones: data models, class structures, APIs, flows, error
handling, etc.

**When to Use**

- After the Research is done, to guide the Implementer.
- Before Implementation Plan or simultaneously with it.

**Best Practices**

- Keep the design as **complete** as possible so coders can proceed with minimal
  guesswork.
- Emphasize any performance or concurrency considerations.
- Use diagrams (Mermaid) for clarity.

---

# Technical Design Specification: Network Executor & iModel Refactor

## 1. Overview

### 1.1 Purpose

This document outlines the technical design for a new `Executor` class within
`lionfuncs.network` responsible for managing and rate-limiting API calls. It
also details a new `NetworkRequestEvent` for tracking request lifecycles and the
necessary refactoring of the existing `iModel` class to utilize this new
`Executor`.

### 1.2 Scope

**In Scope:**

- Design of the `lionfuncs.network.executor.Executor` class, including its
  integration with [`lionfuncs.WorkQueue`](src/lionfuncs/concurrency.py:341),
  [`lionfuncs.CapacityLimiter`](src/lionfuncs/concurrency.py:487), and two
  [`lionfuncs.TokenBucketRateLimiter`](src/lionfuncs/network/primitives.py:256)
  instances.
- Definition of method signatures for task submission, starting, and stopping
  the `Executor`.
- Specification of configuration parameters for the `Executor`.
- Design of a `NetworkRequestEvent` class (e.g., in
  [`src/lionfuncs/network/events.py`](src/lionfuncs/network/events.py)).
- Refactoring plan for the `iModel` class to use the new `Executor` and accept
  direct `EndpointConfig` or dictionary configuration.
- Interaction diagrams illustrating the API call flow through the `Executor`.
- Ensuring alignment with the `TokenBucketRateLimiter`'s gradual replenishment
  model.

**Out of Scope:**

- Implementation of specific API client logic beyond the `Executor`'s
  interaction points.
- Detailed design of retry mechanisms (though the `Executor` should be
  extensible for this).
- UI components or command-line interfaces for managing the `Executor`.

### 1.3 Background

This design is based on the requirements outlined in GitHub Issue #17
([`https://github.com/khive-ai/lionfuncs/issues/17`](https://github.com/khive-ai/lionfuncs/issues/17))
and the findings of the research report
[`RR-17.md`](.khive/reports/rr/RR-17.md). The primary goal is to create a
robust, configurable, and observable system for making rate-limited API calls
using existing `lionfuncs` primitives.

### 1.4 Design Goals

- **Robustness:** Ensure reliable execution of API calls with proper error
  handling and state management.
- **Configurability:** Allow flexible configuration of concurrency, rate limits
  (requests and API tokens), and queue capacity.
- **Observability:** Provide a mechanism (via `NetworkRequestEvent`) to track
  the lifecycle and status of each API call.
- **Reusability:** Design the `Executor` as a general-purpose component for
  various API interactions.
- **Integration:** Seamlessly integrate with existing `lionfuncs` concurrency
  and network primitives.
- **Maintainability:** Clear separation of concerns and well-defined interfaces.

### 1.5 Key Constraints

- Must utilize existing `lionfuncs` primitives:
  [`WorkQueue`](src/lionfuncs/concurrency.py:341),
  [`CapacityLimiter`](src/lionfuncs/concurrency.py:487),
  [`TokenBucketRateLimiter`](src/lionfuncs/network/primitives.py:256).
- The `TokenBucketRateLimiter`'s gradual replenishment model should be used.
- The solution must be asynchronous (`asyncio`).

## 2. Architecture

### 2.1 Component Diagram (`Executor` Internal)

```mermaid
graph TD
    subgraph Executor
        direction LR
        WQ[WorkQueue] -->|Tasks| Workers
        Workers -->|Acquire Slot| CL(CapacityLimiter)
        Workers -->|Acquire Request Token| RRL(TokenBucketRateLimiter <br> Requests/Interval)
        Workers -->|Acquire API Tokens| TRL(TokenBucketRateLimiter <br> API Tokens/Interval)
        Workers -->|Make API Call| HTTP_Client[HTTP Client <br> (e.g., aiohttp)]
        HTTP_Client -->|Response/Error| Workers
        Workers -->|Update Event| NRE(NetworkRequestEvent)
    end

    ExternalCaller -->|submit_task()| Executor
    Executor -->|event_updated| EventSubscribers
```

### 2.2 Dependencies

- **Internal `lionfuncs` Dependencies:**
  - [`lionfuncs.concurrency.WorkQueue`](src/lionfuncs/concurrency.py:341)
  - [`lionfuncs.concurrency.CapacityLimiter`](src/lionfuncs/concurrency.py:487)
  - [`lionfuncs.network.primitives.TokenBucketRateLimiter`](src/lionfuncs/network/primitives.py:256)
  - `asyncio` (Python standard library)
- **External Dependencies (for making HTTP calls, to be used by the task logic
  passed to Executor):**
  - Typically `aiohttp` or a similar asynchronous HTTP client library (this is
    not a direct dependency of the `Executor` itself, but of the callables it
    executes).

### 2.3 Data Flow / Interaction Diagram (Simplified API Call Task)

```mermaid
sequenceDiagram
    participant ClientCode as Client Code (e.g., iModel)
    participant Executor
    participant WorkQueue as WorkQueue (Internal)
    participant Worker as Worker (Internal)
    participant CapacityLimiter as CapacityLimiter (Internal)
    participant ReqRateLimiter as ReqRateLimiter (Internal)
    participant ApiTokenRateLimiter as ApiTokenRateLimiter (Internal)
    participant HttpClient as HTTP Client (Task Logic)
    participant NetworkRequestEvent as NetworkRequestEvent

    ClientCode->>+Executor: submit_task(api_call_coro, event_details)
    Executor->>WorkQueue: Enqueue task (api_call_coro, event)
    Executor-->>-ClientCode: Returns NetworkRequestEvent (initial state: QUEUED)

    WorkQueue->>+Worker: Dequeue task
    Worker->>+NetworkRequestEvent: Update status (e.g., PROCESSING)
    Worker->>+CapacityLimiter: Acquire slot
    CapacityLimiter-->>-Worker: Slot acquired
    Worker->>+ReqRateLimiter: acquire(tokens=1)
    ReqRateLimiter-->>-Worker: Wait time (if any), token acquired
    alt API tokens required
        Worker->>+ApiTokenRateLimiter: acquire(tokens=N)
        ApiTokenRateLimiter-->>-Worker: Wait time (if any), tokens acquired
    end
    Worker->>+HttpClient: Execute api_call_coro()
    HttpClient-->>-Worker: Response / Error
    Worker->>-CapacityLimiter: Release slot (implicitly via context manager)
    Worker->>+NetworkRequestEvent: Update status (COMPLETED/FAILED), result/error
    NetworkRequestEvent-->>-Worker:
    Worker-->>-WorkQueue: Task done
```

## 3. Class Structures & Internal Interfaces

This section details the Python class structures.

### 3.1 `lionfuncs.network.executor.Executor`

**File:**
[`src/lionfuncs/network/executor.py`](src/lionfuncs/network/executor.py) (New
file)

```python
import asyncio
from typing import Callable, Coroutine, Any, Optional, Dict
import uuid # For generating request_id for events

from lionfuncs.concurrency import WorkQueue, CapacityLimiter
from lionfuncs.network.primitives import TokenBucketRateLimiter
from lionfuncs.network.events import NetworkRequestEvent, RequestStatus # Assuming events.py is created

class Executor:
    def __init__(
        self,
        queue_capacity: int = 1000,
        concurrency_limit: int = 10,
        requests_rate: float = 10,  # e.g., 10 requests
        requests_period: float = 1,  # e.g., per 1 second
        requests_bucket_capacity: Optional[float] = None, # Defaults to rate if None
        api_tokens_rate: Optional[float] = None, # e.g., 10000 tokens
        api_tokens_period: float = 60, # e.g., per 60 seconds
        api_tokens_bucket_capacity: Optional[float] = None, # Defaults to rate if None
        num_workers: int = 5 # Number of workers for the WorkQueue
    ):
        """
        Initializes the Executor.

        Args:
            queue_capacity: Max capacity of the internal task queue.
            concurrency_limit: Max number of concurrent API calls.
            requests_rate: Max requests for the requests_rate_limiter.
            requests_period: Period in seconds for requests_rate.
            requests_bucket_capacity: Max capacity of the request token bucket.
                                      Defaults to requests_rate if None.
            api_tokens_rate: Max API tokens for the api_tokens_rate_limiter.
                             If None, this limiter is disabled.
            api_tokens_period: Period in seconds for api_tokens_rate.
            api_tokens_bucket_capacity: Max capacity of the API token bucket.
                                        Defaults to api_tokens_rate if None.
            num_workers: Number of worker coroutines to process the queue.
        """
        self.work_queue = WorkQueue(maxsize=queue_capacity, num_workers=num_workers)
        self.capacity_limiter = CapacityLimiter(limit=concurrency_limit)

        self.requests_rate_limiter = TokenBucketRateLimiter(
            rate=requests_rate,
            period=requests_period,
            bucket_capacity=requests_bucket_capacity
        )

        self.api_tokens_rate_limiter: Optional[TokenBucketRateLimiter] = None
        if api_tokens_rate is not None:
            self.api_tokens_rate_limiter = TokenBucketRateLimiter(
                rate=api_tokens_rate,
                period=api_tokens_period,
                bucket_capacity=api_tokens_bucket_capacity
            )

        self._is_running = False

    async def _worker(self, task_data: Dict[str, Any]):
        """
        Internal worker coroutine that processes a single task from the queue.
        """
        api_coro: Callable[[], Coroutine[Any, Any, Any]] = task_data["api_coro"]
        event: NetworkRequestEvent = task_data["event"]

        event.update_status(RequestStatus.PROCESSING)
        try:
            async with self.capacity_limiter:
                event.add_log("Acquired concurrency slot.")
                # Acquire request rate limit token
                wait_time_req = await self.requests_rate_limiter.acquire(tokens=1)
                if wait_time_req > 0:
                    event.add_log(f"Waiting {wait_time_req:.2f}s for request rate limit.")
                    await asyncio.sleep(wait_time_req)
                event.add_log("Acquired request rate limit token.")

                # Acquire API token rate limit tokens (if applicable)
                num_api_tokens_needed = event.num_api_tokens_needed
                if self.api_tokens_rate_limiter and num_api_tokens_needed > 0:
                    wait_time_api_tokens = await self.api_tokens_rate_limiter.acquire(tokens=num_api_tokens_needed)
                    if wait_time_api_tokens > 0:
                        event.add_log(f"Waiting {wait_time_api_tokens:.2f}s for API token rate limit ({num_api_tokens_needed} tokens).")
                        await asyncio.sleep(wait_time_api_tokens)
                    event.add_log(f"Acquired API token rate limit ({num_api_tokens_needed} tokens).")

                event.update_status(RequestStatus.CALLING)
                # The api_coro is expected to return a tuple: (status_code, headers, body)
                # or raise an exception.
                response_status_code, response_headers, response_body = await api_coro()
                event.set_result(response_status_code, response_headers, response_body)
                # Status is set to COMPLETED by set_result
        except Exception as e:
            event.set_error(e)
            # Status is set to FAILED by set_error
        finally:
            # Ensure event completion is signaled if using asyncio.Event
            # if hasattr(event, 'completion_event'):
            #     event.completion_event.set()
            pass


    async def submit_task(
        self,
        api_call_coroutine: Callable[[], Coroutine[Any, Any, Any]], # Should return (status_code, headers, body)
        endpoint_url: Optional[str] = None,
        method: Optional[str] = None,
        headers: Optional[Dict[str, Any]] = None,
        payload: Optional[Any] = None,
        num_api_tokens_needed: int = 0,
        metadata: Optional[Dict[str, Any]] = None
    ) -> NetworkRequestEvent:
        """
        Submits a new API call task to the executor.

        Args:
            api_call_coroutine: A callable that returns a coroutine.
                                The coroutine should perform the API call and return a tuple
                                (status_code: int, headers: Dict, body: Any) or raise an exception.
            endpoint_url: URL of the API endpoint.
            method: HTTP method (e.g., "GET", "POST").
            headers: Request headers.
            payload: Request payload/body.
            num_api_tokens_needed: Number of API-specific tokens this call will consume.
            metadata: Optional dictionary for custom metadata on the event.

        Returns:
            A NetworkRequestEvent instance tracking this task.
        """
        if not self._is_running:
            raise RuntimeError("Executor is not running. Call start() first.")

        event = NetworkRequestEvent(
            request_id=str(uuid.uuid4()),
            endpoint_url=endpoint_url,
            method=method,
            headers=headers,
            payload=payload,
            num_api_tokens_needed=num_api_tokens_needed,
            metadata=metadata or {}
        )
        event.update_status(RequestStatus.QUEUED)

        task_data = {
            "api_coro": api_call_coroutine,
            "event": event,
        }
        await self.work_queue.put(task_data)
        return event

    async def start(self):
        """Starts the executor and its internal worker queue."""
        if self._is_running:
            return
        self._is_running = True
        await self.work_queue.start(worker_coro_func=self._worker)

    async def stop(self, graceful: bool = True):
        """
        Stops the executor.

        Args:
            graceful: If True, waits for the queue to empty and workers to finish.
                      If False, attempts a more immediate shutdown (cancels tasks).
        """
        if not self._is_running:
            return
        self._is_running = False
        await self.work_queue.stop(graceful=graceful)

    async def __aenter__(self):
        await self.start()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.stop()
```

### 3.2 `lionfuncs.network.events.NetworkRequestEvent`

**File:** [`src/lionfuncs/network/events.py`](src/lionfuncs/network/events.py)
(New file)

```python
import asyncio
from enum import Enum
from typing import Any, Optional, Dict, List
from dataclasses import dataclass, field
import datetime
import traceback # For detailed error logging

class RequestStatus(str, Enum):
    PENDING = "PENDING"    # Initial state before queueing (event created, not yet submitted)
    QUEUED = "QUEUED"      # Task is in the WorkQueue
    PROCESSING = "PROCESSING" # Task picked by worker, waiting for limits/capacity
    CALLING = "CALLING"    # API call is in flight
    COMPLETED = "COMPLETED"  # API call finished successfully
    FAILED = "FAILED"      # API call failed
    CANCELLED = "CANCELLED"  # Task was cancelled

@dataclass
class NetworkRequestEvent:
    request_id: str # e.g., uuid, should be set by Executor on creation
    created_at: datetime.datetime = field(default_factory=datetime.datetime.utcnow)
    updated_at: datetime.datetime = field(default_factory=datetime.datetime.utcnow)
    status: RequestStatus = RequestStatus.PENDING

    # Request details
    endpoint_url: Optional[str] = None
    method: Optional[str] = None
    headers: Optional[Dict[str, Any]] = None
    payload: Optional[Any] = None # Or request_body

    # Execution details
    num_api_tokens_needed: int = 0 # For API token rate limiter

    # Response details
    response_status_code: Optional[int] = None
    response_headers: Optional[Dict[str, Any]] = None
    response_body: Optional[Any] = None

    # Error details
    error_type: Optional[str] = None
    error_message: Optional[str] = None
    error_details: Optional[str] = None # Store traceback string

    # Timing
    queued_at: Optional[datetime.datetime] = None
    processing_started_at: Optional[datetime.datetime] = None
    call_started_at: Optional[datetime.datetime] = None
    completed_at: Optional[datetime.datetime] = None # or failed_at / cancelled_at

    # Logs/Metadata
    logs: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    # Optional asyncio.Event for subscribers to wait on completion
    # completion_event: asyncio.Event = field(default_factory=asyncio.Event, repr=False, init=False)

    def __post_init__(self):
        # self.completion_event = asyncio.Event() # Initialize if used
        pass

    def _update_timestamp(self):
        self.updated_at = datetime.datetime.utcnow()

    def update_status(self, new_status: RequestStatus):
        old_status = self.status
        self.status = new_status
        now = datetime.datetime.utcnow()

        if old_status != new_status: # Log status change
            self.add_log(f"Status changed from {old_status.value} to {new_status.value}")

        if new_status == RequestStatus.QUEUED and not self.queued_at:
            self.queued_at = now
        elif new_status == RequestStatus.PROCESSING and not self.processing_started_at:
            self.processing_started_at = now
        elif new_status == RequestStatus.CALLING and not self.call_started_at:
            self.call_started_at = now
        elif new_status in [RequestStatus.COMPLETED, RequestStatus.FAILED, RequestStatus.CANCELLED] and not self.completed_at:
            self.completed_at = now
            # if hasattr(self, 'completion_event'):
            #     self.completion_event.set()
        self._update_timestamp()

    def set_result(self, status_code: int, headers: Optional[Dict], body: Optional[Any]):
        self.response_status_code = status_code
        self.response_headers = headers
        self.response_body = body
        self.add_log(f"Call completed with status code: {status_code}")
        self.update_status(RequestStatus.COMPLETED)

    def set_error(self, exception: Exception):
        self.error_type = type(exception).__name__
        self.error_message = str(exception)
        self.error_details = traceback.format_exc()
        self.add_log(f"Call failed: {self.error_type} - {self.error_message}")
        self.update_status(RequestStatus.FAILED)

    def add_log(self, message: str):
        self.logs.append(f"{datetime.datetime.utcnow().isoformat()} - {message}")
        self._update_timestamp()
```

## 4. `iModel` Refactoring

The `iModel` class (assuming it's a class responsible for interacting with a
specific API model like OpenAI's models) will be refactored as follows:

1. **Dependency Injection of `Executor`:**
   - `iModel` will accept an instance of the new
     `lionfuncs.network.executor.Executor` in its constructor.
   - This `Executor` instance will be used for all its underlying API calls.

2. **Configuration Handling:**
   - The `iModel` constructor will accept an `EndpointConfig` object (if such a
     class exists or is to be created) or a dictionary directly for its
     configuration.
   - The `match_endpoint` logic, which previously might have selected or
     configured a `RateLimitedAPIExecutor` internally based on endpoint details,
     will be removed. The `Executor` passed to `iModel` will already be
     configured with the appropriate rate limits for the intended service(s).
   - If `iModel` needs to make calls that consume API-specific tokens (e.g.,
     OpenAI tokens), it will pass `num_api_tokens_needed` when submitting tasks
     to the `Executor`.

3. **API Call Submission:**
   - When `iModel` needs to make an API call (e.g., `acompletion`), it will:
     1. Prepare the API call coroutine (e.g., a method that uses `aiohttp` to
        make the actual request and returns `(status_code, headers, body)` or
        raises an error).
     2. Call
        `executor.submit_task(api_call_coroutine, endpoint_url=..., method=..., ..., num_api_tokens_needed=...)`.
     3. It will receive a `NetworkRequestEvent` object, which it can return or
        use to track the call's progress (e.g.,
        `await event.completion_event.wait()` if implemented).

4. **Location of `iModel`:**
   - **Recommendation:** The refactoring primarily concerns `iModel`'s internal
     logic to use the `Executor`. Its specific file location
     (`lionfuncs.network.imodel.py` vs. external) is a secondary concern for
     this TDS but should be decided during implementation. If it's a generic
     model interaction pattern, `lionfuncs.network.imodel` is suitable. If
     highly service-specific, it might live elsewhere.

**Example (Conceptual `iModel` refactoring):**

```python
# Conceptual iModel
# from lionfuncs.network.executor import Executor
# from lionfuncs.network.events import NetworkRequestEvent, RequestStatus
# import aiohttp # Example HTTP client

class iModel:
    def __init__(self, executor: Executor, model_endpoint_config: Dict[str, Any]):
        self.executor = executor
        self.config = model_endpoint_config # e.g., {'base_url': '...', 'api_key': '...'}
        self.http_session: Optional[aiohttp.ClientSession] = None

    async def _get_session(self) -> aiohttp.ClientSession:
        if self.http_session is None or self.http_session.closed:
            self.http_session = aiohttp.ClientSession()
        return self.http_session

    async def close_session(self):
        if self.http_session and not self.http_session.closed:
            await self.http_session.close()

    async def _make_actual_api_call(self, method: str, url: str, headers: Dict, json_payload: Optional[Dict]) -> tuple[int, Dict, Any]:
        session = await self._get_session()
        async with session.request(method, url, headers=headers, json=json_payload) as response:
            response_body = await response.json() # Or .text() depending on content type
            return response.status, dict(response.headers), response_body

    async def acompletion(self, prompt: str, num_tokens_to_consume: int = 100) -> NetworkRequestEvent:
        endpoint_url = f"{self.config['base_url']}/completions" # Example
        method = "POST"
        payload = {"prompt": prompt, "max_tokens": 150} # Example
        headers = {"Authorization": f"Bearer {self.config['api_key']}"} # Example

        # Prepare the coroutine for the actual API call
        api_call_coro = lambda: self._make_actual_api_call(method, endpoint_url, headers, payload)

        request_event = await self.executor.submit_task(
            api_call_coroutine=api_call_coro,
            endpoint_url=endpoint_url,
            method=method,
            headers=headers,
            payload=payload,
            num_api_tokens_needed=num_tokens_to_consume,
            metadata={"model_name": self.config.get("model_name", "unknown")}
        )

        return request_event

    # Ensure to provide a way to close the session, e.g., via context manager for iModel
    async def __aenter__(self):
        await self._get_session()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close_session()
```

## 5. Behavior

### 5.1 Core Workflows

(Refer to the Mermaid sequence diagram in Section 2.3 "Data Flow / Interaction
Diagram")

The core workflow involves:

1. Task submission to the `Executor` via `submit_task`, which creates a
   `NetworkRequestEvent`.
2. Task (including the event) queuing in `WorkQueue`.
3. Worker dequeues task. `NetworkRequestEvent` status updated to `PROCESSING`.
4. Worker acquires resources, logging waits to the event:
   - `CapacityLimiter` slot.
   - `TokenBucketRateLimiter` token for requests/interval.
   - `TokenBucketRateLimiter` tokens for API tokens/interval (if applicable).
5. Worker executes the API call coroutine. `NetworkRequestEvent` status updated
   to `CALLING`.
6. API call coroutine returns `(status_code, headers, body)` or raises an
   exception.
7. Worker updates `NetworkRequestEvent` with status (`COMPLETED`/`FAILED`),
   result, or error.
8. `CapacityLimiter` slot is released.

### 5.2 Error Handling

- Errors during API call execution (within the user-provided coroutine) are
  caught by the `Executor`'s `_worker`.
- These errors are recorded in the `NetworkRequestEvent` (e.g., `status=FAILED`,
  `error_type`, `error_message`, `error_details`).
- The `Executor` itself can raise errors for invalid configuration or
  operational issues (e.g., `RuntimeError` if `submit_task` is called when not
  started).
- `WorkQueue` and other primitives might have their own exceptions, though these
  are generally handled internally by those primitives or by the `Executor`'s
  use of them.
- Cancellation: If `Executor.stop(graceful=False)` is called, tasks in
  `WorkQueue` might be cancelled. The `NetworkRequestEvent` has a `CANCELLED`
  status, though explicit cancellation handling in the worker might be needed if
  tasks are long-running before the actual API call.

### 5.3 Security Considerations

- The `Executor` itself does not handle authentication or authorization for API
  calls; this is the responsibility of the submitted API call coroutines (e.g.,
  including API keys in headers, as shown in the `iModel` example).
- Configuration parameters (like rate limits) should be validated by the
  `Executor`'s `__init__` to prevent misconfiguration (e.g., negative rates,
  zero periods).

## 6. External Interactions

The `Executor` primarily interacts with internal `lionfuncs` primitives. The
tasks it executes (API call coroutines) will interact with external API
services.

## 7. Performance Considerations

### 7.1 Expected Load

The `Executor` is designed to handle a configurable load, determined by
`queue_capacity`, `concurrency_limit`, and rate limit settings.

### 7.2 Scalability Approach

Scalability is managed by:

- Adjusting `num_workers` in `WorkQueue`.
- Adjusting `concurrency_limit`.
- Configuring appropriate rate limits to match external API provider limits.

### 7.3 Optimizations

- Leveraging efficient `asyncio` primitives.
- `TokenBucketRateLimiter`'s gradual replenishment avoids thundering herd
  problems.
- Using `aiohttp.ClientSession` (or similar) effectively in the calling code
  (e.g., `iModel`) can improve performance by reusing connections.

### 7.4 Caching Strategy

N/A for the `Executor` itself. Caching would be implemented at a higher level or
by the API call logic submitted to the `Executor`.

## 8. Observability

### 8.1 Logging

- The `Executor` can have internal logging for its state changes (start, stop,
  worker activity, errors).
- The `NetworkRequestEvent.logs` field provides detailed per-request diagnostic
  logging.

### 8.2 Metrics

The `Executor` could expose metrics such as:

- Current queue size (`self.work_queue.qsize()`).
- Number of active tasks/concurrency slots used
  (`self.capacity_limiter.count()`).
- Number of available tokens in rate limiters (requires `TokenBucketRateLimiter`
  to expose `available_tokens()` or similar).
- Counts of events by status (e.g., `QUEUED`, `PROCESSING`, `COMPLETED`,
  `FAILED`), tracked externally by processing emitted events or internally by
  the `Executor`.

### 8.3 Tracing

While not implementing distributed tracing, the `NetworkRequestEvent` timestamps
(`created_at`, `queued_at`, `processing_started_at`, `call_started_at`,
`completed_at`) allow for calculating durations of different stages of a
request's lifecycle.

## 9. Testing Strategy

### 9.1 Unit Testing

- Test `Executor.__init__` with various valid and invalid configurations.
- Test `Executor.submit_task` behavior (event creation, queueing).
- Test `Executor.start` and `Executor.stop` (graceful and non-graceful).
- Test `Executor._worker` logic extensively:
  - Successful calls.
  - Calls requiring waits for request rate limits.
  - Calls requiring waits for API token rate limits.
  - Calls requiring waits for both.
  - Calls that raise exceptions.
- Test `NetworkRequestEvent` class:
  - Initialization and default values.
  - `update_status` and timestamp updates.
  - `set_result` and `set_error`.
  - `add_log`.

### 9.2 Integration Testing

- Test `Executor` with actual instances of `WorkQueue`, `CapacityLimiter`, and
  `TokenBucketRateLimiter`.
- Test end-to-end flow with mock API call coroutines that simulate success,
  delays, and failures.
- Verify that rate limiting (both request and API token) and concurrency
  limiting behaviors are correctly enforced.
- Test `async with Executor():` context manager usage.

### 9.3 Performance Testing

- Measure throughput (tasks processed per second) under different configurations
  and simulated loads.
- Measure latency of task processing.
- Identify potential bottlenecks.

## 10. Deployment and Configuration

### 10.1 Deployment Requirements

The `Executor` is a Python class, intended to be part of the `lionfuncs`
library. No special deployment procedures beyond including it in the library.

### 10.2 Configuration Parameters

As defined in the `Executor.__init__` method signature and documented in Section
3.1. Example JSON representation:

```json
{
  "queue_capacity": 1000,
  "concurrency_limit": 10,
  "requests_rate": 10.0,
  "requests_period": 1.0,
  "requests_bucket_capacity": null, // Defaults to requests_rate
  "api_tokens_rate": 10000.0, // Example: 10k tokens
  "api_tokens_period": 60.0, // per minute
  "api_tokens_bucket_capacity": null, // Defaults to api_tokens_rate
  "num_workers": 5
}
```

**Note on `TokenBucketRateLimiter` usage:** The design correctly uses the
gradual replenishment model inherent to
[`lionfuncs.TokenBucketRateLimiter`](src/lionfuncs/network/primitives.py:256),
as recommended in [`RR-17.md`](.khive/reports/rr/RR-17.md) (Section 3.3). This
ensures continuous token availability based on elapsed time rather than periodic
full resets.

## 11. Risks and Mitigations

- **Risk:** Complexity in managing multiple asynchronous components and ensuring
  correct state transitions within the `Executor` and `NetworkRequestEvent`.
  - **Mitigation:** Thorough unit and integration testing focusing on state
    changes and interactions. Clear logging within the `Executor` and
    `NetworkRequestEvent` to aid debugging.
- **Risk:** Potential for deadlocks or resource starvation if concurrency
  primitives are misused.
  - **Mitigation:** Rely on the tested behavior of `lionfuncs`'s `WorkQueue`,
    `CapacityLimiter`, and `TokenBucketRateLimiter`. Careful review and testing
    of the `_worker` logic, especially around acquiring and releasing resources
    (though `CapacityLimiter` uses context management).
- **Risk:** Misconfiguration of rate limits (e.g., rates, periods, bucket
  capacities) leading to API errors from external services or underutilization
  of available quotas.
  - **Mitigation:** Clear documentation for all configuration parameters.
    Implement validation for sensible ranges (e.g., non-negative rates, positive
    periods) in `Executor.__init__`. Provide examples of common configurations.
- **Risk:** Unhandled exceptions in user-provided API call coroutines could
  break worker tasks if not caught properly by the `_worker` method.
  - **Mitigation:** The `_worker` method includes a broad
    `try...except Exception` block to catch errors from `api_coro` and update
    the `NetworkRequestEvent` accordingly. Ensure this is robust.
- **Risk:** Resource leakage if `Executor.start()` and `Executor.stop()` are not
  managed correctly by the consuming code (e.g., `WorkQueue` workers not shut
  down).
  - **Mitigation:** Provide `async with` context manager support (`__aenter__`,
    `__aexit__`) for the `Executor` to simplify resource management for users.
    Ensure `stop()` correctly shuts down the `WorkQueue`.
- **Risk:** `NetworkRequestEvent` objects could become large if response bodies
  or extensive logs are stored directly.
  - **Mitigation:** Advise users on managing the data stored in events. Consider
    options for truncating large response bodies or providing summaries if this
    becomes an issue. For now, the design assumes full storage.

## 12. Open Questions

- **`NetworkRequestEvent` `completion_event`:** Should `NetworkRequestEvent`
  include an `asyncio.Event` for external subscribers to
  `await event.completion_event.wait()`?
  - **Decision:** For v1, defer this. Callers can poll the status or implement
    their own waiting mechanism if needed. Can be added later if a strong use
    case emerges.
- **`Executor` Event Bus/Callbacks:** Should the `Executor` provide a direct way
  to subscribe to `NetworkRequestEvent` updates (e.g., an event bus or callback
  mechanism for when an event reaches a terminal state)?
  - **Decision:** Defer for v1. The current model returns the event object upon
    submission, which the caller owns and can monitor.
- **Cancellation Propagation:** How deeply should task cancellation (e.g., if
  `Executor.stop(graceful=False)` is called or an `asyncio.Task` wrapping
  `submit_task` is cancelled) propagate into the `api_call_coroutine`?
  - **Consideration:** Standard `asyncio` cancellation will propagate. The
    `api_call_coroutine` should be written to handle `asyncio.CancelledError`
    gracefully if it performs long operations or needs cleanup. The `_worker`
    can catch `CancelledError` and update the event to `CANCELLED`.

## 13. Appendices

### Appendix A: Alternative Designs

N/A - The current design closely follows the recommendations from
[`RR-17.md`](.khive/reports/rr/RR-17.md) which leverages existing `lionfuncs`
primitives and aligns with common patterns for such executors.

### Appendix B: Research References

- GitHub Issue #17:
  [`https://github.com/khive-ai/lionfuncs/issues/17`](https://github.com/khive-ai/lionfuncs/issues/17)
- Research Report [`RR-17.md`](.khive/reports/rr/RR-17.md)
- [`lionfuncs.concurrency.WorkQueue`](src/lionfuncs/concurrency.py:341)
- [`lionfuncs.concurrency.CapacityLimiter`](src/lionfuncs/concurrency.py:487)
- [`lionfuncs.network.primitives.TokenBucketRateLimiter`](src/lionfuncs/network/primitives.py:256)
