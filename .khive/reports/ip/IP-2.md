---
title: "Implementation Plan: lionfuncs Package (Issue #2)"
by: khive-implementer
created: 2025-05-19
updated: 2025-05-19
version: 1.0
doc_type: IP
output_subdir: ip
description: Detailed implementation plan for the lionfuncs package.
date: 2025-05-19
issue_id: 2
---

# Guidance

**Purpose** Plan out the entire coding effort before writing code. Clarify
**phases**, **tasks**, dependencies, test strategy, and acceptance criteria.

**When to Use**

- After design is approved, before actual implementation starts.

**Best Practices**

- Include TDD approach details (e.g., required test coverage).
- Provide a clear sequence of tasks.
- Reference external docs or prior designs.

---

# Implementation Plan: `lionfuncs` Package

## 1. Overview

### 1.1 Component Purpose

The `lionfuncs` Python package aims to provide a core set of reusable utilities
for asynchronous operations, file system interactions, network calls,
concurrency management, error handling, and general utilities. It will be
located at `src/lionfuncs/`. This implementation directly addresses the
requirements outlined in GitHub Issue #2 and the approved Technical Design
Specification (TDS-2.md).

### 1.2 Design Reference

- **Technical Design Specification:** `.khive/reports/tds/TDS-2.md` (Version
  1.0, Approved)
