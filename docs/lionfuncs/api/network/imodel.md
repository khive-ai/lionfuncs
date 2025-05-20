---
title: "lionfuncs.network.imodel"
---

# lionfuncs.network.imodel

The `imodel` module provides the iModel class, which uses the Executor for making rate-limited API calls to model endpoints.

## Classes

### iModel

```python
class iModel
```

Client for interacting with API models using the Executor. The iModel class provides methods for making API calls to model endpoints, using the Executor for rate limiting and concurrency control.

#### Constructor

```python
def __init__(
    self,
    executor: Executor,
    model_endpoint_config: Union[dict[str, Any], EndpointConfig],
)
```

Initialize the iModel.

**Parameters:**
- `executor`: An instance of Executor for making API calls.
- `model_endpoint_config`: Configuration for the model endpoint, either as a dictionary or EndpointConfig.

**Raises:**
- `TypeError`: If model_endpoint_config is not a dict or EndpointConfig.

**Example:**
```python
from lionfuncs.network.executor import Executor
from lionfuncs.network.imodel import iModel
from lionfuncs.network.primitives import EndpointConfig

# Create an executor
executor = Executor(
    concurrency_limit=5,
    requests_rate=10.0,
    api_tokens_rate=10000.0,
    api_tokens_period=60.0
)

# Create an endpoint config
config = EndpointConfig(
    endpoint="completions",
    base_url="https://api.openai.com/v1",
    api_key="your-api-key",
    model_name="gpt-3.5-turbo"
)

# Create an iModel instance
model = iModel(executor, config)
```

#### Methods

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

The iModel class supports the async context manager protocol, which automatically creates an HTTP session when entering the context and closes it when exiting.

```python
async with iModel(executor, config) as model:
    # Use model here
    event = await model.acompletion("Hello, world!")
```

## Internal Implementation

Internally, the iModel class:

1. Maintains an aiohttp.ClientSession for making HTTP requests.
2. Uses the provided Executor to submit API call tasks.
3. Constructs API requests based on the model_endpoint_config.
4. Returns NetworkRequestEvent objects for tracking the status and results of API calls.

## Configuration

The model_endpoint_config can include the following keys:

- `base_url`: Base URL for the API (e.g., "https://api.openai.com/v1").
- `endpoint`: Endpoint path (e.g., "completions").
- `api_key`: API key for authentication.
- `method`: HTTP method (defaults to "POST").
- `model_name`: Name of the model to use.
- `default_headers`: Additional headers to include in requests.
- `kwargs`: Additional parameters to include in all requests.
- `timeout`: Request timeout in seconds (defaults to 300).

## Usage Example

```python
import asyncio
from lionfuncs.network.executor import Executor
from lionfuncs.network.imodel import iModel
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
                event = await model.acompletion(
                    prompt=prompt,
                    max_tokens=150,
                    temperature=0.7,
                    num_tokens_to_consume=len(prompt) + 150  # Estimate token usage
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

1. **Executor**: For managing API call concurrency and rate limiting.
2. **NetworkRequestEvent**: For tracking the status and results of API calls.
3. **EndpointConfig**: For configuring the model endpoint.

This integration allows for efficient and controlled access to AI model APIs, with proper rate limiting and concurrency control.