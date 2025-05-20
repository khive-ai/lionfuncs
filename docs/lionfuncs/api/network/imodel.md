---
title: "lionfuncs.network.imodel"
---

# lionfuncs.network.imodel

The `imodel` module provides the iModel class, which uses the Executor for
making rate-limited API calls to model endpoints.

## Classes

### iModel

```python
class iModel
```

Client for interacting with API models using the Executor. The iModel class
provides methods for making API calls to model endpoints, using the Executor for
rate limiting and concurrency control.

#### Constructor

```python
def __init__(
    self,
    endpoint: Endpoint,
    executor: Executor,
)
```

Initialize the iModel.

**Parameters:**

- `executor`: An instance of Executor for making API calls.
- `model_endpoint_config`: Configuration for the model endpoint, either as a
  dictionary or EndpointConfig.

**Raises:**

- `TypeError`: If model_endpoint_config is not a dict or EndpointConfig.

**Example:**

```python
from lionfuncs.network.executor import Executor
from lionfuncs.network.imodel import iModel
from lionfuncs.network.endpoint import Endpoint
from lionfuncs.network.primitives import ServiceEndpointConfig, HttpTransportConfig

# Create an executor
executor = Executor(
    concurrency_limit=5,
    requests_rate=10.0,
    api_tokens_rate=10000.0,
    api_tokens_period=60.0
)

# Create a service endpoint config
config = ServiceEndpointConfig(
    name="openai_chat",
    transport_type="http",
    base_url="https://api.openai.com/v1",
    api_key="your-api-key",
    http_config=HttpTransportConfig(method="POST"),
    default_request_kwargs={"model": "gpt-4"}
)

# Create an endpoint
endpoint = Endpoint(config)

# Create an iModel instance
model = iModel(endpoint, executor)
```

````
#### Methods

##### invoke

```python
async def invoke(
    self,
    request_payload: Any,  # Can be a dict or Pydantic model
    num_api_tokens_needed: int = 0,
    http_path: Optional[str] = None,  # e.g., "v1/chat/completions"
    http_method: Optional[str] = None,  # Overrides ServiceEndpointConfig.http_config.method
    sdk_method_name: Optional[str] = None,  # e.g., "chat.completions.create"
    **additional_request_params: Any,
) -> NetworkRequestEvent
````

Makes a generic call to the configured API endpoint.

**Parameters:**

- `request_payload`: The primary payload for the request (dict or Pydantic
  model).
- `num_api_tokens_needed`: Estimated API tokens this call will consume.
- `http_path`: Specific path for HTTP requests (appended to Endpoint's
  base_url).
- `http_method`: HTTP method (e.g., "GET", "POST"). Overrides Endpoint default.
- `sdk_method_name`: Specific SDK method to call (e.g.,
  "chat.completions.create").
- `**additional_request_params`: Further keyword arguments for the API call,
  merged with/overriding Endpoint's defaults and payload. Can include 'metadata'
  for NetworkRequestEvent.

**Returns:**

- A NetworkRequestEvent tracking the request.

**Example:**

```python
# For HTTP transport
event = await model.invoke(
    request_payload={"messages": [{"role": "user", "content": "Hello!"}]},
    http_path="chat/completions",
    http_method="POST",
    num_api_tokens_needed=10,
    metadata={"request_type": "chat"}
)

# For SDK transport
event = await model.invoke(
    request_payload={"messages": [{"role": "user", "content": "Hello!"}]},
    sdk_method_name="chat.completions.create",
    num_api_tokens_needed=10,
    metadata={"request_type": "chat"}
)

# Wait for completion and check the result
if event.status == RequestStatus.COMPLETED:
    print(f"Response: {event.response_body}")
else:
    print(f"Error: {event.error_message}")
```

##### acompletion

```python
async def acompletion(
    self,
    prompt: str,
    max_tokens: int = 150,
    temperature: float = 0.7,
    num_tokens_to_consume: int = 0,
    **kwargs,
) -> NetworkRequestEvent
```

Make an asynchronous completion request.

**Parameters:**

- `prompt`: The prompt to complete.
- `max_tokens`: Maximum number of tokens to generate.
- `temperature`: Sampling temperature.
- `num_tokens_to_consume`: Number of API tokens this call will consume.
- `**kwargs`: Additional parameters for the completion request.

**Returns:**

- A NetworkRequestEvent tracking the request.

**Raises:**

- `RuntimeError`: If the executor is not running.

**Example:**

```python
# Make a completion request
event = await model.acompletion(
    prompt="Once upon a time",
    max_tokens=100,
    temperature=0.8,
    num_tokens_to_consume=150
)

