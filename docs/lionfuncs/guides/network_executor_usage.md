---
title: "Using the Network Executor and iModel"
---

# Using the Network Executor and iModel

This guide demonstrates how to use the Network Executor and iModel components
for making rate-limited API calls to model endpoints.

## Overview

The `lionfuncs.network` module provides several components for managing API
calls with proper rate limiting, concurrency control, and request tracking:

- **Executor**: Manages a queue of API call tasks, enforces concurrency and rate
  limits.
- **NetworkRequestEvent**: Tracks the lifecycle of API requests.
- **Endpoint**: Manages the creation, configuration, and lifecycle of API
  clients.
- **ServiceEndpointConfig**: Provides comprehensive configuration for API
  endpoints.
- **iModel**: Client for interacting with API models using the Endpoint and
  Executor.

These components work together to provide a robust solution for making API calls
to model endpoints, with features like:

- Configurable concurrency limits
- Request rate limiting
- API token rate limiting
- Request lifecycle tracking
- Detailed logging and error handling

## Basic Setup

### Creating an Executor

The first step is to create an Executor instance with appropriate configuration:

```python
import asyncio
from lionfuncs.network.executor import Executor

async def main():
    # Create an executor with custom settings
    executor = Executor(
        queue_capacity=1000,        # Maximum queue size
        concurrency_limit=10,       # Maximum concurrent requests
        requests_rate=10.0,         # Maximum requests per period
        requests_period=1.0,        # Period in seconds for request rate
        api_tokens_rate=10000.0,    # Maximum API tokens per period
        api_tokens_period=60.0,     # Period in seconds for API token rate
        num_workers=5               # Number of worker coroutines
    )

    # Start the executor
    await executor.start()

    try:
        # Use the executor...
        pass
    finally:
        # Stop the executor when done
        await executor.stop(graceful=True)

# Run the async main function
asyncio.run(main())
```

Alternatively, you can use the executor as an async context manager:

```python
async def main():
    async with Executor(
        concurrency_limit=10,
        requests_rate=10.0,
        requests_period=1.0
    ) as executor:
        # Use the executor...
        pass

asyncio.run(main())
```

### Submitting Tasks to the Executor

You can submit API call tasks directly to the executor:

```python
import aiohttp

async def main():
    async with Executor(concurrency_limit=5) as executor:
        # Define an API call coroutine
        async def fetch_data():
            async with aiohttp.ClientSession() as session:
                async with session.get("https://api.example.com/data") as response:
                    body = await response.json()
                    return response.status, dict(response.headers), body

        # Submit the task to the executor
        event = await executor.submit_task(
            api_call_coroutine=fetch_data,
            endpoint_url="https://api.example.com/data",
            method="GET",
            num_api_tokens_needed=1,
            metadata={"request_type": "data_fetch"}
        )

        # The event is a NetworkRequestEvent instance that tracks the task
        print(f"Task submitted with request_id: {event.request_id}")
        print(f"Current status: {event.status}")

        # Wait for the task to complete
        while event.status not in [RequestStatus.COMPLETED, RequestStatus.FAILED]:
            await asyncio.sleep(0.1)

        # Check the result
        if event.status == RequestStatus.COMPLETED:
            print(f"Success! Status code: {event.response_status_code}")
            print(f"Response body: {event.response_body}")
        else:
            print(f"Failed: {event.error_type} - {event.error_message}")

asyncio.run(main())
```

## Using Endpoint, ServiceEndpointConfig, and iModel

The iModel class provides a higher-level interface for interacting with model
APIs:

```python
import asyncio
from lionfuncs.network.executor import Executor
from lionfuncs.network.imodel import iModel
from lionfuncs.network.endpoint import Endpoint
from lionfuncs.network.primitives import ServiceEndpointConfig, HttpTransportConfig, SdkTransportConfig
from lionfuncs.network.events import RequestStatus

async def main():
    # Create an executor
    async with Executor(
        concurrency_limit=5,
        requests_rate=3.0,
        api_tokens_rate=10000.0,
        api_tokens_period=60.0
    ) as executor:
        # Create a service endpoint configuration for HTTP transport
        http_config = ServiceEndpointConfig(
            name="openai_completions",
            transport_type="http",
            base_url="https://api.openai.com/v1",
            api_key="your-api-key",
            timeout=30.0,
            default_headers={"User-Agent": "lionfuncs/0.1.0"},
            http_config=HttpTransportConfig(method="POST"),
            default_request_kwargs={"model": "gpt-3.5-turbo-instruct"}
        )

        # Create an iModel instance
        async with iModel(endpoint, executor) as model:
            # Make a completion request using the generic invoke method
            event = await model.invoke(
                request_payload={
                    "prompt": "Write a short poem about programming",
                    "max_tokens": 150,
                    "temperature": 0.7
                },
                http_path="completions",
                num_api_tokens_needed=200,  # Estimate of token usage
                metadata={"request_type": "completion"}
            )

            # Wait for completion
            while event.status not in [RequestStatus.COMPLETED, RequestStatus.FAILED]:
                await asyncio.sleep(0.1)

            # Process the result
            if event.status == RequestStatus.COMPLETED:
                completion = event.response_body.get("choices", [{}])[0].get("text", "")
                print(f"Completion:\n{completion.strip()}")
            else:
                print(f"Error: {event.error_type} - {event.error_message}")

asyncio.run(main())
```

