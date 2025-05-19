---
title: "lionfuncs.concurrency"
---

# lionfuncs.concurrency

The `concurrency` module provides concurrency primitives and utilities for
asynchronous programming, including bounded queues and wrappers around `anyio`
primitives.

## Classes

### QueueStatus

```python
class QueueStatus(str, Enum)
```

Enum for possible states of a queue.

#### Values

- `IDLE`: Queue is idle, not processing.
- `PROCESSING`: Queue is actively processing.
- `STOPPING`: Queue is in the process of stopping.
- `STOPPED`: Queue has stopped.

#### Example

```python
from lionfuncs.concurrency import QueueStatus

# Check if a queue's status is PROCESSING
if queue.status == QueueStatus.PROCESSING:
    print("Queue is processing")
```

### QueueConfig

```python
class QueueConfig(BaseModel)
```

Configuration options for work queues.

#### Attributes

- **queue_capacity** (`int`): Maximum queue size. Default: `100`.
- **capacity_refresh_time** (`float`): Time in seconds between capacity
  refreshes. Default: `1.0`.
- **concurrency_limit** (`int | None`): Maximum number of concurrent workers.
  Default: `None`.

#### Validation

- `queue_capacity` must be at least 1.
- `capacity_refresh_time` must be positive.
- `concurrency_limit` must be at least 1 if provided.

#### Example

```python
from lionfuncs.concurrency import QueueConfig

# Create a queue configuration
config = QueueConfig(
    queue_capacity=200,
    capacity_refresh_time=0.5,
    concurrency_limit=10
)
print(f"Queue capacity: {config.queue_capacity}")
```

### BoundedQueue

```python
class BoundedQueue(Generic[T])
```

Bounded async queue with backpressure support.

This implementation wraps `asyncio.Queue` with additional functionality for
worker management, backpressure, and lifecycle control.

#### Constructor

```python
def __init__(
    self,
    maxsize: int = 100,
    timeout: float = 0.1,
    logger: logging.Logger | None = None,
)
```

- **maxsize** (`int`): Maximum queue size (must be > 0). Default: `100`.
- **timeout** (`float`): Timeout for queue operations in seconds. Default:
  `0.1`.
- **logger** (`logging.Logger | None`): Optional logger. Default: `None`.

#### Properties

- **status** (`QueueStatus`): Get the current queue status.
- **metrics** (`dict[str, int]`): Get queue metrics (enqueued, processed,
  errors, backpressure_events).
- **size** (`int`): Get the current queue size.
- **is_full** (`bool`): Check if the queue is full.
- **is_empty** (`bool`): Check if the queue is empty.
- **worker_count** (`int`): Get the current number of active workers.

#### Methods

##### put

```python
async def put(self, item: T, timeout: float | None = None) -> bool
```

Add an item to the queue with backpressure.

- **item** (`T`): The item to enqueue.
- **timeout** (`float | None`): Operation timeout (overrides default). Default:
  `None`.
- **Returns** (`bool`): True if the item was enqueued, False if backpressure was
  applied.
- **Raises** (`QueueStateError`): If the queue is not in PROCESSING state.

##### get

```python
async def get(self) -> T
```

Get an item from the queue.

- **Returns** (`T`): The next item from the queue.
- **Raises** (`QueueStateError`): If the queue is not in PROCESSING state.

##### task_done

```python
def task_done(self) -> None
```

Mark a task as done.

##### join

```python
async def join(self) -> None
```

Wait for all queue items to be processed.

##### start

```python
async def start(self) -> None
```

Start the queue for processing.

##### stop

```python
async def stop(self, timeout: float | None = None) -> None
```

Stop the queue and all worker tasks.

- **timeout** (`float | None`): Maximum time to wait for pending tasks. Default:
  `None`.

##### start_workers

```python
async def start_workers(
    self,
    worker_func: Callable[[T], Awaitable[Any]],
    num_workers: int,
    error_handler: Callable[[Exception, T], Awaitable[None]] | None = None,
) -> None
```

Start worker tasks to process queue items.

- **worker_func** (`Callable[[T], Awaitable[Any]]`): Async function that
  processes each queue item.
- **num_workers** (`int`): Number of worker tasks to start.
- **error_handler** (`Callable[[Exception, T], Awaitable[None]] | None`):
  Optional async function to handle worker errors. Default: `None`.
- **Raises** (`ValueError`): If num_workers is less than 1.

#### Context Manager

`BoundedQueue` implements the async context manager protocol (`__aenter__` and
`__aexit__`), allowing it to be used with `async with`:

```python
async with BoundedQueue(maxsize=10) as queue:
    # Queue is started automatically
    await queue.put(item)
    # Queue is stopped automatically when exiting the context
```

