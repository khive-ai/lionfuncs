---
title: "Technical Design Specification: lionfuncs Package (Issue #2)"
status: "Draft"
date: "2025-05-19"
author: "@khive-architect"
version: "1.0"
issue: "https://github.com/khive-ai/lionfuncs/issues/2"
---

## 1. Introduction

This document outlines the technical design for the `lionfuncs` Python package,
as specified in GitHub Issue #2. The `lionfuncs` package aims to provide a core
set of reusable utilities for asynchronous operations, file system interactions,
network calls, concurrency management, error handling, and general utilities. It
will be located at `src/lionfuncs/`.

This design is based on the requirements outlined in Issue #2, and refactoring
of existing code found in `/.khive/dev/concurrency.py` and
`/.khive/dev/file.py`.

**Note on Missing Source Files:** The source files `adapter.py`,
`sdk_errors.py`, and `binary_message.py`, originally expected to be in
`/.khive/dev/transport/`, were not found despite searches in that directory and
the broader `/.khive/` directory. The design for components intended to be
refactored from these files (primarily affecting `lionfuncs.network` and
`lionfuncs.errors`) is therefore based on the specifications in Issue #2 and
general best practices.

## 2. Proposed File Structure (`src/lionfuncs/`)

```
src/lionfuncs/
├── __init__.py
├── async_utils.py
├── concurrency.py
├── errors.py
├── file_system/
│   ├── __init__.py
│   ├── core.py       # Main file system functions
│   └── media.py      # Media-specific file functions
├── network/
│   ├── __init__.py
│   ├── client.py     # AsyncAPIClient
│   ├── resilience.py # Circuit breaker, retry decorators
│   ├── adapters.py   # SDK adapter interfaces/implementations (conceptual)
│   └── Primitives.py # EndpointConfig, HeaderFactory, BinaryMessage (conceptual)
└── utils.py
```

## 3. Module Design Details

### 3.1. `lionfuncs.async_utils`

(Source: Refactor from `/.khive/dev/concurrency.py`)

**File:** `src/lionfuncs/async_utils.py`

**Public API (`__all__`):**

- `alcall(input_: list[Any], func: Callable[..., T], ..., **kwargs) -> list[T] | list[tuple[T, float]]`:
  Asynchronously call a function for each item in a list with comprehensive
  options for retries, concurrency, throttling, etc.
- `bcall(input_: Any, func: Callable[..., T], batch_size: int, ..., **kwargs) -> AsyncGenerator[list[T | tuple[T, float]], None]`:
  Asynchronously call a function in batches.
- `@max_concurrent(limit: int) -> Callable`: Decorator to limit the concurrency
  of an async function using a semaphore. (Wraps `asyncio.Semaphore`).
- `@throttle(period: float) -> Callable`: Decorator to throttle function
  execution (sync/async).
- `parallel_map(func: Callable[[T], Awaitable[R]], items: list[T], max_concurrency: int = 10) -> list[R]`:
  (Equivalent to `parallel_requests` in `concurrency.py`, to be
  renamed/adapted).

**Internal/Advanced Components (Not in `__all__` unless explicitly decided
otherwise):**

- `CancelScope`: Wrapper around `anyio.CancelScope` for structured cancellation.
  (From `pynector.concurrency.cancel` via `concurrency.py`).
- `TaskGroup`: Wrapper around `anyio.create_task_group` for managing groups of
  tasks. (From `pynector.concurrency.task` via `concurrency.py`).
- `ALCallParams(CallParams)`: Pydantic model for `alcall` parameters.
- `BCallParams(CallParams)`: Pydantic model for `bcall` parameters.
- `Throttle` (class): The class implementing the throttle logic, used by the
  `@throttle` decorator.

**Refactoring Notes:**

- Extract `Throttle` class, `throttle` decorator, `max_concurrent` decorator.
- Extract `alcall`, `bcall` functions and their associated `Params` Pydantic
  models.
- Adapt `parallel_requests` from `concurrency.py` to `parallel_map` as specified
  in the issue.
- Integrate `CancelScope` and `TaskGroup` (likely as wrappers or direct
  re-exports if `anyio` is a direct dependency, or reimplement if `pynector` is
  not desired as a direct dependency).

