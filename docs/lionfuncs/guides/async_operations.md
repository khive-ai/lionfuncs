---
title: "Async Operations Guide"
---

# Async Operations Guide

This guide covers advanced asynchronous operations using the
`lionfuncs.async_utils` module, focusing on parallel processing with `alcall`
and `bcall`, controlling concurrency with `@max_concurrent`, and rate limiting
with `@throttle`.

## Introduction to Asynchronous Programming

Asynchronous programming allows you to write non-blocking code that can perform
multiple operations concurrently. Python's `asyncio` library provides the
foundation for asynchronous programming, and `lionfuncs` builds on top of it to
provide higher-level abstractions.

Key concepts:

- **Coroutines**: Functions defined with `async def` that can be paused and
  resumed.
- **Tasks**: Wrappers around coroutines that allow them to be scheduled for
  execution.
- **Event Loop**: The core of asyncio, responsible for executing coroutines and
  handling I/O operations.

## Parallel Processing with alcall

The `alcall` (async list call) function is a powerful tool for processing lists
of items in parallel with fine-grained control over concurrency, retries, and
result formatting.

### Basic Usage

```python
import asyncio
from lionfuncs.async_utils import alcall

async def process_item(item):
    await asyncio.sleep(0.1)  # Simulate some async work
    return item * 2

async def main():
    items = [1, 2, 3, 4, 5]

    # Process all items concurrently
    results = await alcall(items, process_item)
    print(f"Results: {results}")  # [2, 4, 6, 8, 10]

asyncio.run(main())
```

### Controlling Concurrency

By default, `alcall` processes all items concurrently, which might not be
desirable for large lists or resource-intensive operations. You can limit
concurrency with the `max_concurrent` parameter:

```python
async def main():
    items = list(range(100))

    # Process items with a maximum of 10 concurrent operations
    results = await alcall(items, process_item, max_concurrent=10)
    print(f"Processed {len(results)} items")

asyncio.run(main())
```

### Retries and Error Handling

`alcall` supports automatic retries with exponential backoff:

```python
import random
from lionfuncs.async_utils import alcall

async def flaky_operation(item):
    # Simulate an operation that sometimes fails
    if random.random() < 0.3:
        raise ConnectionError(f"Failed to process {item}")
    return item * 2

async def main():
    items = list(range(20))

    # Process with retries
    results = await alcall(
        items,
        flaky_operation,
        num_retries=3,           # Number of retry attempts
        retry_delay=0.5,         # Initial delay between retries
        backoff_factor=2.0,      # Factor to increase delay with each retry
        retry_default="FAILED",  # Default value if all retries fail
    )
    print(f"Results: {results}")

asyncio.run(main())
```

### Timing Information

You can include timing information in the results:

```python
async def main():
    items = list(range(10))

    # Process with timing information
    results = await alcall(
        items,
        process_item,
        retry_timing=True  # Include timing information
    )

    # Each result is a tuple of (result, duration)
    for result, duration in results:
        print(f"Result: {result}, Duration: {duration:.4f}s")

asyncio.run(main())
```

### Input and Output Processing

`alcall` provides options for processing input and output:

```python
async def main():
    # Input with nested lists
    nested_input = [[1, 2], [3, 4], [5, 6]]

    # Process with input and output transformations
    results = await alcall(
        nested_input,
        process_item,
        sanitize_input=True,  # Flatten and clean input
        flatten=True,         # Flatten output
        dropna=True,          # Drop None values from output
        unique_output=True,   # Remove duplicates from output
    )
    print(f"Results: {results}")

asyncio.run(main())
```

## Batch Processing with bcall

The `bcall` (batch call) function is similar to `alcall`, but processes items in
batches. This is useful for operations that benefit from batching, such as
database operations or API calls with batch endpoints.

### Basic Usage

```python
import asyncio
from lionfuncs.async_utils import bcall

async def process_batch(item):
    await asyncio.sleep(0.1)  # Simulate some async work
    return item * 2

async def main():
    items = list(range(100))

    # Process in batches of 10
    batch_count = 0
    async for batch_results in bcall(items, process_batch, batch_size=10):
        batch_count += 1
        print(f"Batch {batch_count} results: {batch_results[:3]}...")

asyncio.run(main())
```

### Combining with alcall Parameters

`bcall` supports all the same parameters as `alcall` for each batch:

```python
async def main():
    items = list(range(100))

    # Process in batches with concurrency limit and retries
    all_results = []
    async for batch_results in bcall(
        items,
        process_batch,
        batch_size=20,
        max_concurrent=5,     # Limit concurrency within each batch
        num_retries=2,        # Retry failed operations
        retry_delay=0.5,      # Initial delay between retries
        backoff_factor=2.0,   # Factor to increase delay with each retry
    ):
        all_results.extend(batch_results)

    print(f"Processed {len(all_results)} items")

asyncio.run(main())
```