#### Example

```python
import asyncio
from lionfuncs.concurrency import BoundedQueue
from lionfuncs.errors import QueueStateError

async def process_item(item):
    print(f"Processing {item}")
    await asyncio.sleep(0.1)
    return item * 2

async def handle_error(error, item):
    print(f"Error processing {item}: {error}")

async def main():
    # Create a bounded queue
    queue = BoundedQueue(maxsize=5)

    # Start the queue
    await queue.start()

    # Start workers
    await queue.start_workers(
        worker_func=process_item,
        num_workers=3,
        error_handler=handle_error
    )

    # Add items to the queue
    for i in range(10):
        success = await queue.put(i)
        print(f"Item {i} enqueued: {success}")

    # Wait for all items to be processed
    await queue.join()

    # Get metrics
    print(f"Queue metrics: {queue.metrics}")

    # Stop the queue
    await queue.stop()

asyncio.run(main())
```

### WorkQueue

```python
class WorkQueue(Generic[T])
```

High-level wrapper around BoundedQueue with additional functionality.

#### Constructor

```python
def __init__(
    self,
    maxsize: int = 100,
    timeout: float = 0.1,
    concurrency_limit: int | None = None,
    logger: logging.Logger | None = None,
)
```

- **maxsize** (`int`): Maximum queue size. Default: `100`.
- **timeout** (`float`): Timeout for queue operations in seconds. Default:
  `0.1`.
- **concurrency_limit** (`int | None`): Maximum number of concurrent workers.
  Default: `None`.
- **logger** (`logging.Logger | None`): Optional logger. Default: `None`.

#### Properties

- **is_full** (`bool`): Check if the queue is full.
- **is_empty** (`bool`): Check if the queue is empty.
- **metrics** (`dict[str, int]`): Get queue metrics.
- **size** (`int`): Get the current queue size.

#### Methods

##### start

```python
async def start(self) -> None
```

Start the queue for processing.

##### stop

```python
async def stop(self, timeout: float | None = None) -> None
```

Stop the queue and all worker tasks.

- **timeout** (`float | None`): Maximum time to wait for pending tasks. Default:
  `None`.

##### put

```python
async def put(self, item: T) -> bool
```

Add an item to the queue.

- **item** (`T`): The item to enqueue.
- **Returns** (`bool`): True if the item was enqueued, False if backpressure was
  applied.

##### process

```python
async def process(
    self,
    worker_func: Callable[[T], Awaitable[Any]],
    num_workers: int | None = None,
    error_handler: Callable[[Exception, T], Awaitable[None]] | None = None,
) -> None
```

Start worker tasks to process queue items.

- **worker_func** (`Callable[[T], Awaitable[Any]]`): Async function that
  processes each queue item.
- **num_workers** (`int | None`): Number of worker tasks to start. If None, uses
  concurrency_limit or 1. Default: `None`.
- **error_handler** (`Callable[[Exception, T], Awaitable[None]] | None`):
  Optional async function to handle worker errors. Default: `None`.

##### join

```python
async def join(self) -> None
```

Wait for all queue items to be processed.

##### batch_process

```python
async def batch_process(
    self,
    items: list[T],
    worker_func: Callable[[T], Awaitable[Any]],
    num_workers: int | None = None,
    error_handler: Callable[[Exception, T], Awaitable[None]] | None = None,
) -> None
```

Process a batch of items through the queue.

- **items** (`list[T]`): The items to process.
- **worker_func** (`Callable[[T], Awaitable[Any]]`): Async function that
  processes each queue item.
- **num_workers** (`int | None`): Number of worker tasks to start. If None, uses
  concurrency_limit or 1. Default: `None`.
- **error_handler** (`Callable[[Exception, T], Awaitable[None]] | None`):
  Optional async function to handle worker errors. Default: `None`.

#### Context Manager

`WorkQueue` implements the async context manager protocol (`__aenter__` and
`__aexit__`), allowing it to be used with `async with`:

```python
async with WorkQueue(maxsize=10, concurrency_limit=5) as queue:
    # Queue is started automatically
    await queue.process(worker_func)
    await queue.put(item)
    # Queue is stopped automatically when exiting the context
```

#### Example

```python
import asyncio
from lionfuncs.concurrency import WorkQueue

async def process_item(item):
    print(f"Processing {item}")
    await asyncio.sleep(0.1)
    return item * 2

async def handle_error(error, item):
    print(f"Error processing {item}: {error}")

async def main():
    # Create a work queue
    queue = WorkQueue(maxsize=5, concurrency_limit=3)

    # Process a batch of items
    await queue.batch_process(
        items=list(range(10)),
        worker_func=process_item,
        error_handler=handle_error
    )

    # Get metrics
    print(f"Queue metrics: {queue.metrics}")

asyncio.run(main())
```

