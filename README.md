# lionfuncs

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](https://opensource.org/licenses/MIT)

A Python utility library for robust asynchronous programming, file system
operations, and network interactions.

## Overview

`lionfuncs` provides a core set of reusable utilities designed to simplify
common programming tasks with a focus on reliability and performance. It offers
a comprehensive suite of tools for asynchronous operations, file system
interactions, network calls, concurrency management, error handling, and general
utilities.

## Key Features

- **Async Utilities**: Powerful tools like `alcall` and `bcall` for concurrent
  execution with fine-grained control
- **Concurrency Management**: Primitives such as `BoundedQueue` and `WorkQueue`
  for managing concurrent workloads
- **File System Operations**: Utilities for reading, writing, and processing
  files with both sync and async APIs
- **Network Client**: Resilient HTTP client with built-in circuit breaker,
  retry, and rate limiting capabilities
- **Error Handling**: Standardized error types and handling mechanisms
- **Media Processing**: Optional utilities for working with images and PDFs

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

## Documentation

For comprehensive documentation, including detailed API references and usage
guides, visit:

- [API Reference](docs/lionfuncs/api/index.md)
- [Usage Guides](docs/lionfuncs/guides)
  - [Async Operations Guide](docs/lionfuncs/guides/async_operations.md)
  - [File System Utilities Guide](docs/lionfuncs/guides/file_system_utils.md)
  - [Network Client Guide](docs/lionfuncs/guides/network_client.md)
  - [Resilience Patterns Guide](docs/lionfuncs/guides/resilience_patterns.md)

## Contributing

We welcome contributions to `lionfuncs`! Please see our
[Contribution Guidelines](docs/lionfuncs/contributing.md) for details on how to
get started, coding standards, and the pull request process.

## License

`lionfuncs` is licensed under the MIT License. See the [LICENSE](LICENSE) file
for details.
