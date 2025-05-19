---
title: "Documentation Draft: lionfuncs Package (Issue #2)"
author: "@khive-documenter"
date: "2025-05-19"
version: "1.0"
issue: "https://github.com/khive-ai/lionfuncs/issues/2"
---

# Documentation Plan for lionfuncs Package

## 1. Overview

This document outlines the documentation plan for the `lionfuncs` Python
package, which provides a core set of reusable utilities for asynchronous
operations, file system interactions, network calls, concurrency management,
error handling, and general utilities.

The documentation will be comprehensive, covering all public APIs, installation
instructions, usage examples, and contribution guidelines. It will be structured
to serve both end users of the package and developers who might contribute to
it.

## 2. Documentation Structure

The documentation will be organized as follows:

```
docs/lionfuncs/
├── index.md                     # Overview, installation, quick start
├── api/                         # API reference documentation
│   ├── utils.md                 # lionfuncs.utils module
│   ├── errors.md                # lionfuncs.errors module
│   ├── file_system/             # lionfuncs.file_system module
│   │   ├── index.md             # Overview of file_system module
│   │   ├── core.md              # file_system.core module
│   │   └── media.md             # file_system.media module
│   ├── concurrency.md           # lionfuncs.concurrency module
│   ├── async_utils.md           # lionfuncs.async_utils module
│   └── network/                 # lionfuncs.network module
│       ├── index.md             # Overview of network module
│       ├── client.md            # network.client module
│       ├── resilience.md        # network.resilience module
│       ├── adapters.md          # network.adapters module
│       └── primitives.md        # network.primitives module
├── guides/                      # Usage guides and tutorials
│   ├── async_operations.md      # Guide to async operations with alcall/bcall
│   ├── file_system_utils.md     # Guide to file system utilities
│   ├── network_client.md        # Guide to using AsyncAPIClient
│   └── resilience_patterns.md   # Guide to resilience patterns
└── contributing.md              # Contribution guidelines
```

## 3. Documentation Content

### 3.1 Overview and Installation (index.md)

- Introduction to `lionfuncs`
- Key features and capabilities
- Installation instructions
  - Basic installation: `pip install lionfuncs`
  - Installation with extras: `pip install lionfuncs[media]`
- Quick start examples
- Package structure overview

### 3.2 API Reference

Each module's documentation will include:

- Module overview
- Public API listing
- Detailed documentation for each public function, class, and method, including:
  - Function/method signature
  - Parameter descriptions
  - Return type descriptions
  - Exceptions raised
  - Usage examples
  - Notes and caveats

#### 3.2.1 lionfuncs.utils (utils.md)

- `is_coro_func`: Function to check if a callable is a coroutine function
- `force_async`: Function to wrap a synchronous function to be called
  asynchronously
- `get_env_bool`: Function to get a boolean environment variable
- `get_env_dict`: Function to get a dictionary environment variable
- `to_list`: Function to convert input to a list with optional transformations

#### 3.2.2 lionfuncs.errors (errors.md)

- Error hierarchy diagram
- `LionError`: Base exception for all lionfuncs errors
- `LionFileError`: For file system operation errors
- `LionNetworkError`: For network operation errors
- `APIClientError` and its subclasses
- `LionConcurrencyError` and its subclasses
- `LionSDKError`: Base for errors originating from SDK interactions

#### 3.2.3 lionfuncs.file_system (file_system/index.md, core.md, media.md)

- `chunk_content`: Function to split content by chars or tokens
- `read_file`: Function to read file content
- `save_to_file`: Function to save text to a file
- `list_files`: Function to list files in a directory
- `concat_files`: Function to concatenate multiple files
- `dir_to_files`: Function to recursively list files in a directory
- `read_image_to_base64`: Function to read an image and encode to base64
- `pdf_to_images`: Function to convert PDF pages to images

#### 3.2.4 lionfuncs.concurrency (concurrency.md)