# Wait for completion and check the result
if event.status == RequestStatus.COMPLETED:
    print(f"Completion: {event.response_body}")
else:
    print(f"Error: {event.error_message}")
```

##### close_session

```python
async def close_session() -> None
```

Close the HTTP session if it exists.

**Example:**

```python
await model.close_session()
```

#### Context Manager

The iModel class supports the async context manager protocol, which
automatically creates an HTTP session when entering the context and closes it
when exiting.

```python
async with iModel(endpoint, executor) as model:
    # Use model here
    event = await model.invoke(request_payload={"prompt": "Hello, world!"})
```

## Internal Implementation

Internally, the iModel class:

1. Maintains an aiohttp.ClientSession for making HTTP requests.
2. Uses the provided Executor to submit API call tasks.
3. Constructs API requests based on the model_endpoint_config.
4. Returns NetworkRequestEvent objects for tracking the status and results of
   API calls.

## Configuration

The iModel is configured through the Endpoint's ServiceEndpointConfig, which can
be configured for either HTTP or SDK transport:

### HTTP Transport Configuration

- `transport_type`: Set to "http"
- `base_url`: Base URL for the API (e.g., "https://api.openai.com/v1")
- `http_config`: Configuration for HTTP transport (method, etc.)
- `default_headers`: Headers to include in all requests
- `default_request_kwargs`: Default parameters for all requests

### SDK Transport Configuration

- `transport_type`: Set to "sdk"
- `sdk_config`: Configuration for SDK transport (provider name, default method)
- `client_constructor_kwargs`: Parameters for SDK client initialization
- `default_request_kwargs`: Default parameters for all SDK method calls

## Usage Example

## Usage Example

```python
import asyncio
from lionfuncs.network.executor import Executor
from lionfuncs.network.imodel import iModel
from lionfuncs.network.endpoint import Endpoint
from lionfuncs.network.primitives import ServiceEndpointConfig, HttpTransportConfig
from lionfuncs.network.events import RequestStatus

async def main():
    # Create an executor
    async with Executor(
        concurrency_limit=5,
        requests_rate=3.0,
        requests_period=1.0,
        api_tokens_rate=10000.0,
        api_tokens_period=60.0
    ) as executor:
        # Create a service endpoint config for OpenAI
        config = ServiceEndpointConfig(
            name="openai_completions",
            transport_type="http",
            base_url="https://api.openai.com/v1",
            api_key="your-api-key",
            http_config=HttpTransportConfig(method="POST"),
            default_request_kwargs={"model": "gpt-3.5-turbo-instruct"}
        )

        # Create an endpoint
        endpoint = Endpoint(config)

        # Create an iModel instance
        config = {
            "base_url": "https://api.openai.com/v1",
            "endpoint": "completions",
            "api_key": "your-api-key",
            "model_name": "gpt-3.5-turbo-instruct",
            "default_headers": {
                "Content-Type": "application/json"
            },
            "kwargs": {
                "model": "gpt-3.5-turbo-instruct"
            }
        }

        async with iModel(executor, config) as model:
            # Make multiple completion requests
            prompts = [
                "Write a short poem about AI",
                "Explain quantum computing in simple terms",
                "List 5 benefits of exercise"
            ]

            events = []
            for prompt in prompts:
                # Using the generic invoke method
                event = await model.invoke(
                    request_payload={
                        "prompt": prompt,
                        "max_tokens": 150,
                        "temperature": 0.7
                    },
                    http_path="completions",
                    num_api_tokens_needed=len(prompt) + 150,  # Estimate token usage
                    metadata={"prompt": prompt}
                )
                events.append((prompt, event))
                print(f"Submitted request for prompt: {prompt[:20]}...")

            # Wait for all requests to complete
            while any(event.status not in [RequestStatus.COMPLETED, RequestStatus.FAILED]
                     for _, event in events):
                await asyncio.sleep(0.1)

            # Process results
            for prompt, event in events:
                print(f"\nPrompt: {prompt}")
                if event.status == RequestStatus.COMPLETED:
                    completion = event.response_body.get("choices", [{}])[0].get("text", "")
                    print(f"Completion: {completion.strip()}")
                else:
                    print(f"Error: {event.error_type} - {event.error_message}")

asyncio.run(main())
```

## Integration with Other Components

The iModel class is designed to work with:

1. **Endpoint**: For managing client creation and lifecycle.
2. **Executor**: For managing API call concurrency and rate limiting.
3. **NetworkRequestEvent**: For tracking the status and results of API calls.
4. **ServiceEndpointConfig**: For configuring the endpoint.

This integration allows for efficient and controlled access to AI model APIs,
with proper rate limiting and concurrency control.