### Using SDK Transport

You can also use SDK transport to interact with APIs through their official
SDKs:

```python
# Create a service endpoint configuration for SDK transport
sdk_config = ServiceEndpointConfig(
    name="openai_sdk",
    transport_type="sdk",
    api_key="your-api-key",
    sdk_config=SdkTransportConfig(
        sdk_provider_name="openai",
        default_sdk_method_name="chat.completions.create"
    ),
    client_constructor_kwargs={"organization": "your-org-id"},
    default_request_kwargs={"model": "gpt-4"}
)

# Create an endpoint
endpoint = Endpoint(sdk_config)

# Create an iModel instance
async with iModel(endpoint, executor) as model:
    # Make a chat completion request using the SDK
    event = await model.invoke(
        request_payload={
            "messages": [
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": "Write a short poem about programming"}
            ]
        },
        # sdk_method_name is optional if default_sdk_method_name is set in the config
        num_api_tokens_needed=200  # Estimate of token usage
    )

    # Process the result...
```

### Using the Legacy acompletion Method

For backward compatibility, you can still use the acompletion method:

```python
# Using the acompletion method (which now uses invoke internally)
event = await model.acompletion(
    prompt="Write a short poem about programming",
    max_tokens=150,
    temperature=0.7,
    num_tokens_to_consume=200  # Estimate of token usage
)
```

## Advanced Usage

### Handling Multiple Concurrent Requests

The Executor is designed to handle multiple concurrent requests efficiently:

```python
async def main():
    async with Executor(
        concurrency_limit=10,
        requests_rate=10.0,
        requests_period=1.0
    ) as executor:
        # Define an API call coroutine factory
        def create_api_call(url):
            async def api_call():
                async with aiohttp.ClientSession() as session:
                    async with session.get(url) as response:
                        body = await response.json()
                        return response.status, dict(response.headers), body
            return api_call

        # Submit multiple tasks
        urls = [
            "https://api.example.com/data/1",
            "https://api.example.com/data/2",
            "https://api.example.com/data/3",
            "https://api.example.com/data/4",
            "https://api.example.com/data/5"
        ]

        events = []
        for url in urls:
            event = await executor.submit_task(
                api_call_coroutine=create_api_call(url),
                endpoint_url=url,
                method="GET"
            )
            events.append(event)

        # Wait for all tasks to complete
        while any(event.status not in [RequestStatus.COMPLETED, RequestStatus.FAILED] for event in events):
            await asyncio.sleep(0.1)

        # Process results
        for i, event in enumerate(events):
            if event.status == RequestStatus.COMPLETED:
                print(f"Task {i} completed with status code: {event.response_status_code}")
            else:
                print(f"Task {i} failed: {event.error_type} - {event.error_message}")

asyncio.run(main())
```

### Monitoring Request Lifecycle

The NetworkRequestEvent provides detailed information about the request
lifecycle:

```python
async def main():
    async with Executor(concurrency_limit=5) as executor:
        # Submit a task
        event = await executor.submit_task(
            api_call_coroutine=fetch_data,
            endpoint_url="https://api.example.com/data",
            method="GET"
        )

        # Monitor the request lifecycle
        previous_status = event.status
        while event.status not in [RequestStatus.COMPLETED, RequestStatus.FAILED]:
            if event.status != previous_status:
                print(f"Status changed: {previous_status} -> {event.status}")
                previous_status = event.status

                if event.status == RequestStatus.QUEUED:
                    print(f"Queued at: {event.queued_at}")
                elif event.status == RequestStatus.PROCESSING:
                    print(f"Processing started at: {event.processing_started_at}")
                elif event.status == RequestStatus.CALLING:
                    print(f"API call started at: {event.call_started_at}")

            await asyncio.sleep(0.1)

        # Final status
        print(f"Final status: {event.status}")
        print(f"Completed at: {event.completed_at}")

        # Request logs
        print("\nRequest logs:")
        for log in event.logs:
            print(f"  {log}")

        # Timing information
        if event.queued_at and event.completed_at:
            total_time = (event.completed_at - event.queued_at).total_seconds()
            print(f"\nTotal time: {total_time:.2f} seconds")

            if event.processing_started_at:
                queue_time = (event.processing_started_at - event.queued_at).total_seconds()
                print(f"Time in queue: {queue_time:.2f} seconds")

            if event.call_started_at and event.processing_started_at:
                processing_time = (event.call_started_at - event.processing_started_at).total_seconds()
                print(f"Processing time (waiting for rate limits): {processing_time:.2f} seconds")

            if event.completed_at and event.call_started_at:
                call_time = (event.completed_at - event.call_started_at).total_seconds()
                print(f"API call time: {call_time:.2f} seconds")

asyncio.run(main())
```

