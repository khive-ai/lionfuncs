---
title: "lionfuncs.async_utils"
---

# lionfuncs.async_utils

The `async_utils` module provides asynchronous utilities for parallel
processing, concurrency control, and structured concurrency. It includes
functions for processing lists and batches asynchronously, decorators for
controlling concurrency and throttling, and wrappers around `anyio` primitives
for structured concurrency.

## Functions

### alcall

```python
async def alcall(
    input_: list[Any],
    func: Callable[..., T],
    /,
    *,
    sanitize_input: bool = False,
    unique_input: bool = False,
    num_retries: int = 0,
    initial_delay: float = 0.0,
    retry_delay: float = 0.0,
    backoff_factor: float = 1.0,
    retry_default: Any = UNDEFINED,
    retry_timeout: Optional[float] = None,
    retry_timing: bool = False,
    max_concurrent: Optional[int] = None,
    throttle_period: Optional[float] = None,
    flatten: bool = False,
    dropna: bool = False,
    unique_output: bool = False,
    flatten_tuple_set: bool = False,
    **kwargs: Any,
) -> list[Any]
```

Asynchronously call a function for each item in a list with comprehensive
options for retries, concurrency, throttling, etc.

This function is useful for parallel processing of lists, with fine-grained
control over concurrency, retries, and result formatting.

#### Parameters

- **input_** (`list[Any]`): The list of items to process.
- **func** (`Callable[..., T]`): The function to call for each item.
- **sanitize_input** (`bool`, optional): Whether to sanitize the input list
  (flatten, clean). Defaults to `False`.
- **unique_input** (`bool`, optional): Whether to remove duplicates from the
  input list. Defaults to `False`.
- **num_retries** (`int`, optional): Number of retries for each call. Defaults
  to `0`.
- **initial_delay** (`float`, optional): Initial delay before processing in
  seconds. Defaults to `0.0`.
- **retry_delay** (`float`, optional): Delay between retries in seconds.
  Defaults to `0.0`.
- **backoff_factor** (`float`, optional): Factor to increase delay with each
  retry. Defaults to `1.0`.
- **retry_default** (`Any`, optional): Default value to return if all retries
  fail. Defaults to `UNDEFINED`.
- **retry_timeout** (`Optional[float]`, optional): Timeout for each call in
  seconds. Defaults to `None`.
- **retry_timing** (`bool`, optional): Whether to include timing information in
  the results. Defaults to `False`.
- **max_concurrent** (`Optional[int]`, optional): Maximum number of concurrent
  calls. Defaults to `None`.
- **throttle_period** (`Optional[float]`, optional): Minimum time between calls
  in seconds. Defaults to `None`.
- **flatten** (`bool`, optional): Whether to flatten the output list. Defaults
  to `False`.
- **dropna** (`bool`, optional): Whether to drop None values from the output.
  Defaults to `False`.
- **unique_output** (`bool`, optional): Whether to remove duplicates from the
  output. Defaults to `False`.
- **flatten_tuple_set** (`bool`, optional): Whether to flatten tuples and sets
  in the output. Defaults to `False`.
- **\*\*kwargs** (`Any`): Additional keyword arguments to pass to the function.

#### Returns

- `list[Any]`: The results of calling the function on each item. If
  `retry_timing` is `True`, each result is a tuple of `(result, duration)`.

#### Example

```python
import asyncio
from lionfuncs.async_utils import alcall

async def process_item(item):
    await asyncio.sleep(0.1)  # Simulate some async work
    return item * 2

async def main():
    items = [1, 2, 3, 4, 5]

    # Basic usage
    results = await alcall(items, process_item)
    print(f"Basic results: {results}")  # [2, 4, 6, 8, 10]

    # With concurrency limit
    results = await alcall(items, process_item, max_concurrent=2)
    print(f"Limited concurrency results: {results}")  # [2, 4, 6, 8, 10]

    # With retries and timing
    results = await alcall(
        items,
        process_item,
        num_retries=3,
        retry_delay=0.1,
        backoff_factor=2.0,
        retry_timing=True
    )
    print(f"Results with timing: {results}")  # [(2, 0.1), (4, 0.1), ...]

    # With throttling
    results = await alcall(items, process_item, throttle_period=0.2)
    print(f"Throttled results: {results}")  # [2, 4, 6, 8, 10]

asyncio.run(main())
```

### bcall

