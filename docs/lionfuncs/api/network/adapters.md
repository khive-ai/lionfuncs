---
title: "lionfuncs.network.adapters"
---

# lionfuncs.network.adapters

The `network.adapters` module provides abstract interfaces and implementations
for SDK adapters, allowing the `AsyncAPIClient` to delegate calls to specific
SDK implementations.

## Protocols

### AbstractSDKAdapter

```python
class AbstractSDKAdapter(Protocol)
```

Protocol defining the interface for SDK adapters.

SDK adapters provide a consistent interface for interacting with different AI
service SDKs (OpenAI, Anthropic, etc.) through a common API.

#### Methods

##### call

```python
async def call(self, method_name: str, **kwargs) -> Any
```

Call a method on the SDK.

- **method_name** (`str`): The name of the method to call.
- **\*\*kwargs**: Additional keyword arguments for the method.

**Returns**:

- `Any`: The result of the method call.

**Raises**:

- `LionSDKError`: If the SDK call fails.

##### close

```python
async def close() -> None
```

Close the SDK client and release resources.

#### Context Manager

`AbstractSDKAdapter` implementations should support the async context manager
protocol (`__aenter__` and `__aexit__`), allowing them to be used with
`async with`:

```python
async with adapter as sdk:
    result = await sdk.call("method_name", **kwargs)
```

## Classes

### BaseSDKAdapter

```python
class BaseSDKAdapter(ABC)
```

Base class for SDK adapters.

This class provides a common implementation for SDK adapters, handling resource
management and error mapping.

#### Constructor

```python
def __init__(self, api_key: str, **kwargs)
```

- **api_key** (`str`): The API key for the service.
- **\*\*kwargs**: Additional keyword arguments for the SDK client.

#### Methods

##### close

```python
async def close(self) -> None
```

Close the SDK client and release resources.

##### _get_client

```python
@abstractmethod
async def _get_client(self) -> Any
```

Get or create the SDK client.

**Returns**:

- `Any`: The SDK client instance.

**Raises**:

- `RuntimeError`: If the client is already closed.

##### call

```python
@abstractmethod
async def call(self, method_name: str, **kwargs) -> Any
```

Call a method on the SDK.

- **method_name** (`str`): The name of the method to call.
- **\*\*kwargs**: Additional keyword arguments for the method.

**Returns**:

- `Any`: The result of the method call.

**Raises**:

- `LionSDKError`: If the SDK call fails.

#### Context Manager

`BaseSDKAdapter` implements the async context manager protocol (`__aenter__` and
`__aexit__`), allowing it to be used with `async with`:

```python
async with adapter as sdk:
    result = await sdk.call("method_name", **kwargs)
```

### OpenAI Adapter

```python
class OpenAIAdapter(BaseSDKAdapter)
```

Adapter for the OpenAI API.

This adapter provides a consistent interface for interacting with the OpenAI API
through the official Python SDK.

#### Constructor

```python
def __init__(self, api_key: str, **kwargs)
```

- **api_key** (`str`): The OpenAI API key.
- **\*\*kwargs**: Additional keyword arguments for the OpenAI SDK client.

#### Methods

##### _get_client

```python
async def _get_client(self) -> Any
```

Get or create the OpenAI SDK client.

**Returns**:

- `Any`: The OpenAI SDK client instance.

**Raises**:

- `RuntimeError`: If the client is already closed.
- `ImportError`: If the OpenAI SDK is not installed.

##### call

```python
async def call(self, method_name: str, **kwargs) -> Any
```

Call a method on the OpenAI SDK.

- **method_name** (`str`): The name of the method to call (e.g.,
  "chat.completions.create").
- **\*\*kwargs**: Additional keyword arguments for the method.

**Returns**:

- `Any`: The result of the method call.

**Raises**:

- `LionSDKError`: If the SDK call fails.

#### Example

```python
import asyncio
import os
from lionfuncs.network import OpenAIAdapter

async def main():
    # Get API key from environment variable
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        print("OPENAI_API_KEY environment variable not set")
        return

    # Create an OpenAI adapter
    adapter = OpenAIAdapter(api_key=api_key)

    # Use the adapter
    async with adapter as sdk:
        try:
            # Call the chat completions API
            response = await sdk.call(
                "chat.completions.create",
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "You are a helpful assistant."},
                    {"role": "user", "content": "Hello, world!"}
                ]
            )
            print(f"OpenAI response: {response}")
        except Exception as e:
            print(f"Error calling OpenAI API: {e}")

asyncio.run(main())
```

### Anthropic Adapter

```python
class AnthropicAdapter(BaseSDKAdapter)
```

Adapter for the Anthropic API.

