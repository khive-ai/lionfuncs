---
title: "lionfuncs.utils"
---

# lionfuncs.utils

The `utils` module provides general utility functions for the `lionfuncs`
package.

## Functions

### is_coro_func

```python
def is_coro_func(func: Callable[..., Any]) -> bool
```

Checks if a callable is a coroutine function.

This function properly handles wrapped callables (e.g., those wrapped with
`functools.partial`) by unwrapping them to get to the original function.

#### Parameters

- **func** (`Callable[..., Any]`): The callable to check.

#### Returns

- `bool`: `True` if the callable is a coroutine function, `False` otherwise.

#### Example

```python
import asyncio
from lionfuncs.utils import is_coro_func

# Define a regular function
def sync_func():
    return "Hello, World!"

# Define an async function
async def async_func():
    return "Hello, World!"

# Check if they are coroutine functions
print(is_coro_func(sync_func))  # False
print(is_coro_func(async_func))  # True

# Check a wrapped function
from functools import partial
wrapped_async = partial(async_func)
print(is_coro_func(wrapped_async))  # True
```

### force_async

```python
def force_async(func: Callable[..., R]) -> Callable[..., Coroutine[Any, Any, R]]
```

Wraps a synchronous function to be called asynchronously in a thread pool. If
the function is already async, it's returned unchanged.

#### Parameters

- **func** (`Callable[..., R]`): The synchronous or asynchronous function to
  wrap.

#### Returns

- `Callable[..., Coroutine[Any, Any, R]]`: An awaitable version of the function.

#### Example

```python
import asyncio
from lionfuncs.utils import force_async

# Define a regular function
def sync_func(x):
    import time
    time.sleep(1)  # Simulate some work
    return x * 2

# Wrap it to be async
async_func = force_async(sync_func)

# Use it in an async context
async def main():
    result = await async_func(5)
    print(result)  # 10

asyncio.run(main())
```

### get_env_bool

```python
def get_env_bool(var_name: str, default: bool = False) -> bool
```

Gets a boolean environment variable.

True values (case-insensitive): 'true', '1', 'yes', 'y', 'on'. False values
(case-insensitive): 'false', '0', 'no', 'n', 'off'.

#### Parameters

- **var_name** (`str`): The name of the environment variable.
- **default** (`bool`, optional): The default value if the variable is not set
  or is not a recognized boolean. Defaults to `False`.

#### Returns

- `bool`: The boolean value of the environment variable.

#### Example

```python
import os
from lionfuncs.utils import get_env_bool

# Set an environment variable
os.environ["DEBUG"] = "true"

# Get the boolean value
debug = get_env_bool("DEBUG")
print(debug)  # True

# Get a non-existent variable with default
verbose = get_env_bool("VERBOSE", default=True)
print(verbose)  # True
```

### get_env_dict

```python
def get_env_dict(var_name: str, default: dict[Any, Any] | None = None) -> dict[Any, Any] | None
```

Gets a dictionary environment variable (expected to be a JSON string).

#### Parameters

- **var_name** (`str`): The name of the environment variable.
- **default** (`dict[Any, Any] | None`, optional): The default value if the
  variable is not set or is not valid JSON. Defaults to `None`.

#### Returns

- `dict[Any, Any] | None`: The dictionary value of the environment variable or
  the default.

#### Example

```python
import os
from lionfuncs.utils import get_env_dict

# Set an environment variable with a JSON string
os.environ["CONFIG"] = '{"debug": true, "log_level": "info"}'

# Get the dictionary value
config = get_env_dict("CONFIG")
print(config)  # {'debug': True, 'log_level': 'info'}

# Get a non-existent variable with default
settings = get_env_dict("SETTINGS", default={"debug": False})
print(settings)  # {'debug': False}
```

### to_list

```python
def to_list(
    input_: Any,
    /,
    *,
    flatten: bool = False,
    dropna: bool = False,
    unique: bool = False,
    use_values: bool = False,
    flatten_tuple_set: bool = False,
) -> list
```

Convert input to a list with optional transformations.

Transforms various input types into a list with configurable processing options
for flattening, filtering, and value extraction.

#### Parameters

- **input_** (`Any`): Value to convert to list.
- **flatten** (`bool`, optional): If True, recursively flatten nested iterables.
  Defaults to `False`.
- **dropna** (`bool`, optional): If True, remove None and undefined values.
  Defaults to `False`.