## Concurrency Primitives

The following classes are wrappers around `anyio` primitives, providing a
consistent interface for concurrency primitives across different async backends.

### Lock

```python
class Lock
```

A mutex lock for controlling access to a shared resource. This lock is
reentrant, meaning the same task can acquire it multiple times without
deadlocking. Wraps `anyio.Lock`.

#### Methods

- **async def acquire() -> bool**: Acquire the lock.
- **def release() -> None**: Release the lock.

#### Context Manager

`Lock` implements the async context manager protocol, allowing it to be used
with `async with`:

```python
lock = Lock()
async with lock:
    # Critical section
    pass
```

### Semaphore

```python
class Semaphore
```

A semaphore for limiting concurrent access to a resource. Wraps
`anyio.Semaphore`.

#### Constructor

```python
def __init__(self, initial_value: int)
```

- **initial_value** (`int`): The initial value of the semaphore.
- **Raises** (`ValueError`): If initial_value is negative.

#### Methods

- **async def acquire() -> None**: Acquire the semaphore.
- **def release() -> None**: Release the semaphore.

#### Context Manager

`Semaphore` implements the async context manager protocol, allowing it to be
used with `async with`:

```python
semaphore = Semaphore(5)
async with semaphore:
    # Limited concurrency section
    pass
```

### CapacityLimiter

```python
class CapacityLimiter
```

A context manager for limiting the number of concurrent operations. Wraps
`anyio.CapacityLimiter`.

#### Constructor

```python
def __init__(self, total_tokens: float)
```

- **total_tokens** (`float`): The total number of tokens (must be >= 1).
- **Raises** (`ValueError`): If total_tokens is less than 1.

#### Methods

- **async def acquire() -> None**: Acquire a token.
- **def release() -> None**: Release a token.

#### Properties

- **total_tokens** (`float`): The total number of tokens.
- **borrowed_tokens** (`int`): The number of tokens currently borrowed.
- **available_tokens** (`float`): The number of tokens currently available.

#### Context Manager

`CapacityLimiter` implements the async context manager protocol, allowing it to
be used with `async with`:

```python
limiter = CapacityLimiter(10)
async with limiter:
    # Limited capacity section
    pass
```

### Event

```python
class Event
```

An event object for task synchronization. Wraps `anyio.Event`.

#### Methods

- **def is_set() -> bool**: Check if the event is set.
- **def set() -> None**: Set the event.
- **async def wait() -> None**: Wait for the event to be set.

#### Example

```python
import asyncio
from lionfuncs.concurrency import Event

async def waiter(event, name):
    print(f"{name} waiting for event")
    await event.wait()
    print(f"{name} received event")

async def main():
    event = Event()

    # Start waiters
    asyncio.create_task(waiter(event, "Waiter 1"))
    asyncio.create_task(waiter(event, "Waiter 2"))

    # Wait a bit
    await asyncio.sleep(1)

    # Set the event
    print("Setting event")
    event.set()

    # Wait for tasks to complete
    await asyncio.sleep(0.1)

asyncio.run(main())
```

### Condition

```python
class Condition
```

A condition variable for task synchronization. Wraps `anyio.Condition`.

#### Constructor

```python
def __init__(self, lock: Optional[Lock] = None)
```

- **lock** (`Optional[Lock]`): The lock to use. If None, a new Lock is created.
  Default: `None`.

#### Methods

- **async def wait() -> None**: Wait for the condition to be notified.
- **async def notify(n: int = 1) -> None**: Notify n waiters.
- **async def notify_all() -> None**: Notify all waiters.

#### Context Manager

`Condition` implements the async context manager protocol, allowing it to be
used with `async with`:

```python
condition = Condition()
async with condition:
    await condition.wait()
```

#### Example

```python
import asyncio
from lionfuncs.concurrency import Condition

async def producer(condition, queue):
    for i in range(5):
        async with condition:
            queue.append(i)
            print(f"Produced {i}")
            await condition.notify()
        await asyncio.sleep(0.5)

async def consumer(condition, queue, name):
    while True:
        async with condition:
            while not queue:
                await condition.wait()
            item = queue.pop(0)
            print(f"{name} consumed {item}")

async def main():
    condition = Condition()
    queue = []

    # Start consumer
    consumer_task = asyncio.create_task(consumer(condition, queue, "Consumer"))

    # Run producer
    await producer(condition, queue)

    # Cancel consumer
    consumer_task.cancel()
    try:
        await consumer_task
    except asyncio.CancelledError:
        pass

asyncio.run(main())
```