### 3.2. `lionfuncs.concurrency`

(Source: Refactor from `/.khive/dev/concurrency.py`)

**File:** `src/lionfuncs/concurrency.py`

**Public API (`__all__`):**

- `BoundedQueue(Generic[T])`: Bounded async queue with backpressure support.
- `WorkQueue(Generic[T])`: High-level wrapper around `BoundedQueue`.

**Internal/Advanced Components (Not in `__all__` unless explicitly decided
otherwise):**

- `Lock`: Wrapper around `anyio.Lock`. (From `pynector.concurrency.primitives`
  via `concurrency.py`).
- `Semaphore`: Wrapper around `anyio.Semaphore`. (From
  `pynector.concurrency.primitives` via `concurrency.py`).
- `CapacityLimiter`: Wrapper around `anyio.CapacityLimiter`. (From
  `pynector.concurrency.primitives` via `concurrency.py`).
- `Event`: Wrapper around `anyio.Event`. (From `pynector.concurrency.primitives`
  via `concurrency.py`).
- `Condition`: Wrapper around `anyio.Condition`. (From
  `pynector.concurrency.primitives` via `concurrency.py`).
- `QueueStatus(str, Enum)`: Enum for queue states.
- `QueueConfig(BaseModel)`: Pydantic model for queue configuration.

**Refactoring Notes:**

- Extract `BoundedQueue`, `WorkQueue`, `QueueStatus`, and `QueueConfig`.
- Integrate `Lock`, `Semaphore`, `CapacityLimiter`, `Event`, `Condition` (as
  wrappers or re-exports from `anyio` or reimplement if `pynector` is not a
  direct dependency).

### 3.3. `lionfuncs.file_system`

(Source: Refactor from `/.khive/dev/file.py`)

**File Structure:**

- `src/lionfuncs/file_system/__init__.py`
- `src/lionfuncs/file_system/core.py`
- `src/lionfuncs/file_system/media.py`

**Public API (`__all__` in `file_system/__init__.py`):**

- From `core.py`:
  - `chunk_content(content: str, chunk_by: Literal["chars", "tokens"], ..., as_node: bool = False) -> list[dict | Node]`:
    Splits content by chars or tokens.
  - `read_file(path: Path | str) -> str`: Reads file content.
  - `save_to_file(text: str, directory: Path | str, filename: str, ..., verbose: bool = False) -> Path`:
    Saves text to a file.
  - `list_files(dir_path: Path | str, extension: str | None = None, recursive: bool = False) -> list[Path]`:
    Lists files in a directory (potentially non-recursive by default,
    `dir_to_files` for recursive).
  - `concat_files(data_path: str | Path | list, file_types: list[str], ..., return_files: bool = False) -> list[str] | str | tuple`:
    Concatenates multiple files.
  - `dir_to_files(directory: str | Path, ..., recursive: bool = True) -> list[Path]`:
    Recursively lists files in a directory.
- From `media.py`:
  - `read_image_to_base64(image_path: str | Path) -> str`: Reads an image and
    encodes to base64.
  - `pdf_to_images(pdf_path: str, output_folder: str, ...) -> list`: Converts
    PDF pages to images.

**Internal Components:**

- Helper functions from `file.py` like `_chunk_two_parts`,
  `_chunk_multiple_parts`, `_process_single_chunk`, `_chunk_token_two_parts`,
  `_chunk_token_multiple_parts`, `_format_chunks` will be internal to `core.py`.
- `create_path` utility might be an internal helper within `file_system` or
  moved to `lionfuncs.utils`.
- The `FileUtil` class itself will likely be deprecated in favor of direct
  functional imports, or kept as an internal utility if its structure is
  beneficial.

**Refactoring Notes:**

- Split functions from `file.py` into `core.py` and `media.py`.
- Ensure public API functions are directly importable from
  `lionfuncs.file_system`.
- `chunk_content` will be the primary chunking interface.
- Clarify the distinction and naming between `list_files` and `dir_to_files`
  based on recursive behavior. The issue lists both; `dir_to_files` implies
  recursion. `list_files` could be top-level only.

### 3.4. `lionfuncs.network`

