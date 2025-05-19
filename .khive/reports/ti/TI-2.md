---
title: "Test Intent: lionfuncs Package (Issue #2)"
by: khive-implementer
created: 2025-05-19
updated: 2025-05-19
version: 1.0
doc_type: TI
output_subdir: ti
description: Comprehensive test suite plan for the lionfuncs package.
date: 2025-05-19
issue_id: 2
---

# Guidance

**Purpose** Document the planned and actual test implementation. Clarify unit,
integration, performance, mocking details, and test data.

**When to Use**

- Before/during writing tests, especially if it’s a large feature or
  microservice.
- As a blueprint to ensure coverage is complete.

**Best Practices**

- Keep tests short and focused.
- Use mocking for external calls.
- Outline coverage goals.

---

# Test Implementation Plan: `lionfuncs` Package

## 1. Overview

### 1.1 Component Under Test

This document outlines the testing strategy for the `lionfuncs` Python package.
The package includes modules for:

- `lionfuncs.utils`
- `lionfuncs.errors`
- `lionfuncs.file_system` (including `core` and `media` submodules)
- `lionfuncs.concurrency`
- `lionfuncs.async_utils`
- `lionfuncs.network` (including `client`, `resilience`, `adapters`, and
  `primitives`)

The implementation details are specified in `TDS-2.md` and `IP-2.md`.

### 1.2 Test Approach

The primary test approach will be **Unit Testing** following Test-Driven
Development (TDD) principles. Each public function, class, and method will have
dedicated unit tests. Lightweight integration tests may be considered for
interactions between closely coupled components within the `lionfuncs` package
itself, but external service integrations will be mocked at the boundary.

### 1.3 Key Testing Goals

- Verify the correctness of all public API functions and classes as defined in
  `TDS-2.md`.
- Ensure robust error handling for all modules, including the correct raising
  and typing of custom `LionError` exceptions.
- Validate behavior of concurrency primitives and asynchronous utilities under
  various conditions.
- Confirm file system operations (read, write, list, chunk, concat, media
  conversion) work as expected.
- Test network client (`AsyncAPIClient`) functionality, including request
  formation, response parsing, and error handling (with HTTP calls mocked).
- Verify resilience patterns (`@circuit_breaker`, `@with_retry`) behave
  correctly.
- Test conceptual SDK adapters and `BinaryMessage` handling at an interface
  level.
- Achieve >80% overall test coverage (line and branch).

## 2. Test Environment

### 2.1 Test Framework

```python
# pyproject.toml [tool.pytest.ini_options] and [project.optional-dependencies]
pytest
pytest-asyncio # For testing async code
pytest-mock    # For mocker fixture
coverage       # For test coverage measurement
```

### 2.2 Mock Framework

```python
# For Python
unittest.mock # Standard library
pytest-mock   # Provides mocker fixture, often preferred with pytest
```

We will primarily use `pytest-mock` and `unittest.mock`.

### 2.3 Test Database

N/A. The `lionfuncs` package does not directly interact with a database.

## 3. Unit Tests

Unit tests will be organized by module, mirroring the `src/lionfuncs` structure
under a `tests/unit/` directory.

### 3.1 Test Suite: `tests.unit.test_utils`

#### Test Cases for `is_coro_func`

- Purpose: Verify correct identification of coroutine functions.
- Scenarios: Test with regular functions, async functions, lambdas, methods.

#### Test Cases for `force_async`

- Purpose: Verify that sync functions are correctly wrapped to run in a thread
  pool.
- Scenarios: Test with simple sync function, sync function raising an exception.
  Ensure original function's signature and return values are preserved.

#### Test Cases for `get_env_bool`

- Purpose: Verify correct parsing of boolean environment variables.
- Scenarios: Test with 'true', '1', 'yes', 'false', '0', 'no'
  (case-insensitive), missing variable (default value), empty string.

#### Test Cases for `get_env_dict`

- Purpose: Verify correct parsing of JSON string environment variables into
  dicts.
- Scenarios: Test with valid JSON string, invalid JSON string (expect error or
  default), missing variable (default value).

### 3.2 Test Suite: `tests.unit.test_errors`

#### Test Cases for Custom Exceptions

- Purpose: Verify that all custom `LionError` subclasses can be raised and
  caught correctly.
- Scenarios: For each error (e.g., `LionFileError`, `LionNetworkError`,
  `APIClientError`, `LionSDKError`), write a simple test that raises and catches
  it. Verify inheritance.

### 3.3 Test Suite: `tests.unit.test_file_system`

Directory structure: `tests/unit/file_system/test_core.py`,
`tests/unit/file_system/test_media.py`