- **GitHub Issue:**
  [https://github.com/khive-ai/lionfuncs/issues/2](https://github.com/khive-ai/lionfuncs/issues/2)
- **Code Review Report (for TDS):** `.khive/reports/crr/CRR-2.md`

### 1.3 Implementation Approach

The implementation will follow a Test-Driven Development (TDD) methodology. For
each module and its public API functions/classes:

1. Write failing unit tests that cover the expected behavior, edge cases, and
   error conditions.
2. Implement the functionality to make the tests pass.
3. Refactor the code for clarity, performance, and maintainability while
   ensuring tests continue to pass.

The package structure and module contents will adhere strictly to `TDS-2.md`.
Code from `/.khive/dev/concurrency.py` and `/.khive/dev/file.py` will be
refactored and integrated. Conceptual components from `/.khive/dev/transport/`
(SDK adapters, SDK errors, BinaryMessage), whose source files were missing, will
be implemented based on the specifications in TDS-2.md.

An overall test coverage target of >80% will be aimed for.

## 2. Implementation Phases

### 2.1 Phase 1: Core Structure, `utils`, and `errors` Modules

**Description:** Establish the basic package structure, implement the
`lionfuncs.utils` module, and define the custom error hierarchy in
`lionfuncs.errors`.

**Key Deliverables:**

- `src/lionfuncs/__init__.py` (initial setup)
- `src/lionfuncs/utils.py` with `is_coro_func`, `force_async`, `get_env_bool`,
  `get_env_dict`.
- `src/lionfuncs/errors.py` with `LionError`, `LionFileError`,
  `LionNetworkError` (and its children like `APIClientError`),
  `LionConcurrencyError` (and `QueueStateError`), `LionSDKError`.
- Unit tests for all implemented functions and error classes in `utils` and
  `errors`.

**Dependencies:**

- None external to standard Python.

**Estimated Complexity:** Low

### 2.2 Phase 2: `file_system` Module

**Description:** Implement the `lionfuncs.file_system` module, including its
`core` and `media` submodules. Refactor from `/.khive/dev/file.py`.

**Key Deliverables:**

- `src/lionfuncs/file_system/__init__.py`
- `src/lionfuncs/file_system/core.py` with `chunk_content`, `read_file`,
  `save_to_file`, `list_files`, `concat_files`, `dir_to_files`.
- `src/lionfuncs/file_system/media.py` with `read_image_to_base64`,
  `pdf_to_images`.
- Unit tests for all `file_system` functionalities.

**Dependencies:**

- `lionfuncs.errors`
- Potentially `Pillow` for `pdf_to_images` (if not using a CLI tool like
  `pdftoppm`). This needs to be added to `pyproject.toml`. (Search:
  pplx-python-pdf-to-images-library) - `pdf2image` library seems a good
  candidate.

**Estimated Complexity:** Medium

### 2.3 Phase 3: `concurrency` Module

**Description:** Implement the `lionfuncs.concurrency` module. Refactor from
`/.khive/dev/concurrency.py`.

**Key Deliverables:**

- `src/lionfuncs/concurrency.py` with `BoundedQueue`, `WorkQueue`, and internal
  primitives (`Lock`, `Semaphore`, `CapacityLimiter`, `Event`, `Condition` -
  likely wrappers around `anyio`).
- Unit tests for `BoundedQueue` and `WorkQueue`.

**Dependencies:**

- `lionfuncs.errors`
- `anyio` (as per TDS recommendation). This needs to be added to
  `pyproject.toml`.

**Estimated Complexity:** Medium

### 2.4 Phase 4: `async_utils` Module

**Description:** Implement the `lionfuncs.async_utils` module. Refactor from
`/.khive/dev/concurrency.py`.

**Key Deliverables:**

- `src/lionfuncs/async_utils.py` with `alcall`, `bcall`, `@max_concurrent`,
  `@throttle`, `parallel_map`, and internal/advanced `CancelScope`, `TaskGroup`
  (wrappers for `anyio`).
- Unit tests for all public API functions and decorators.

**Dependencies:**

- `lionfuncs.errors`, `lionfuncs.concurrency`
- `anyio`

**Estimated Complexity:** Medium-High

### 2.5 Phase 5: `network` Module (Core Client & Resilience)

**Description:** Implement the core `AsyncAPIClient` and resilience patterns
(`@circuit_breaker`, `@with_retry`) in the `lionfuncs.network` module.

**Key Deliverables:**

- `src/lionfuncs/network/__init__.py`
- `src/lionfuncs/network/client.py` with `AsyncAPIClient`.
- `src/lionfuncs/network/resilience.py` with `@circuit_breaker`, `@with_retry`,
  and their backing classes.
- `src/lionfuncs/network/primitives.py` (initial parts like `Endpoint`,
  `EndpointConfig`, `HeaderFactory`).
- Unit tests for `AsyncAPIClient` (mocking HTTP calls), circuit breaker, and
  retry decorators.

**Dependencies:**

- `lionfuncs.errors`
- `httpx` (for `AsyncAPIClient`). This needs to be added to `pyproject.toml`.
- `anyio`

**Estimated Complexity:** High

### 2.6 Phase 6: `network` Module (SDK Adapters & `BinaryMessage`)

**Description:** Implement the conceptual SDK adapters and `BinaryMessage`
within the `lionfuncs.network` module.

**Key Deliverables:**

- `src/lionfuncs/network/adapters.py` with `AbstractSDKAdapter`,
  `OpenAIAdapter`, `AnthropicAdapter` (conceptual implementations as per TDS).
- `src/lionfuncs/network/primitives.py` with `BinaryMessage` (conceptual
  implementation).
- Update `AsyncAPIClient` to potentially use adapters.
- Define specific `LionSDKError` subclasses in `lionfuncs.errors` (e.g.,
  `OpenAISDKError`).
- Unit tests for the adapter interfaces and conceptual `BinaryMessage` handling.

**Dependencies:**

- `lionfuncs.errors`, `lionfuncs.network.client`
- Potentially `openai` and `anthropic` client libraries if actual calls are to
  be wrapped (though TDS implies conceptual for now).

**Estimated Complexity:** Medium

### 2.7 Phase 7: Integration, Final Testing, and Documentation Polish

**Description:** Integrate all modules, perform final integration testing,
ensure test coverage, and polish any inline documentation.

**Key Deliverables:**

- Fully integrated `lionfuncs` package.
- Achieved >80% test coverage.
- Docstrings and type hints for all public APIs.

**Dependencies:**

- All previous phases completed.

**Estimated Complexity:** Medium

## 3. Test Strategy

Refer to `TI-2.md` (Test Intent document) for a detailed test strategy. The
general approach includes:

- **Unit Tests:** For each function and class, covering happy paths, edge cases,
  and error handling. Pytest will be used. Mocks will be used for external
  dependencies (e.g., network calls, file system interactions where
  appropriate).
- **Integration Tests (Lightweight):** Where modules interact significantly
  (e.g., `AsyncAPIClient` using `lionfuncs.errors`), light integration tests
  will be considered.
- **Coverage:** Aim for >80% line and branch coverage, measured using
  `coverage.py`.

## 4. Implementation Tasks

(Detailed task breakdown will be managed within each phase, this is a high-level
overview)

| ID   | Task                                          | Module(s) Involved  | Dependencies                     | Priority | Complexity |
| ---- | --------------------------------------------- | ------------------- | -------------------------------- | -------- | ---------- |
| T-1  | Setup project structure & `__init__` files    | All                 | -                                | High     | Low        |
| T-2  | Implement `lionfuncs.utils`                   | `utils`             | -                                | High     | Low        |
| T-3  | Implement `lionfuncs.errors`                  | `errors`            | -                                | High     | Low        |
| T-4  | Implement `lionfuncs.file_system.core`        | `file_system`       | `errors`                         | High     | Medium     |
| T-5  | Implement `lionfuncs.file_system.media`       | `file_system`       | `errors`, `pdf2image`            | High     | Medium     |
| T-6  | Implement `lionfuncs.concurrency`             | `concurrency`       | `errors`, `anyio`                | High     | Medium     |
| T-7  | Implement `lionfuncs.async_utils`             | `async_utils`       | `errors`, `concurrency`, `anyio` | High     | Med-High   |
| T-8  | Implement `lionfuncs.network` (client)        | `network`           | `errors`, `httpx`, `anyio`       | High     | High       |
| T-9  | Implement `lionfuncs.network` (resilience)    | `network`           | `errors`, `anyio`                | High     | Medium     |
| T-10 | Implement `lionfuncs.network` (adapters)      | `network`, `errors` | `network.client`                 | Medium   | Medium     |
| T-11 | Implement `lionfuncs.network` (BinaryMessage) | `network`           | `network.client`                 | Medium   | Low        |
| T-12 | Write all unit tests                          | All                 | Corresponding implementations    | High     | Med-High   |
| T-13 | Integration and coverage check                | All                 | All tests written                | High     | Medium     |
| T-14 | Add dependencies to `pyproject.toml`          | Build System        | -                                | High     | Low        |

## 5. Implementation Sequence

```mermaid
gantt
    title lionfuncs Package Implementation Sequence
    dateFormat YYYY-MM-DD

    section Phase 1: Core, Utils, Errors
    Setup Structure           :p1_t1, 2025-05-20, 1d
    Implement Utils           :p1_t2, after p1_t1, 2d
    Implement Errors          :p1_t3, after p1_t1, 2d
    Tests for Utils/Errors    :p1_t4, after p1_t3, 2d
    Add pyproject deps (initial):p1_t5, after p1_t1, 1d


    section Phase 2: File System
    Implement FS Core         :p2_t1, after p1_t4, 3d
    Implement FS Media        :p2_t2, after p2_t1, 2d
    Tests for FS              :p2_t3, after p2_t2, 3d
    Add pdf2image dep         :p2_t4, during p2_t2, 1d

    section Phase 3: Concurrency
    Implement Concurrency     :p3_t1, after p2_t3, 3d
    Tests for Concurrency     :p3_t2, after p3_t1, 2d
    Add anyio dep             :p3_t3, during p3_t1, 1d

    section Phase 4: Async Utils
    Implement Async Utils     :p4_t1, after p3_t2, 4d
    Tests for Async Utils     :p4_t2, after p4_t1, 3d

    section Phase 5: Network (Client & Resilience)
    Implement Network Client  :p5_t1, after p4_t2, 4d
    Implement Resilience      :p5_t2, after p5_t1, 3d
    Tests for Net Client/Res  :p5_t3, after p5_t2, 4d
    Add httpx dep             :p5_t4, during p5_t1, 1d

    section Phase 6: Network (Adapters & BinaryMessage)
    Implement Adapters (concept):p6_t1, after p5_t3, 2d
    Implement BinaryMsg (concept):p6_t2, after p6_t1, 1d
    Tests for Adapters/BinaryMsg:p6_t3, after p6_t2, 2d

    section Phase 7: Integration & Polish
    Final Integration & Tests :p7_t1, after p6_t3, 3d
    Coverage Checks & Polish  :p7_t2, after p7_t1, 2d
```

## 6. Acceptance Criteria

Refer to `TDS-2.md` for detailed API specifications.

| ID   | Criterion                                                                    | Validation Method                   |
| ---- | ---------------------------------------------------------------------------- | ----------------------------------- |
| AC-1 | All public APIs defined in TDS-2.md are implemented.                         | Code review, Unit Tests             |
| AC-2 | All refactoring from `/.khive/dev/` files is completed as per TDS-2.md.      | Code review                         |
| AC-3 | Conceptual components (SDK Adapters, BinaryMessage, SDK Errors) are defined. | Code review                         |
| AC-4 | Unit test coverage is >80%.                                                  | `coverage report`                   |
| AC-5 | All implemented code passes pre-commit checks.                               | `uv run pre-commit run --all-files` |
| AC-6 | Package is installable and basic imports work.                               | Manual check / Simple test script   |

## 7. Test Implementation Plan

A separate `TI-2.md` (Test Intent) document will be created to detail the
testing strategy.

## 8. Implementation Risks and Mitigations

| Risk                                                                 | Impact | Likelihood | Mitigation                                                                                                                                                                |
| -------------------------------------------------------------------- | ------ | ---------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Underestimation of refactoring complexity from `/.khive/dev/` files. | Medium | Medium     | Allocate sufficient time for understanding and refactoring. Break down refactoring into smaller, testable chunks.                                                         |
| Difficulty in implementing conceptual components accurately.         | Medium | Medium     | Focus on the interfaces defined in TDS-2.md. Implement minimal viable versions first. Seek clarification if ambiguity arises. (Search: pplx-interface-driven-development) |
| `anyio` integration challenges or unexpected behavior.               | Medium | Low        | Rely on `anyio`'s official documentation. Test `anyio`-dependent wrappers thoroughly. (Search: pplx-anyio-best-practices)                                                 |
| Achieving >80% test coverage proves difficult for some modules.      | Low    | Medium     | Prioritize testing critical paths. If specific areas are hard to test, document reasons and discuss with reviewer/architect.                                              |
| Missing `pdf2image` or `httpx` dependencies in `pyproject.toml`.     | Low    | Low        | Add dependencies to `pyproject.toml` early in the respective phase and run `uv sync`.                                                                                     |

## 9. Dependencies and Environment

### 9.1 External Libraries (to be added to `pyproject.toml`)

| Library          | Version (approx) | Purpose                                                         | Module(s)                               |
| ---------------- | ---------------- | --------------------------------------------------------------- | --------------------------------------- |
| `anyio`          | ^4.0             | Core async/concurrency primitives                               | `async_utils`, `concurrency`, `network` |
| `httpx`          | ^0.27            | Asynchronous HTTP client                                        | `network`                               |
| `pdf2image`      | ^1.17            | PDF to image conversion                                         | `file_system.media`                     |
| `pytest`         | ^8.0             | Testing framework                                               | dev dependency                          |
| `pytest-asyncio` | ^0.23            | Pytest support for asyncio                                      | dev dependency                          |
| `coverage`       | ^7.0             | Test coverage measurement                                       | dev dependency                          |
| `Pillow`         | ^10.0            | Image manipulation (often a dep of pdf2image or used alongside) | `file_system.media` (indirect)          |

### 9.2 Environment Setup

Development will use `uv` for environment and package management as per project
standards.

```bash
# Ensure uv is installed
# In project root:
uv venv # Create/activate .venv
uv sync # Install dependencies from pyproject.toml and uv.lock
# To add new dependencies (example):
# uv add anyio httpx pdf2image
# uv add --dev pytest pytest-asyncio coverage
```

## 10. Additional Resources

### 10.1 Reference Implementation

- `/.khive/dev/concurrency.py` (for `async_utils`, `concurrency`, parts of
  `network`, `utils`)
- `/.khive/dev/file.py` (for `file_system`)

### 10.2 Relevant Documentation

- `anyio` documentation:
  [https://anyio.readthedocs.io/](https://anyio.readthedocs.io/)
- `httpx` documentation:
  [https://www.python-httpx.org/](https://www.python-httpx.org/)
- `pdf2image` documentation:
  [https://github.com/Belval/pdf2image](https://github.com/Belval/pdf2image)
- `pytest` documentation: [https://docs.pytest.org/](https://docs.pytest.org/)

### 10.3 Design Patterns

- Adapter Pattern (for SDK adapters)
- Decorator Pattern (for resilience, e.g., `@throttle`, `@max_concurrent`,
  `@circuit_breaker`, `@with_retry`)
- Test-Driven Development (TDD)
- Interface-based design for conceptual components.