(Source: Consolidate `AsyncAPIClient` from `/.khive/dev/concurrency.py`.
Integrate SDK adapters and `BinaryMessage` conceptually as
`/.khive/dev/transport/` files were missing.)

**File Structure:**

- `src/lionfuncs/network/__init__.py`
- `src/lionfuncs/network/client.py`
- `src/lionfuncs/network/resilience.py`
- `src/lionfuncs/network/adapters.py` (Conceptual)
- `src/lionfuncs/network/primitives.py` (Conceptual for `EndpointConfig`,
  `HeaderFactory`, `BinaryMessage`)

**Public API (`__all__` in `network/__init__.py`):**

- From `client.py`:
  - `AsyncAPIClient`: Generic async HTTP client.
- From `resilience.py`:
  - `@circuit_breaker(...) -> Callable`: Decorator for circuit breaker pattern.
  - `@with_retry(...) -> Callable`: Decorator for retry with backoff.
- From `primitives.py` (Potentially, if `Endpoint` itself is public):
  - `Endpoint`: Class to define and call specific API endpoints (from
    `concurrency.py`).

**Internal/Advanced Components:**

- From `client.py`:
  - Internal error handling logic within `AsyncAPIClient.request`.
- From `resilience.py`:
  - `CircuitBreaker` (class): Used by the decorator.
  - `RetryConfig` (class): Configuration for retry logic.
  - `retry_with_backoff` (function): Core retry logic.
- From `primitives.py`:
  - `EndpointConfig(BaseModel)`: Configuration for `Endpoint` instances.
  - `HeaderFactory`: Utility for creating auth/content headers.
  - `match_endpoint`: Function to select an `Endpoint` instance.
  - `TokenBucketRateLimiter`, `EndpointRateLimiter`, `AdaptiveRateLimiter`: Rate
    limiting classes from `concurrency.py`. These might be internal or advanced
    primitives.
  - `BinaryMessage` (Conceptual): A class/type definition for handling binary
    request/response bodies. Its interface would need to define how it
    serializes/deserializes data and indicates content type.
- From `adapters.py` (Conceptual):
  - `AbstractSDKAdapter(Protocol)`: Defines the interface for SDK adapters
    (e.g., `async def call(self, method_name: str, **kwargs) -> Any`).
  - `OpenAIAdapter(AbstractSDKAdapter)`: Conceptual implementation for OpenAI.
  - `AnthropicAdapter(AbstractSDKAdapter)`: Conceptual implementation for
    Anthropic.
  - `AsyncAPIClient` would be modified to optionally use these adapters if a
    request is designated for an SDK rather than direct HTTP.

**Refactoring Notes:**

- Move `AsyncAPIClient`, `EndpointConfig`, `Endpoint`, `HeaderFactory`,
  `match_endpoint` from `concurrency.py` to `network/client.py` and
  `network/primitives.py`.
- Move resilience patterns (`CircuitBreaker` class, `@circuit_breaker`
  decorator, `RetryConfig`, `retry_with_backoff`, `@with_retry` decorator) from
  `concurrency.py` to `network/resilience.py`.
- Move rate limiting classes (`TokenBucketRateLimiter`, etc.) from
  `concurrency.py` to `network/resilience.py` or `network/primitives.py` as
  internal/advanced components.
- **Due to missing `adapter.py`**: Design `adapters.py` with an abstract
  interface for SDK adapters. `AsyncAPIClient` should be designed to potentially
  delegate calls to these adapters.
- **Due to missing `binary_message.py`**: Define a conceptual `BinaryMessage`
  structure in `primitives.py` for `AsyncAPIClient` to handle binary data.

### 3.5. `lionfuncs.errors`

(Source: Define new errors. Integrate SDK errors conceptually as
`/.khive/dev/transport/sdk_errors.py` was missing.)

**File:** `src/lionfuncs/errors.py`

**Public API (`__all__`):**

- `LionError(Exception)`: Base exception for the package.
- `LionFileError(LionError)`: For file system operation errors.
- `LionNetworkError(LionError)`: For network operation errors (e.g., connection
  issues, non-HTTP errors).
  - `APIClientError(LionNetworkError)`: Base for HTTP client errors from
    `AsyncAPIClient`.
  - `APIConnectionError(APIClientError)`
  - `APITimeoutError(APIClientError)`
  - `RateLimitError(APIClientError)`
  - `AuthenticationError(APIClientError)`
  - `ResourceNotFoundError(APIClientError)`
  - `ServerError(APIClientError)`
  - `CircuitBreakerOpenError(LionNetworkError)`