#### Test Cases for `file_system.core` (e.g., `read_file`, `save_to_file`, `list_files`, `chunk_content`)

- Purpose: Verify core file operations.
- Setup: Use `tmp_path` fixture from pytest to create temporary files and
  directories.
- Scenarios for `read_file`: Read existing file, non-existent file (expect
  `LionFileError`).
- Scenarios for `save_to_file`: Save new file, overwrite existing file.
- Scenarios for `list_files`: List files with/without extension,
  recursive/non-recursive.
- Scenarios for `chunk_content`: Chunk by chars/tokens, different chunk sizes,
  edge cases (empty content).
- Scenarios for `concat_files`: Concatenate multiple files, different file
  types.
- Scenarios for `dir_to_files`: Recursive listing.

#### Test Cases for `file_system.media` (e.g., `read_image_to_base64`, `pdf_to_images`)

- Purpose: Verify media file operations.
- Setup: Use sample image and PDF files. Mock external libraries like
  `pdf2image` or `Pillow` if direct calls are made, or test wrappers around CLI
  tools.
- Scenarios for `read_image_to_base64`: Valid image, non-existent image,
  corrupted image.
- Scenarios for `pdf_to_images`: Valid PDF, multi-page PDF, non-existent PDF.
  Mock the underlying `pdf2image.convert_from_path` call.

### 3.4 Test Suite: `tests.unit.test_concurrency`

#### Test Cases for `BoundedQueue`

- Purpose: Verify queue operations, capacity limits, and state transitions.
- Scenarios: Put/get items, blocking on full/empty queue, `join()`,
  `task_done()`, error states (`QueueStateError`). Test with
  `anyio.CapacityLimiter` if used internally.

#### Test Cases for `WorkQueue`

- Purpose: Verify high-level work queue functionality.
- Scenarios: Similar to `BoundedQueue`, focusing on its specific API.

#### Test Cases for Primitives (`Lock`, `Semaphore`, etc. - if implemented as wrappers)

- Purpose: Verify basic functionality of wrapped `anyio` primitives.
- Scenarios: Acquire/release lock, semaphore, event set/wait.

### 3.5 Test Suite: `tests.unit.test_async_utils`

#### Test Cases for `alcall`, `bcall`

- Purpose: Verify asynchronous calling of functions for lists/batches.
- Scenarios: Test with successful calls, calls raising exceptions, different
  concurrency/retry/throttle settings (mocking underlying mechanisms if
  complex). Test return values (with/without timing).

#### Test Cases for `@max_concurrent`

- Purpose: Verify concurrency limiting decorator.
- Scenarios: Ensure no more than `limit` functions run concurrently. Use
  `anyio.Semaphore` internally and test its usage.

#### Test Cases for `@throttle`

- Purpose: Verify throttling decorator.
- Scenarios: Ensure function calls are spaced by `period`.

#### Test Cases for `parallel_map`

- Purpose: Verify parallel execution of a function over a list of items.
- Scenarios: Test with various numbers of items and `max_concurrency` values.

#### Test Cases for `CancelScope`, `TaskGroup` (if implemented as wrappers)

- Purpose: Verify structured cancellation and task group management.
- Scenarios: Test task creation, cancellation propagation, and group completion
  using wrapped `anyio` features.

### 3.6 Test Suite: `tests.unit.test_network`

Directory structure: `tests/unit/network/test_client.py`,
`tests.unit/network/test_resilience.py`, etc.

#### Test Cases for `AsyncAPIClient` (`network.client`)

- Purpose: Verify HTTP request/response handling, error mapping.
- Setup: Use `pytest-httpx` or `respx` to mock HTTP responses from
  `httpx.AsyncClient`.
- Scenarios: Test GET, POST, PUT, DELETE methods. Test different status codes
  (2xx, 4xx, 5xx) and ensure they map to correct `APIClientError` subclasses.
  Test request/response body serialization/deserialization (JSON,
  `BinaryMessage` concept). Test header handling.

#### Test Cases for Resilience Decorators (`@circuit_breaker`, `@with_retry` in `network.resilience`)

- Purpose: Verify circuit breaker and retry logic.
- Scenarios for `@circuit_breaker`: Test state transitions (CLOSED, OPEN,
  HALF_OPEN), call blocking when open, success/failure thresholds.
- Scenarios for `@with_retry`: Test retries on specific exceptions, backoff
  strategies, max attempts.

#### Test Cases for SDK Adapters (`network.adapters` - Conceptual)

- Purpose: Verify the `AbstractSDKAdapter` interface and conceptual adapter
  behavior.