- **unique** (`bool`, optional): If True, remove duplicates (requires
  flatten=True). Defaults to `False`.
- **use_values** (`bool`, optional): If True, extract values from
  enums/mappings. Defaults to `False`.
- **flatten_tuple_set** (`bool`, optional): If True, include tuples and sets in
  flattening. Defaults to `False`.

#### Returns

- `list`: Processed list based on input and specified options.

#### Raises

- `ValueError`: If unique=True is used without flatten=True.

#### Example

```python
from lionfuncs.utils import to_list
from enum import Enum

# Basic conversion
print(to_list(1))  # [1]
print(to_list("hello"))  # ['hello']
print(to_list([1, 2, 3]))  # [1, 2, 3]

# Flattening nested lists
nested = [[1, 2], [3, 4]]
print(to_list(nested, flatten=True))  # [1, 2, 3, 4]

# Dropping None values
with_none = [1, None, 2, None, 3]
print(to_list(with_none, dropna=True))  # [1, 2, 3]

# Unique values
duplicates = [1, 2, 2, 3, 3, 3]
print(to_list(duplicates, flatten=True, unique=True))  # [1, 2, 3]

# Using values from enums
class Color(Enum):
    RED = 1
    GREEN = 2
    BLUE = 3

print(to_list(Color, use_values=True))  # [1, 2, 3]

# Using values from dictionaries
d = {"a": 1, "b": 2, "c": 3}
print(to_list(d, use_values=True))  # [1, 2, 3]
```

### to_dict

```python
def to_dict(
    obj: Any,
    *,
    fields: list[str] | None = None,
    exclude: list[str] | None = None,
    by_alias: bool = False,
    exclude_none: bool = False,
    exclude_unset: bool = False,
    exclude_defaults: bool = False,
) -> dict | list | Any
```

Convert various object types to a dictionary representation.

Handles Pydantic models, dataclasses, dictionaries, lists, and other objects.
For Pydantic models, uses model_dump() with appropriate options. For other
types, attempts to convert to a dictionary-like structure.

#### Parameters

- **obj** (`Any`): The object to convert to a dictionary
- **fields** (`list[str] | None`, optional): Optional list of field names to
  include (for Pydantic models). Defaults to `None`.
- **exclude** (`list[str] | None`, optional): Optional list of field names to
  exclude (for Pydantic models). Defaults to `None`.
- **by_alias** (`bool`, optional): Whether to use field aliases (for Pydantic
  models). Defaults to `False`.
- **exclude_none** (`bool`, optional): Whether to exclude None values (for
  Pydantic models). Defaults to `False`.
- **exclude_unset** (`bool`, optional): Whether to exclude unset fields (for
  Pydantic models). Defaults to `False`.
- **exclude_defaults** (`bool`, optional): Whether to exclude fields with
  default values (for Pydantic models). Defaults to `False`.

#### Returns

- `dict | list | Any`: A dictionary representation of the object, or the
  original object if it cannot be converted to a dictionary

#### Raises

- `TypeError`: If the object cannot be converted to a dictionary

#### Example

```python
from lionfuncs.utils import to_dict
from pydantic import BaseModel
from dataclasses import dataclass

# Pydantic model example
class User(BaseModel):
    name: str
    age: int
    email: str | None = None

user = User(name="John", age=30, email="john@example.com")
user_dict = to_dict(user)
print(user_dict)  # {'name': 'John', 'age': 30, 'email': 'john@example.com'}

# With exclude_none option
user.email = None
user_dict = to_dict(user, exclude_none=True)
print(user_dict)  # {'name': 'John', 'age': 30}

# With fields option
user_dict = to_dict(user, fields=["name"])
print(user_dict)  # {'name': 'John'}

# Dataclass example
@dataclass
class Product:
    name: str
    price: float

product = Product(name="Widget", price=19.99)
product_dict = to_dict(product)
print(product_dict)  # {'name': 'Widget', 'price': 19.99}

# Nested structures
nested = {
    "user": user,
    "products": [product, Product(name="Gadget", price=29.99)]
}
nested_dict = to_dict(nested)
print(nested_dict)  # Converts the entire structure recursively
```

## Internal Functions

The following functions are used internally by the module and are not part of
the public API:

- `hash_dict(data: Any) -> int`: Simple hash for dict-like objects for to_list's
  unique functionality.
- `_run_sync_in_executor(func: Callable[..., R], *args: Any, **kwargs: Any) -> R`:
  Helper to run a sync function in the default executor.
