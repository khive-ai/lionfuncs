---
title: "lionfuncs API Reference"
---

# API Reference

This section provides detailed documentation for all public modules, classes, functions, and decorators in the `lionfuncs` package.

## Modules

### Core Utilities

- [**utils**](utils.md): General utility functions.
- [**errors**](errors.md): Custom exception classes.

### File System

- [**file_system**](file_system/index.md): File system utilities.
  - [**core**](file_system/core.md): Core file system operations.
  - [**media**](file_system/media.md): Media-specific file operations.

### Concurrency and Async

- [**concurrency**](concurrency.md): Concurrency primitives and utilities.
- [**async_utils**](async_utils.md): Asynchronous utilities.

### Network

- [**network**](network/index.md): Network utilities.
  - [**client**](network/client.md): Async API client.
  - [**resilience**](network/resilience.md): Resilience patterns.
  - [**adapters**](network/adapters.md): SDK adapters.
  - [**primitives**](network/primitives.md): Network primitives.

## Module Dependencies

The following diagram shows the dependencies between the modules:

```
lionfuncs
├── utils
├── errors
├── file_system
│   ├── core (depends on: errors)
│   └── media (depends on: errors)
├── concurrency (depends on: errors)
├── async_utils (depends on: utils, concurrency)
└── network
    ├── client (depends on: errors)
    ├── resilience (depends on: errors)
    ├── adapters (depends on: errors)
    └── primitives (depends on: concurrency)
```

## Public API

The `lionfuncs` package exposes the following public APIs:

### lionfuncs.utils

- `is_coro_func(func)`: Check if a callable is a coroutine function.
- `force_async(func)`: Wrap a synchronous function to be called asynchronously.
- `get_env_bool(var_name, default=False)`: Get a boolean environment variable.
- `get_env_dict(var_name, default=None)`: Get a dictionary environment variable.
- `to_list(input_, flatten=False, dropna=False, unique=False, use_values=False, flatten_tuple_set=False)`: Convert input to a list with optional transformations.

### lionfuncs.errors

- `LionError`: Base exception for all lionfuncs errors.
- `LionFileError`: For file system operation errors.
- `LionNetworkError`: For network operation errors.
- `APIClientError`: Base for HTTP client errors.
- `LionConcurrencyError`: For concurrency primitive errors.
- `LionSDKError`: Base for errors originating from SDK interactions.

### lionfuncs.file_system

- `chunk_content(content, chunk_by="chars", ...)`: Split content by chars or tokens.
- `read_file(path)`: Read file content.
- `save_to_file(text, directory, filename, ...)`: Save text to a file.
- `list_files(dir_path, extension=None, recursive=False)`: List files in a directory.
- `concat_files(data_path, file_types, ...)`: Concatenate multiple files.
- `dir_to_files(directory, file_types=None, ...)`: Recursively list files in a directory.
- `read_image_to_base64(image_path)`: Read an image and encode to base64.
- `pdf_to_images(pdf_path, output_folder, ...)`: Convert PDF pages to images.

### lionfuncs.concurrency

- `BoundedQueue`: Bounded async queue with backpressure support.
- `WorkQueue`: High-level wrapper around BoundedQueue.
- `Lock`, `Semaphore`, `CapacityLimiter`, `Event`, `Condition`: Concurrency primitives.

### lionfuncs.async_utils

- `alcall(input_, func, ...)`: Asynchronously call a function for each item in a list.
- `bcall(input_, func, batch_size, ...)`: Asynchronously call a function in batches.
- `@max_concurrent(limit)`: Decorator to limit the concurrency of an async function.
- `@throttle(period)`: Decorator to throttle function execution.
- `parallel_map(func, items, max_concurrency=10)`: Apply an async function to each item in a list in parallel.
- `CancelScope`: Wrapper around anyio.CancelScope for structured cancellation.
- `TaskGroup`: Wrapper around anyio.create_task_group for managing groups of tasks.

### lionfuncs.network

- `AsyncAPIClient`: Generic async HTTP client.
- `@circuit_breaker(...)`: Decorator for circuit breaker pattern.
- `@with_retry(...)`: Decorator for retry with backoff.
- `AbstractSDKAdapter`: Protocol defining the interface for SDK adapters.
- `OpenAIAdapter`, `AnthropicAdapter`: SDK adapters for specific APIs.
- `EndpointConfig`, `Endpoint`: Classes for defining and calling API endpoints.
- `HeaderFactory`: Utility for creating auth/content headers.
- `TokenBucketRateLimiter`, `EndpointRateLimiter`, `AdaptiveRateLimiter`: Rate limiting classes.