This adapter provides a consistent interface for interacting with the Anthropic
API through the official Python SDK.

#### Constructor

```python
def __init__(self, api_key: str, **kwargs)
```

- **api_key** (`str`): The Anthropic API key.
- **\*\*kwargs**: Additional keyword arguments for the Anthropic SDK client.

#### Methods

##### _get_client

```python
async def _get_client(self) -> Any
```

Get or create the Anthropic SDK client.

**Returns**:

- `Any`: The Anthropic SDK client instance.

**Raises**:

- `RuntimeError`: If the client is already closed.
- `ImportError`: If the Anthropic SDK is not installed.

##### call

```python
async def call(self, method_name: str, **kwargs) -> Any
```

Call a method on the Anthropic SDK.

- **method_name** (`str`): The name of the method to call (e.g.,
  "messages.create").
- **\*\*kwargs**: Additional keyword arguments for the method.

**Returns**:

- `Any`: The result of the method call.

**Raises**:

- `LionSDKError`: If the SDK call fails.

#### Example

```python
import asyncio
import os
from lionfuncs.network import AnthropicAdapter

async def main():
    # Get API key from environment variable
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        print("ANTHROPIC_API_KEY environment variable not set")
        return

    # Create an Anthropic adapter
    adapter = AnthropicAdapter(api_key=api_key)

    # Use the adapter
    async with adapter as sdk:
        try:
            # Call the messages API
            response = await sdk.call(
                "messages.create",
                model="claude-3-sonnet-20240229",
                messages=[
                    {"role": "user", "content": "Hello, world!"}
                ],
                max_tokens=1000
            )
            print(f"Anthropic response: {response}")
        except Exception as e:
            print(f"Error calling Anthropic API: {e}")

asyncio.run(main())
```

## Functions

### create_sdk_adapter

```python
def create_sdk_adapter(provider: str, api_key: str, **kwargs) -> AbstractSDKAdapter
```

Create an SDK adapter for the specified provider.

#### Parameters

- **provider** (`str`): The provider name (e.g., "openai", "anthropic").
- **api_key** (`str`): The API key for the service.
- **\*\*kwargs**: Additional keyword arguments for the SDK client.

#### Returns

- `AbstractSDKAdapter`: An SDK adapter instance.

#### Raises

- `ValueError`: If the provider is not supported.

#### Example

```python
import asyncio
import os
from lionfuncs.network import create_sdk_adapter

async def main():
    # Get API keys from environment variables
    openai_api_key = os.environ.get("OPENAI_API_KEY")
    anthropic_api_key = os.environ.get("ANTHROPIC_API_KEY")

    # Create adapters using the factory function
    if openai_api_key:
        openai_adapter = create_sdk_adapter("openai", openai_api_key)
        async with openai_adapter as sdk:
            response = await sdk.call(
                "chat.completions.create",
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "You are a helpful assistant."},
                    {"role": "user", "content": "Hello from OpenAI!"}
                ]
            )
            print(f"OpenAI response: {response}")

    if anthropic_api_key:
        anthropic_adapter = create_sdk_adapter("anthropic", anthropic_api_key)
        async with anthropic_adapter as sdk:
            response = await sdk.call(
                "messages.create",
                model="claude-3-sonnet-20240229",
                messages=[
                    {"role": "user", "content": "Hello from Anthropic!"}
                ],
                max_tokens=1000
            )
            print(f"Anthropic response: {response}")

asyncio.run(main())
```

## Implementation Details

### Method Name Resolution

The `call` method in both adapter implementations uses a path-based approach to
resolve nested methods in the SDK client. For example, the method name
"chat.completions.create" is resolved to `client.chat.completions.create`.

### Async Wrapping

The `AnthropicAdapter` implementation includes logic to wrap synchronous SDK
methods in `asyncio.to_thread` if they are not already asynchronous. This
ensures that all SDK calls are non-blocking, even if the underlying SDK is
synchronous.

### Error Handling

Both adapter implementations catch all exceptions from the SDK and wrap them in
a `LionSDKError` with the original exception as the `original_exception`
attribute. This provides a consistent error handling approach across different
SDKs.

### Resource Management

The base class `BaseSDKAdapter` provides common resource management
functionality, including:

1. Lazy initialization of the SDK client
2. Proper cleanup of resources when the adapter is closed
3. Support for the async context manager protocol

### Dependencies

The adapters have optional dependencies on their respective SDK libraries:

- `OpenAIAdapter` requires the `openai` package
- `AnthropicAdapter` requires the `anthropic` package

These dependencies are not installed by default with `lionfuncs`. You need to
install them separately if you want to use the corresponding adapter.