- Scenarios: Mock the `call` method of `OpenAIAdapter`, `AnthropicAdapter` and
  test that `AsyncAPIClient` can (conceptually) delegate to them. Test mapping
  of SDK-specific errors to `LionSDKError` subclasses.

#### Test Cases for `BinaryMessage` (`network.primitives` - Conceptual)

- Purpose: Verify conceptual handling of binary data.
- Scenarios: Test how `AsyncAPIClient` might use `BinaryMessage` for
  request/response bodies (mocking actual serialization).

## 4. Integration Tests

Lightweight integration tests will focus on interactions _within_ the
`lionfuncs` package. Example:

- Test that `AsyncAPIClient` correctly uses custom error classes from
  `lionfuncs.errors`.
- Test that `alcall` correctly uses `max_concurrent` or `throttle` if they are
  applied to the function being called.

External service calls will be mocked. True end-to-end tests are outside the
scope of this package's unit/integration tests.

## 5. API Tests

N/A directly, as `lionfuncs` is a library, not a service with API endpoints.
Tests for `AsyncAPIClient` will cover its "API" interaction with mocked HTTP
services.

## 6. Error Handling Tests

Covered extensively within each module's unit tests. Specific focus on:

- Raising correct `LionError` subclasses.
- Handling exceptions from dependencies (e.g., `httpx` exceptions in
  `AsyncAPIClient`, `anyio` exceptions in concurrency utils) and wrapping them
  if necessary.

## 7. Performance Tests

Not a primary focus for this initial implementation, but the design includes
performance-conscious elements (`@throttle`, `BoundedQueue`). Basic benchmarks
for critical async utilities like `alcall` or `parallel_map` might be considered
if performance concerns arise during development or review.

## 8. Mock Implementation Details

- `mocker` fixture from `pytest-mock` will be used for most mocking.
- `httpx.Request` and `httpx.Response` will be used with `pytest-httpx` or
  `respx` to mock HTTP interactions for `AsyncAPIClient`.
- For file system tests, `tmp_path` fixture will provide real temporary files,
  reducing the need for extensive fs mocking, but `Path.read_text`,
  `Path.write_text`, `os.listdir` etc. might be mocked for specific edge cases
  or to avoid disk I/O in certain tests.
- `anyio` primitives might be mocked in higher-level utilities if testing the
  utility's logic independent of `anyio`'s detailed behavior is needed.

## 9. Test Data

- Simple JSON payloads for `AsyncAPIClient` tests.
- Sample text files, image files (e.g., small PNG/JPEG), and PDF files for
  `file_system` tests.
- Lists of simple data for `alcall`, `parallel_map` tests.

## 10. Helper Functions

- Fixtures for creating `AsyncAPIClient` instances with mocked
  `httpx.AsyncClient`.
- Fixtures for setting up temporary file structures.
- Helper functions to create common test inputs.

## 11. Test Coverage Targets

- **Overall Line Coverage Target:** >80%
- **Overall Branch Coverage Target:** >80%
- **Critical Modules/Functions (e.g., `AsyncAPIClient`, `BoundedQueue`, core
  `alcall` logic):** Aim for >90% coverage. Coverage reports will be generated
  using `coverage run -m pytest` and `coverage report / coverage html`.

## 12. Continuous Integration

Tests will be run in CI on every push/PR. A typical GitHub Actions workflow:

```yaml
name: Python Package CI

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        python-version: ["3.9", "3.10", "3.11", "3.12"] # As per pyproject.toml

    steps:
      - uses: actions/checkout@v4
      - name: Set up Python ${{ matrix.python-version }}
        uses: actions/setup-python@v5
        with:
          python-version: ${{ matrix.python-version }}
      - name: Install uv
        run: curl -LsSf https://astral.sh/uv/install.sh | sh
      - name: Install dependencies
        run: |
          ~/.cargo/bin/uv venv
          ~/.cargo/bin/uv sync --dev # Install main and dev dependencies
      - name: Run tests with coverage
        run: |
          source .venv/bin/activate
          coverage run -m pytest
          coverage xml
      - name: Upload coverage to Codecov
        uses: codecov/codecov-action@v4
        with:
          token: ${{ secrets.CODECOV_TOKEN }} # Optional: if private repo or for PR comments
          files: ./coverage.xml
          fail_ci_if_error: true
```

## 13. Notes and Caveats

### 13.1 Known Limitations

- Testing conceptual SDK adapters and `BinaryMessage` will be limited to
  interface adherence and basic mocked behavior due to their current conceptual
  nature.
- True performance load testing is out of scope for this phase.

### 13.2 Future Improvements

- Introduce property-based testing with `hypothesis` for more robust input
  validation testing.
- Expand performance benchmarks as the library matures.