- `BoundedQueue`: Bounded async queue with backpressure support
- `WorkQueue`: High-level wrapper around BoundedQueue
- `QueueStatus`: Enum for queue states
- `QueueConfig`: Configuration for work queues
- Concurrency primitives: `Lock`, `Semaphore`, `CapacityLimiter`, `Event`,
  `Condition`

#### 3.2.5 lionfuncs.async_utils (async_utils.md)

- `alcall`: Function to asynchronously call a function for each item in a list
- `bcall`: Function to asynchronously call a function in batches
- `@max_concurrent`: Decorator to limit the concurrency of an async function
- `@throttle`: Decorator to throttle function execution
- `parallel_map`: Function to apply an async function to each item in a list in
  parallel
- `CancelScope`: Wrapper around anyio.CancelScope for structured cancellation
- `TaskGroup`: Wrapper around anyio.create_task_group for managing groups of
  tasks

#### 3.2.6 lionfuncs.network (network/index.md, client.md, resilience.md, adapters.md, primitives.md)

- `AsyncAPIClient`: Generic async HTTP client for API interactions
- `@circuit_breaker`: Decorator for circuit breaker pattern
- `@with_retry`: Decorator for retry with backoff
- `CircuitBreaker`: Class for implementing the circuit breaker pattern
- `RetryConfig`: Configuration for retry behavior
- `AbstractSDKAdapter`: Protocol defining the interface for SDK adapters
- `OpenAIAdapter`: Adapter for the OpenAI API
- `AnthropicAdapter`: Adapter for the Anthropic API
- `EndpointConfig`: Configuration for an API endpoint
- `Endpoint`: Class for defining and calling specific API endpoints
- `HeaderFactory`: Utility for creating auth/content headers
- Rate limiting classes: `TokenBucketRateLimiter`, `EndpointRateLimiter`,
  `AdaptiveRateLimiter`

### 3.3 Usage Guides

#### 3.3.1 Async Operations Guide (guides/async_operations.md)

- Introduction to asynchronous programming with `lionfuncs`
- Using `alcall` for parallel processing of lists
- Using `bcall` for batch processing
- Controlling concurrency with `@max_concurrent`
- Rate limiting with `@throttle`
- Structured concurrency with `CancelScope` and `TaskGroup`

#### 3.3.2 File System Utilities Guide (guides/file_system_utils.md)

- Reading and writing files asynchronously
- Working with file paths
- Listing and filtering files
- Chunking content for processing
- Working with media files (images, PDFs)

#### 3.3.3 Network Client Guide (guides/network_client.md)

- Making HTTP requests with `AsyncAPIClient`
- Handling authentication and headers
- Working with JSON and binary data
- Using SDK adapters for third-party APIs
- Configuring endpoints

#### 3.3.4 Resilience Patterns Guide (guides/resilience_patterns.md)

- Understanding resilience patterns
- Implementing retry with backoff using `@with_retry`
- Implementing circuit breaker pattern using `@circuit_breaker`
- Rate limiting strategies
- Combining resilience patterns

### 3.4 Contribution Guidelines (contributing.md)

- Setting up the development environment
- Running tests
- Code style and conventions
- Pull request process
- Adding new features or fixing bugs

## 4. Implementation Plan

1. Create the directory structure for the documentation
2. Write the overview and installation documentation
3. Write the API reference documentation for each module
4. Write the usage guides
5. Write the contribution guidelines
6. Review and finalize the documentation
7. Create a pull request for the documentation

## 5. Deliverables

- Complete documentation in Markdown format
- Pull request with the documentation changes

## 6. Timeline

- Documentation Draft (DD-2.md): May 19, 2025
- Complete documentation: May 20, 2025
- Pull request: May 20, 2025

## 7. Notes

- The documentation will be written in Markdown format for easy viewing on
  GitHub and potential conversion to other formats.
- Code examples will be included for all public APIs to demonstrate usage.
- The documentation will be organized to be easily navigable and searchable.
- The documentation will be written with both end users and developers in mind.