```python
async def bcall(
    input_: Any,
    func: Callable[..., T],
    /,
    batch_size: int,
    *,
    sanitize_input: bool = False,
    unique_input: bool = False,
    num_retries: int = 0,
    initial_delay: float = 0.0,
    retry_delay: float = 0.0,
    backoff_factor: float = 1.0,
    retry_default: Any = UNDEFINED,
    retry_timeout: Optional[float] = None,
    retry_timing: bool = False,
    max_concurrent: Optional[int] = None,
    throttle_period: Optional[float] = None,
    flatten: bool = False,
    dropna: bool = False,
    unique_output: bool = False,
    flatten_tuple_set: bool = False,
    **kwargs: Any,
) -> AsyncGenerator[list[Any], None]
```

Asynchronously call a function in batches.

This function is useful for processing large lists in smaller batches, with the
same fine-grained control as `alcall`.

#### Parameters

- **input_** (`Any`): The input to process (will be converted to a list).
- **func** (`Callable[..., T]`): The function to call for each item.
- **batch_size** (`int`): The size of each batch.
- **sanitize_input** (`bool`, optional): Whether to sanitize the input list
  (flatten, clean). Defaults to `False`.
- **unique_input** (`bool`, optional): Whether to remove duplicates from the
  input list. Defaults to `False`.
- **num_retries** (`int`, optional): Number of retries for each call. Defaults
  to `0`.
- **initial_delay** (`float`, optional): Initial delay before processing in
  seconds. Defaults to `0.0`.
- **retry_delay** (`float`, optional): Delay between retries in seconds.
  Defaults to `0.0`.
- **backoff_factor** (`float`, optional): Factor to increase delay with each
  retry. Defaults to `1.0`.
- **retry_default** (`Any`, optional): Default value to return if all retries
  fail. Defaults to `UNDEFINED`.
- **retry_timeout** (`Optional[float]`, optional): Timeout for each call in
  seconds. Defaults to `None`.
- **retry_timing** (`bool`, optional): Whether to include timing information in
  the results. Defaults to `False`.
- **max_concurrent** (`Optional[int]`, optional): Maximum number of concurrent
  calls within each batch. Defaults to `None`.
- **throttle_period** (`Optional[float]`, optional): Minimum time between calls
  in seconds. Defaults to `None`.
- **flatten** (`bool`, optional): Whether to flatten the output list. Defaults
  to `False`.
- **dropna** (`bool`, optional): Whether to drop None values from the output.
  Defaults to `False`.
- **unique_output** (`bool`, optional): Whether to remove duplicates from the
  output. Defaults to `False`.
- **flatten_tuple_set** (`bool`, optional): Whether to flatten tuples and sets
  in the output. Defaults to `False`.
- **\*\*kwargs** (`Any`): Additional keyword arguments to pass to the function.

#### Returns

- `AsyncGenerator[list[Any], None]`: An async generator that yields the results
  of each batch.

#### Example

```python
import asyncio
from lionfuncs.async_utils import bcall

async def process_item(item):
    await asyncio.sleep(0.1)  # Simulate some async work
    return item * 2

async def main():
    items = list(range(20))

    # Process in batches of 5
    async for batch_results in bcall(items, process_item, batch_size=5):
        print(f"Batch results: {batch_results}")

    # Process in batches with concurrency limit
    batch_results_all = []
    async for batch_results in bcall(
        items,
        process_item,
        batch_size=5,
        max_concurrent=2
    ):
        batch_results_all.append(batch_results)

    print(f"All batch results: {batch_results_all}")

asyncio.run(main())
```

### parallel_map

```python
async def parallel_map(
    func: Callable[[T], CAwaitable[R]],
    items: list[T],
    max_concurrency: int = 10,
) -> list[R]
```

Apply an async function to each item in a list in parallel, with limited
concurrency.

This function is a simpler alternative to `alcall` when you only need basic
parallel processing with concurrency control.

#### Parameters

- **func** (`Callable[[T], CAwaitable[R]]`): The asynchronous function to apply
  to each item.
- **items** (`list[T]`): The list of items to process.
- **max_concurrency** (`int`, optional): The maximum number of concurrent
  executions. Defaults to `10`.

#### Returns

- `list[R]`: A list of results in the same order as the input items.

#### Raises

- `Exception`: Propagates the first exception encountered from any of the tasks.

#### Example

```python
import asyncio
from lionfuncs.async_utils import parallel_map

async def process_item(item):
    await asyncio.sleep(0.1)  # Simulate some async work
    return item * 2

async def main():
    items = [1, 2, 3, 4, 5]

    # Process items in parallel with max concurrency of 3
    results = await parallel_map(process_item, items, max_concurrency=3)
    print(f"Results: {results}")  # [2, 4, 6, 8, 10]

asyncio.run(main())
```