### Reusing Configuration with BCallParams

You can create a reusable configuration with `BCallParams`:

```python
from lionfuncs.async_utils import BCallParams

async def main():
    # Create a reusable configuration
    batch_processor = BCallParams(
        batch_size=20,
        max_concurrent=5,
        num_retries=2,
        retry_delay=0.5,
        backoff_factor=2.0,
    )

    # Use it with different inputs and functions
    items1 = list(range(100))
    async for batch_results in batch_processor(items1, process_batch):
        print(f"Batch results length: {len(batch_results)}")

    items2 = list(range(50))
    async for batch_results in batch_processor(items2, process_batch):
        print(f"Batch results length: {len(batch_results)}")

asyncio.run(main())
```

## Controlling Concurrency with @max_concurrent

The `@max_concurrent` decorator limits the concurrency of an async function
using a semaphore:

```python
import asyncio
import time
from lionfuncs.async_utils import max_concurrent

@max_concurrent(3)  # Maximum of 3 concurrent executions
async def process_item(item):
    print(f"Started processing {item} at {time.time():.2f}")
    await asyncio.sleep(1)  # Simulate some async work
    print(f"Finished processing {item} at {time.time():.2f}")
    return item * 2

async def main():
    # Create tasks for 10 items
    tasks = [process_item(i) for i in range(10)]

    # Run all tasks
    results = await asyncio.gather(*tasks)
    print(f"Results: {results}")

asyncio.run(main())
```

This will limit the concurrency to 3, so you'll see that only 3 items are
processed at a time.

## Rate Limiting with @throttle

The `@throttle` decorator limits the rate of function calls:

```python
import asyncio
import time
from lionfuncs.async_utils import throttle

@throttle(1.0)  # Minimum of 1 second between calls
async def api_call(item):
    print(f"API call for {item} at {time.time():.2f}")
    await asyncio.sleep(0.1)  # Simulate API call
    return item * 2

async def main():
    # Make 5 API calls
    for i in range(5):
        result = await api_call(i)
        print(f"Result: {result}")

asyncio.run(main())
```

This will ensure that there's at least 1 second between each API call,
regardless of how quickly the calls are made.

## Structured Concurrency with TaskGroup and CancelScope

`lionfuncs` provides wrappers around `anyio` primitives for structured
concurrency:

### TaskGroup

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

### CancelScope

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

## Combining with Other lionfuncs Modules

The async utilities can be combined with other `lionfuncs` modules for powerful
workflows:

### With Network Module

```python
import asyncio
from lionfuncs.async_utils import alcall
from lionfuncs.network import AsyncAPIClient

async def fetch_user(user_id):
    async with AsyncAPIClient(base_url="https://api.example.com") as client:
        return await client.request("GET", f"/users/{user_id}")

async def main():
    user_ids = list(range(1, 11))

    # Fetch multiple users in parallel
    users = await alcall(
        user_ids,
        fetch_user,
        max_concurrent=5,  # Limit concurrency
        num_retries=3,     # Retry failed requests
    )

    print(f"Fetched {len(users)} users")

asyncio.run(main())
```

### With File System Module

```python
import asyncio
from lionfuncs.async_utils import alcall
from lionfuncs.file_system import read_file, save_to_file

async def process_file(file_path):
    # Read the file
    content = await read_file(file_path)

    # Process the content
    processed_content = content.upper()

    # Save the processed content
    output_path = await save_to_file(
        processed_content,
        "output",
        f"processed_{file_path.name}",
        file_exist_ok=True,
    )

    return output_path

async def main():
    file_paths = [Path(f"input/file{i}.txt") for i in range(1, 11)]

    # Process multiple files in parallel
    output_paths = await alcall(
        file_paths,
        process_file,
        max_concurrent=3,  # Limit concurrency
    )

    print(f"Processed {len(output_paths)} files")

# Note: This example assumes the input files exist
```

## Best Practices

1. **Limit Concurrency**: Always use `max_concurrent` to limit concurrency for
   resource-intensive operations.
2. **Handle Errors**: Use `num_retries` and `retry_default` to handle transient
   errors.
3. **Monitor Performance**: Use `retry_timing` to monitor the performance of
   your operations.
4. **Batch Processing**: Use `bcall` for operations that benefit from batching.
5. **Structured Concurrency**: Use `TaskGroup` and `CancelScope` for structured
   concurrency.
6. **Rate Limiting**: Use `@throttle` to limit the rate of function calls,
   especially for API calls.

## Conclusion

The `lionfuncs.async_utils` module provides powerful tools for asynchronous
programming, allowing you to process data in parallel with fine-grained control
over concurrency, retries, and result formatting. By combining these tools with
other `lionfuncs` modules, you can build robust and efficient asynchronous
workflows.