- `LionConcurrencyError(LionError)`: For concurrency primitive errors.
  - `QueueStateError(LionConcurrencyError)` (from `BoundedQueue` in
    `concurrency.py`)
- `LionSDKError(LionError)`: Base for errors originating from SDK interactions.
  (Conceptual, as `sdk_errors.py` was missing). Specific SDK errors would
  inherit from this.

**Refactoring Notes:**

- Define the new error hierarchy.
- `APIClientError` and its subclasses are already defined within
  `AsyncAPIClient` in `concurrency.py`; these will be moved here and made part
  of the public API.
- `CircuitBreakerOpenError` from `concurrency.py` will be moved here.
- `QueueStateError` from `concurrency.py` will be moved here.
- **Due to missing `sdk_errors.py`**: The `LionSDKError` will be a new base
  class. The Implementer will need to define specific SDK error wrappers (e.g.,
  `OpenAISDKError`, `AnthropicSDKError`) that inherit from `LionSDKError` and
  potentially wrap original SDK exceptions if direct integration of
  `sdk_errors.py` content is not possible.

### 3.6. `lionfuncs.utils`

(Source: Refactor from `/.khive/dev/concurrency.py` and
`/.khive/dev/telemetry/config.py` - though `telemetry/config.py` was not
explicitly provided for review, the issue mentions the functions.)

**File:** `src/lionfuncs/utils.py`

**Public API (`__all__`):**

- `is_coro_func(func: Callable) -> bool`: Checks if a function is a coroutine
  function.
- `force_async(func: Callable[..., T]) -> Callable[..., Awaitable[T]]`: Wraps a
  sync function to run in a thread pool.
- `get_env_bool(var_name: str, default: bool = False) -> bool`: Gets boolean
  environment variable.
- `get_env_dict(var_name: str, default: dict | None = None) -> dict | None`:
  Gets dictionary environment variable.

**Refactoring Notes:**

- Move `is_coro_func` (or its equivalent `is_coroutine_function`) and
  `force_async` from `concurrency.py` (specifically, its `.util` import).
- Implement `get_env_bool` and `get_env_dict`. The source for these was
  mentioned as `telemetry/config.py` but not provided. If unavailable, these
  will be new implementations based on standard environment variable parsing
  (e.g., using `os.getenv` and appropriate type casting/JSON parsing).

## 4. Potential Challenges & Design Decisions

1. **Missing `transport` Files (`adapter.py`, `sdk_errors.py`,
   `binary_message.py`):**
   - **Challenge:** The inability to review these files means the design for SDK
     adapter integration, specific SDK error handling, and binary message
     formats within `lionfuncs.network` and `lionfuncs.errors` is conceptual.
   - **Decision/Mitigation:**
     - For SDK adapters, define a clear `AbstractSDKAdapter` protocol/interface
       in `lionfuncs.network.adapters`. `AsyncAPIClient` will be designed to use
       this interface. Specific adapters (`OpenAIAdapter`, `AnthropicAdapter`)
       will need to be implemented against this interface.
     - For `BinaryMessage`, define its role and a potential structure within
       `lionfuncs.network.primitives` for handling non-JSON payloads.
     - For SDK errors, create a base `LionSDKError` in `lionfuncs.errors`.
       Specific SDK error classes will inherit from this and will need to be
       implemented to wrap actual errors from the respective SDKs.
     - This will be highlighted to the Implementer.

2. **Dependency Management (`anyio`, `pynector`):**
   - **Challenge:** The existing `concurrency.py` uses `anyio` (for
     `CancelScope`, `TaskGroup`, `Lock`, `Semaphore`, etc.) often via a
     `pynector` library. It needs to be decided if `lionfuncs` will take a
     direct dependency on `anyio` and/or `pynector`, or if these primitives
     should be re-implemented or wrapped more abstractly.
   - **Decision:** For core concurrency primitives (`Lock`, `Semaphore`,
     `Event`, `Condition`, `CancelScope`, `TaskGroup`), it is recommended to use
     `anyio` directly if it's an acceptable dependency for `lionfuncs`. This
     leverages a well-tested library. If `anyio` is not desired, these
     primitives would need to be re-implemented using `asyncio` primitives,
     which would be a significant effort. `pynector` seems to be an internal
     library; its direct use might be avoided in `lionfuncs` unless it's also
     intended to be a public/shared library. The TDS will assume `anyio` can be
     a dependency for now, and wrappers will be thin.

