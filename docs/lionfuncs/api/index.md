---
title: "lionfuncs API Reference"
---

# API Reference

This section provides detailed documentation for all public modules, classes,
functions, and decorators in the `lionfuncs` package.

## Modules

### Core Utilities

- [**utils**](utils.md): General utility functions.
- [**errors**](errors.md): Custom exception classes.
- [**parsers**](parsers.md): Robust parsing utilities for various data formats.
- [**dict_utils**](dict_utils.md): Utilities for advanced dictionary manipulation.
- [**format_utils**](format_utils.md): Utilities for formatting data into
  human-readable strings.
- [**to_dict**](to_dict.md): Utilities for converting various Python objects to dictionaries.
- [**to_list**](to_list.md): Utilities for converting various Python objects to lists.
- [**hash_utils**](hash_utils.md): Utilities for creating deterministic hashes for complex data structures.
- [**schema_utils**](schema_utils.md): Utilities for generating and manipulating
  schemas (renamed to oai_schema_utils.py).

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
├── parsers (depends on: orjson, dirtyjson)
├── dict_utils (depends on: rapidfuzz)
├── format_utils (depends on: to_dict)
├── to_dict (depends on: parsers, xmltodict)
├── to_list (depends on: hash_utils)
├── hash_utils
├── oai_schema_utils (formerly schema_utils)
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

### lionfuncs.errors

- `LionError`: Base exception for all lionfuncs errors.
- `LionFileError`: For file system operation errors.
- `LionNetworkError`: For network operation errors.
- `APIClientError`: Base for HTTP client errors.
- `LionConcurrencyError`: For concurrency primitive errors.
- `LionSDKError`: Base for errors originating from SDK interactions.

### lionfuncs.file_system

- `chunk_content(content, chunk_by="chars", ...)`: Split content by chars or
  tokens.
- `read_file(path)`: Read file content.
- `save_to_file(text, directory, filename, ...)`: Save text to a file.
- `list_files(dir_path, extension=None, recursive=False)`: List files in a
  directory.
- `concat_files(data_path, file_types, ...)`: Concatenate multiple files.
- `dir_to_files(directory, file_types=None, ...)`: Recursively list files in a
  directory.
- `read_image_to_base64(image_path)`: Read an image and encode to base64.
- `pdf_to_images(pdf_path, output_folder, ...)`: Convert PDF pages to images.

### lionfuncs.concurrency

- `BoundedQueue`: Bounded async queue with backpressure support.
- `WorkQueue`: High-level wrapper around BoundedQueue.
- `Lock`, `Semaphore`, `CapacityLimiter`, `Event`, `Condition`: Concurrency
  primitives.

### lionfuncs.async_utils

- `alcall(input_, func, ...)`: Asynchronously call a function for each item in a
  list.
- `bcall(input_, func, batch_size, ...)`: Asynchronously call a function in
  batches.
- `@max_concurrent(limit)`: Decorator to limit the concurrency of an async
  function.
- `@throttle(period)`: Decorator to throttle function execution.
- `parallel_map(func, items, max_concurrency=10)`: Apply an async function to
  each item in a list in parallel.
- `CancelScope`: Wrapper around anyio.CancelScope for structured cancellation.
- `TaskGroup`: Wrapper around anyio.create_task_group for managing groups of
  tasks.

### lionfuncs.network

- `AsyncAPIClient`: Generic async HTTP client.
- `@circuit_breaker(...)`: Decorator for circuit breaker pattern.
- `@with_retry(...)`: Decorator for retry with backoff.
- `AbstractSDKAdapter`: Protocol defining the interface for SDK adapters.
- `OpenAIAdapter`, `AnthropicAdapter`: SDK adapters for specific APIs.
- `EndpointConfig`, `Endpoint`: Classes for defining and calling API endpoints.
- `HeaderFactory`: Utility for creating auth/content headers.
- `TokenBucketRateLimiter`, `EndpointRateLimiter`, `AdaptiveRateLimiter`: Rate
  limiting classes.

### lionfuncs.parsers

- `fuzzy_parse_json(str_to_parse)`: Attempts to parse a JSON-like string into a Python object, trying several common fixes for non-standard JSON syntax.

### lionfuncs.dict_utils

- `fuzzy_match_keys(data_dict, reference_keys, threshold=0.8, default_method="wratio", jaro_winkler_prefix_weight=0.1, case_sensitive=False, handle_unmatched="ignore", fill_value=PydanticUndefined, fill_mapping=None, strict=False)`:
  Match dictionary keys fuzzily against reference keys, returning a new dictionary.

### lionfuncs.format_utils

- `as_readable(data, format_type="auto", indent=2, max_depth=None, in_notebook_override=None)`:
  Convert data into a human-readable string format.

### lionfuncs.to_dict

- `to_dict(input_, use_model_dump=True, use_enum_values=False, parse_strings=False, str_type_for_parsing="json", fuzzy_parse_strings=False, custom_str_parser=None, recursive=False, max_recursive_depth=5, recursive_stop_types=(...), suppress_errors=False, default_on_error=None, convert_top_level_iterable_to_dict=False, **kwargs)`:
  Convert various Python objects to a dictionary representation.

### lionfuncs.to_list

- `to_list(input_, flatten=False, dropna=False, unique=False, use_values=False, flatten_tuple_set=False)`:
  Converts various input types into a list with optional transformations.

### lionfuncs.hash_utils

- `hash_dict(data, strict=False)`:
  Computes a deterministic hash for various Python data structures.

### lionfuncs.oai_schema_utils (formerly schema_utils)

- `function_to_openai_schema(func)`: Generate an OpenAI function schema from a
  Python function.
- `pydantic_model_to_openai_schema(model_class, function_name, function_description)`: Convert a Pydantic model to an OpenAI function schema.