## Best Practices

### Configuring Rate Limits

When configuring rate limits, consider:

1. **API Provider Limits**: Set rate limits based on the API provider's
   documented limits.
2. **Token Bucket Capacity**: For bursty workloads, set a higher bucket capacity
   to allow for bursts of traffic.
3. **Monitoring**: Monitor the logs to see if requests are waiting for rate
   limits, and adjust as needed.

Example configuration for OpenAI API:

```python
executor = Executor(
    # OpenAI allows 3500 RPM for most tiers
    requests_rate=58.0,         # 58 requests per second
    requests_period=1.0,        # 1 second period
    # Token rate for GPT-4 (e.g., 300K TPM)
    api_tokens_rate=5000.0,     # 5000 tokens per second
    api_tokens_period=1.0,      # 1 second period
    # Allow for bursts
    requests_bucket_capacity=100.0,  # Allow bursts of up to 100 requests
    api_tokens_bucket_capacity=10000.0,  # Allow bursts of up to 10K tokens
    # Concurrency
    concurrency_limit=20,       # Maximum concurrent requests
    num_workers=10              # Number of worker coroutines
)
```

### Error Handling

Implement proper error handling for API calls:

```python
async def main():
    async with Executor(concurrency_limit=5) as executor:
        # Submit a task
        event = await executor.submit_task(
            api_call_coroutine=fetch_data,
            endpoint_url="https://api.example.com/data",
            method="GET"
        )

        # Wait for completion
        while event.status not in [RequestStatus.COMPLETED, RequestStatus.FAILED]:
            await asyncio.sleep(0.1)

        # Handle the result
        if event.status == RequestStatus.COMPLETED:
            # Check for API-specific error codes
            if 200 <= event.response_status_code < 300:
                # Success
                print(f"Success: {event.response_body}")
            elif event.response_status_code == 429:
                # Rate limit exceeded
                retry_after = event.response_headers.get("Retry-After", "unknown")
                print(f"Rate limit exceeded. Retry after: {retry_after}")
            elif 400 <= event.response_status_code < 500:
                # Client error
                print(f"Client error: {event.response_status_code} - {event.response_body}")
            elif 500 <= event.response_status_code < 600:
                # Server error
                print(f"Server error: {event.response_status_code} - {event.response_body}")
        else:
            # Handle exception
            if event.error_type == "ClientConnectorError":
                print("Connection error. Check network connectivity.")
            elif event.error_type == "TimeoutError":
                print("Request timed out.")
            else:
                print(f"Error: {event.error_type} - {event.error_message}")
                if event.error_details:
                    print(f"Details: {event.error_details}")

asyncio.run(main())
```

### Resource Cleanup

Always ensure proper cleanup of resources using context managers:

```python
async def main():
    # Create the executor
    executor = Executor(concurrency_limit=5)

    try:
        # Start the executor
        await executor.start()

        # Create the iModel
        model = iModel(executor, config)

        try:
            # Use the model
            event = await model.invoke(request_payload={"prompt": "Hello, world!"})
            # Process the event...

        # The endpoint is still open here, so close it if needed
        await endpoint.close()

asyncio.run(main())
```

Or you can use the Endpoint as a context manager too:

```python
async def main():
    async with Executor(concurrency_limit=5) as executor:
        async with Endpoint(config) as endpoint:
            async with iModel(endpoint, executor) as model:
                # Use the model
                event = await model.invoke(request_payload={"prompt": "Hello, world!"})
                # Process the event...

asyncio.run(main())
```

## Conclusion

The Network Executor and iModel components provide a robust solution for making
rate-limited API calls to model endpoints. By using these components, you can:

- Enforce concurrency and rate limits
- Track the lifecycle of API requests
- Handle errors gracefully
- Efficiently manage resources
- Use both direct HTTP calls and SDK adapters with a unified interface
- Configure endpoints with comprehensive options

For more detailed information, refer to the API documentation:

- [Executor](../api/network/executor.md)
- [Endpoint](../api/network/endpoint.md)
- [ServiceEndpointConfig](../api/network/primitives.md#serviceendpointconfig)
- [NetworkRequestEvent](../api/network/events.md)
- [iModel](../api/network/imodel.md)