3. **API for `list_files` vs. `dir_to_files`:**
   - **Challenge:** Issue #2 lists both. `dir_to_files` in existing code is
     recursive.
   - **Decision:** `dir_to_files` will be the recursive version. `list_files`
     will be implemented to list files non-recursively in the specified
     directory by default, with an optional `recursive: bool` parameter. This
     provides flexibility.

4. **`FileUtil` Class:**
   - **Challenge:** `file.py` has a `FileUtil` class with static methods. Issue
     #2 emphasizes a functional API.
   - **Decision:** The primary public API for `lionfuncs.file_system` will be
     functional, with functions directly importable. The `FileUtil` class will
     be deprecated or kept as an internal utility, not part of the main public
     API.

5. **Source for `get_env_bool`, `get_env_dict`:**
   - **Challenge:** Issue #2 mentions these come from `telemetry/config.py`,
     which was not provided for review.
   - **Decision:** These will be implemented in `lionfuncs.utils` using standard
     Python `os.getenv` and appropriate parsing (e.g., for boolean: check
     against 'true', '1', 'yes'; for dict: `json.loads`).

## 5. Risks and Mitigations

1. **Risk:** Implementation of SDK adapters and specific SDK error handling in
   `lionfuncs.network` and `lionfuncs.errors` may deviate from original intent
   due to missing `adapter.py` and `sdk_errors.py`.
   - **Mitigation:** The TDS proposes clear interfaces (`AbstractSDKAdapter`,
     `LionSDKError` base). The Implementer will need to create concrete
     implementations based on these interfaces and the requirements of the
     specific SDKs (OpenAI, Anthropic). Close collaboration with the original
     authors or further research might be needed if specific nuanced behaviors
     from the missing files were critical.

2. **Risk:** Re-implementing or choosing alternatives for `anyio`/`pynector`
   primitives could introduce bugs or inconsistencies if not done carefully.
   - **Mitigation:** Strongly recommend using `anyio` as a direct dependency for
     its robust and tested concurrency primitives. If not possible, a very
     careful re-implementation or selection of alternative asyncio-native
     patterns will be required, with thorough testing.

3. **Risk:** The exact behavior of `is_coro_func` (imported as
   `is_coroutine_function` from `.util` or `.concurrency.util` in
   `concurrency.py`) needs to be ensured if reimplemented or sourced
   differently.
   - **Mitigation:** The standard library `inspect.iscoroutinefunction` should
     be used, which is likely what the original utility wrapped. This will be
     used in `lionfuncs.utils`.

## 6. Open Questions

1. Should `anyio` be a direct dependency of `lionfuncs` for concurrency
   primitives? (Recommended: Yes)
2. If `anyio` is not a direct dependency, which specific `asyncio` patterns
   should be used to replicate `CancelScope`, `TaskGroup`, `Lock`, `Semaphore`,
   `Event`, `Condition`?
3. Are there any other sources or versions of the missing `transport` files
   (`adapter.py`, `sdk_errors.py`, `binary_message.py`) that can be provided?
4. What is the expected behavior of `lionfuncs.file_system.list_files()`
   regarding recursion if `dir_to_files()` is also present for recursive
   listing? (Proposed: `list_files` non-recursive by default, `dir_to_files`
   explicitly recursive).

## 7. Search Evidence

- Design decisions are primarily based on GitHub Issue #2 and analysis of
  provided source code (`/.khive/dev/concurrency.py`, `/.khive/dev/file.py`).
- (pplx:...) If specific algorithms or patterns for missing components (e.g.,
  SDK adapter design) were researched, citations would be added here. For now,
  the design relies on common practices and the issue's guidance.

---

This TDS will be committed to the `feature/2-lionfuncs-design` branch.
