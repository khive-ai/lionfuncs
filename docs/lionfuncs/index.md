---
title: "lionfuncs Documentation"
---

# lionfuncs

`lionfuncs` is a Python package that provides a core set of reusable utilities
for asynchronous operations, file system interactions, network calls,
concurrency management, error handling, and general utilities.

## Installation

### Basic Installation

```bash
pip install lionfuncs
```

### Installation with Media Utilities

To use the media utilities (e.g., `pdf_to_images`), install with the `media`
extra:

```bash
pip install lionfuncs[media]
```

## Package Structure

`lionfuncs` is organized into several modules:

- **[utils](api/utils.md)**: General utility functions like `is_coro_func`,
  `force_async`, `get_env_bool`, `get_env_dict`, and `to_list`.
- **[errors](api/errors.md)**: Custom exception classes for the package.
- **[file_system](api/file_system/index.md)**: File system utilities for
  reading, writing, listing, and processing files.
  - **[core](api/file_system/core.md)**: Core file system operations.
  - **[media](api/file_system/media.md)**: Media-specific file operations
    (images, PDFs).
- **[concurrency](api/concurrency.md)**: Concurrency primitives and utilities
  like `BoundedQueue` and `WorkQueue`.
- **[async_utils](api/async_utils.md)**: Asynchronous utilities like `alcall`,
  `bcall`, `@max_concurrent`, and `@throttle`.
- **[network](api/network/index.md)**: Network utilities for making HTTP
  requests and handling resilience patterns.
  - **[client](api/network/client.md)**: `AsyncAPIClient` for making HTTP
    requests.
  - **[resilience](api/network/resilience.md)**: Resilience patterns like
    circuit breaker and retry with backoff.
  - **[adapters](api/network/adapters.md)**: SDK adapters for third-party APIs.
  - **[primitives](api/network/primitives.md)**: Network primitives like
    `Endpoint` and rate limiters.
  - **[events](api/network/events.md)**: Event classes for tracking API request
    lifecycles.
  - **[executor](api/network/executor.md)**: Executor for managing and
    rate-limiting API calls.
  - **[imodel](api/network/imodel.md)**: Client for interacting with API models
    using the Executor.

## Quick Start

### Asynchronous Operations

```python
import asyncio
from lionfuncs.async_utils import alcall

async def process_item(item):
    await asyncio.sleep(0.1)  # Simulate some async work
    return item * 2

async def main():
    items = [1, 2, 3, 4, 5]
    # Process all items concurrently with a max concurrency of 3
    results = await alcall(items, process_item, max_concurrent=3)
    print(results)  # [2, 4, 6, 8, 10]

asyncio.run(main())
```

### File System Operations

```python
import asyncio
from lionfuncs.file_system import read_file, save_to_file

async def main():
    # Read a file
    content = await read_file("example.txt")

    # Process the content
    processed_content = content.upper()

    # Save the processed content
    await save_to_file(processed_content, "output", "example_processed.txt")

asyncio.run(main())
```

### Network Operations

```python
import asyncio
from lionfuncs.network import AsyncAPIClient, circuit_breaker, with_retry

# Apply resilience patterns with decorators
@circuit_breaker(failure_threshold=3, recovery_time=10.0)
@with_retry(max_retries=3, base_delay=1.0, backoff_factor=2.0)
async def fetch_data(client, endpoint):
    return await client.request("GET", endpoint)

async def main():
    async with AsyncAPIClient(base_url="https://api.example.com") as client:
        data = await fetch_data(client, "/data")
        print(data)

asyncio.run(main())
```

## Usage Guides

For more detailed examples and usage patterns, check out the following guides:

- [Async Operations Guide](guides/async_operations.md)
- [File System Utilities Guide](guides/file_system_utils.md)
- [Network Client Guide](guides/network_client.md)
- [Resilience Patterns Guide](guides/resilience_patterns.md)
- [Network Executor Usage Guide](guides/network_executor_usage.md)

## API Reference

For detailed API documentation, see the [API Reference](api/index.md).

## Contributing

Interested in contributing to `lionfuncs`? Check out the
[Contribution Guidelines](contributing.md).

## License

`lionfuncs` is licensed under the MIT License. See the
[LICENSE](https://github.com/khive-ai/lionfuncs/blob/main/LICENSE) file for
details.