## Decorators

### max_concurrent

```python
def max_concurrent(
    limit: int,
) -> Callable[[Callable[..., CAwaitable[Any]]], Callable[..., CAwaitable[Any]]]
```

Decorator to limit the concurrency of async function execution using a
semaphore.

If the function is synchronous, it will be wrapped to run in a thread pool.

#### Parameters

- **limit** (`int`): The maximum number of concurrent executions.

#### Returns

- `Callable[[Callable[..., CAwaitable[Any]]], Callable[..., CAwaitable[Any]]]`:
  A decorator that limits concurrency.

#### Raises

- `ValueError`: If limit is less than 1.

#### Example

```python
import asyncio
from lionfuncs.async_utils import max_concurrent

@max_concurrent(3)
async def process_item(item):
    print(f"Processing {item}")
    await asyncio.sleep(1)  # Simulate some async work
    print(f"Finished {item}")
    return item * 2

async def main():
    # Create tasks for 10 items
    tasks = [process_item(i) for i in range(10)]

    # Run all tasks
    results = await asyncio.gather(*tasks)
    print(f"Results: {results}")

asyncio.run(main())
```

### throttle

```python
def throttle(period: float) -> Callable[[Callable[..., Any]], Callable[..., Any]]
```

Decorator to throttle function execution to limit the rate of calls.

Works for both synchronous and asynchronous functions.

#### Parameters

- **period** (`float`): The minimum time period (in seconds) between calls.

#### Returns

- `Callable[[Callable[..., Any]], Callable[..., Any]]`: A decorator that
  throttles function execution.

#### Example

```python
import asyncio
import time
from lionfuncs.async_utils import throttle

# Throttle async function
@throttle(1.0)
async def async_function():
    print(f"Async function called at {time.time()}")
    return "async result"

# Throttle sync function
@throttle(1.0)
def sync_function():
    print(f"Sync function called at {time.time()}")
    return "sync result"

async def main():
    # Call async function multiple times
    for _ in range(3):
        result = await async_function()
        print(f"Async result: {result}")

    # Call sync function multiple times
    for _ in range(3):
        result = sync_function()
        print(f"Sync result: {result}")

asyncio.run(main())
```

## Classes

### Throttle

```python
class Throttle
```

Provides a throttling mechanism for function calls.

Ensures that the decorated function can only be called once per specified
period.

#### Constructor

```python
def __init__(self, period: float) -> None
```

- **period** (`float`): The minimum time period (in seconds) between calls.

#### Methods

- **\_\_call\_\_(func: Callable[..., T]) -> Callable[..., T]**: Decorate a
  synchronous function with the throttling mechanism.
- **async call_async_throttled(func: Callable[..., CAwaitable[Any]], *args,
  **kwargs) -> Any**: Helper to call an async function with throttling.

### ALCallParams

```python
class ALCallParams(CallParams)
```

Pydantic model for `alcall` parameters.

This class can be used to store and reuse parameter configurations for `alcall`.

#### Constructor

```python
def __init__(
    func: Optional[Callable[..., Any]] = None,
    sanitize_input: bool = False,
    unique_input: bool = False,
    num_retries: int = 0,
    initial_delay: float = 0.0,
    retry_delay: float = 0.0,
    backoff_factor: float = 1.0,
    retry_default: Any = UNDEFINED,
    retry_timeout: Optional[float] = None,
    retry_timing: bool = False,
    max_concurrent: Optional[int] = None,
    throttle_period: Optional[float] = None,
    flatten: bool = False,
    dropna: bool = False,
    unique_output: bool = False,
    flatten_tuple_set: bool = False,
    **kwargs,
)
```

#### Methods

- **async \_\_call\_\_(input_: Any, func: Optional[Callable[..., Any]] = None,
  **additional_kwargs)**: Call `alcall` with the stored parameters.

#### Example

```python
import asyncio
from lionfuncs.async_utils import ALCallParams

async def process_item(item):
    await asyncio.sleep(0.1)
    return item * 2

async def main():
    # Create a reusable parameter configuration
    params = ALCallParams(
        max_concurrent=3,
        num_retries=2,
        retry_delay=0.1,
        backoff_factor=2.0
    )

    # Use it with different inputs and functions
    items1 = [1, 2, 3, 4, 5]
    results1 = await params(items1, process_item)
    print(f"Results 1: {results1}")

    items2 = [10, 20, 30]
    results2 = await params(items2, process_item)
    print(f"Results 2: {results2}")

asyncio.run(main())
```

