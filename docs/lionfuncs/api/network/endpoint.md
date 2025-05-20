---
title: "lionfuncs.network.endpoint"
---

# lionfuncs.network.endpoint

The `endpoint` module provides the Endpoint class, which manages the creation,
configuration, and lifecycle of API clients (AsyncAPIClient or SDK Adapters)
based on a ServiceEndpointConfig.

## Classes

### Endpoint

```python
class Endpoint
```

Manages the creation, configuration, and lifecycle of API clients
(AsyncAPIClient or SDK Adapters) based on a ServiceEndpointConfig. It acts as a
factory and context manager for these clients.

#### Constructor

```python
def __init__(self, config: ServiceEndpointConfig)
```

Initialize the Endpoint.

**Parameters:**

- `config`: The configuration defining how to connect to the service.

**Example:**

```python
from lionfuncs.network.endpoint import Endpoint
from lionfuncs.network.primitives import ServiceEndpointConfig, HttpTransportConfig

# Create a configuration for HTTP transport
config = ServiceEndpointConfig(
    name="openai_chat",
    transport_type="http",
    base_url="https://api.openai.com/v1",
    timeout=60.0,
    api_key="your-api-key",
    default_headers={"User-Agent": "lionfuncs/0.1.0"},
    http_config=HttpTransportConfig(method="POST")
)

# Create an endpoint
endpoint = Endpoint(config)
```

#### Methods

##### get_client

```python
async def get_client(self) -> Union[AsyncAPIClient, AbstractSDKAdapter]
```

Provides a configured and ready-to-use client instance. Manages singleton
creation and enters client's async context if applicable.

**Returns:**

- A configured client instance (AsyncAPIClient or AbstractSDKAdapter).

**Raises:**

- `RuntimeError`: If the Endpoint is closed.

**Example:**

```python
# Get a client from the endpoint
client = await endpoint.get_client()

# Use the client
if isinstance(client, AsyncAPIClient):
    response = await client.request("GET", "/models")
else:  # SDK adapter
    response = await client.call("models.list")
```

##### close

```python
async def close(self) -> None
```

Closes the underlying client and marks the Endpoint as closed.

This method is idempotent and can be called multiple times.

**Example:**

```python
# Close the endpoint when done
await endpoint.close()
```

#### Context Manager

The Endpoint class supports the async context manager protocol, which
automatically initializes the client when entering the context and closes it
when exiting.

```python
async with Endpoint(config) as endpoint:
    # Use endpoint here
    client = await endpoint.get_client()
    # Use client...
```

## Implementation Details

The Endpoint class:

1. Lazily creates and configures a client (AsyncAPIClient or SDK adapter) based
   on the ServiceEndpointConfig.
2. Manages the lifecycle of the client, ensuring proper initialization and
   cleanup.
3. Provides thread-safe access to the client through an async lock.
4. Supports both HTTP and SDK transport types.

For HTTP transport, it creates an AsyncAPIClient with the configured base URL,
timeout, headers, and other parameters.

For SDK transport, it uses the create_sdk_adapter factory function to create an
appropriate SDK adapter based on the provider name.

## Integration with Other Components

The Endpoint class is designed to work with:

1. **ServiceEndpointConfig**: For configuring the endpoint.
2. **AsyncAPIClient**: For HTTP transport.
3. **AbstractSDKAdapter**: For SDK transport.
4. **iModel**: Which uses the Endpoint to get a client for making API calls.

This integration allows for a clean separation of concerns:

- ServiceEndpointConfig defines the configuration
- Endpoint manages client creation and lifecycle
- iModel uses the client for making API calls
- Executor handles rate limiting and concurrency