### BCallParams

```python
class BCallParams(CallParams)
```

Pydantic model for `bcall` parameters.

This class can be used to store and reuse parameter configurations for `bcall`.

#### Constructor

```python
def __init__(
    func: Optional[Callable[..., Any]] = None,
    batch_size: int,
    sanitize_input: bool = False,
    unique_input: bool = False,
    num_retries: int = 0,
    initial_delay: float = 0.0,
    retry_delay: float = 0.0,
    backoff_factor: float = 1.0,
    retry_default: Any = UNDEFINED,
    retry_timeout: Optional[float] = None,
    retry_timing: bool = False,
    max_concurrent: Optional[int] = None,
    throttle_period: Optional[float] = None,
    flatten: bool = False,
    dropna: bool = False,
    unique_output: bool = False,
    flatten_tuple_set: bool = False,
    **kwargs,
)
```

#### Methods

- **async \_\_call\_\_(input_: Any, func: Optional[Callable[..., Any]] = None,
  **additional_kwargs)**: Call `bcall` with the stored parameters.

#### Example

```python
import asyncio
from lionfuncs.async_utils import BCallParams

async def process_item(item):
    await asyncio.sleep(0.1)
    return item * 2

async def main():
    # Create a reusable parameter configuration
    params = BCallParams(
        batch_size=5,
        max_concurrent=3,
        num_retries=2
    )

    # Use it with different inputs and functions
    items = list(range(20))
    async for batch_results in params(items, process_item):
        print(f"Batch results: {batch_results}")

asyncio.run(main())
```

## Structured Concurrency

### CancelScope

```python
class CancelScope
```

A context manager for controlling cancellation of tasks, wrapping
anyio.CancelScope.

#### Constructor

```python
def __init__(self, *, deadline: float = float("inf"), shield: bool = False)
```

- **deadline** (`float`, optional): The deadline in seconds from the current
  time. Defaults to `float("inf")`.
- **shield** (`bool`, optional): Whether to shield the scope from external
  cancellation. Defaults to `False`.

#### Methods

- **cancel() -> None**: Cancel all tasks in the scope.

#### Properties

- **cancelled_caught** (`bool`): Whether cancellation was caught by this scope.
- **deadline** (`float`): The deadline in seconds from the current time.
- **shield** (`bool`): Whether the scope is shielded from external cancellation.

#### Context Manager

`CancelScope` implements the async context manager protocol, allowing it to be
used with `async with`:

```python
async with CancelScope(deadline=5.0) as scope:
    # Code that might be cancelled
    if condition:
        scope.cancel()
```

#### Example

```python
import asyncio
from lionfuncs.async_utils import CancelScope

async def long_running_task():
    try:
        print("Starting long task")
        await asyncio.sleep(10)
        print("Long task completed")
    except asyncio.CancelledError:
        print("Long task cancelled")
        raise

async def main():
    # With deadline
    try:
        async with CancelScope(deadline=2.0):
            await long_running_task()
    except asyncio.CancelledError:
        print("Caught deadline cancellation")

    # With manual cancellation
    async with CancelScope() as scope:
        task = asyncio.create_task(long_running_task())
        await asyncio.sleep(1)
        scope.cancel()
        try:
            await task
        except asyncio.CancelledError:
            print("Task was cancelled")

asyncio.run(main())
```

### TaskGroup

```python
class TaskGroup
```

A group of tasks that are treated as a unit, wrapping anyio.abc.TaskGroup.

#### Methods

- *_start_soon(func: Callable[..., CAwaitable[Any]], _args: Any, name: Any =
  None) -> None__: Start a task in the group.

#### Context Manager

`TaskGroup` implements the async context manager protocol, allowing it to be
used with `async with`:

```python
async with TaskGroup() as tg:
    tg.start_soon(task1)
    tg.start_soon(task2)
    # All tasks will be awaited when exiting the context
```

#### Example

```python
import asyncio
from lionfuncs.async_utils import TaskGroup

async def task(name, delay):
    print(f"Task {name} starting")
    await asyncio.sleep(delay)
    print(f"Task {name} completed")
    return name

async def main():
    async with TaskGroup() as tg:
        # Start multiple tasks
        tg.start_soon(task, "A", 1.0)
        tg.start_soon(task, "B", 0.5)
        tg.start_soon(task, "C", 2.0)

        # All tasks will be awaited when exiting the context

asyncio.run(main())
```
