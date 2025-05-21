---
title: "lionfuncs.to_list"
---

# lionfuncs.to_list

The `to_list` module provides utilities for converting various Python objects to
lists, with options for flattening nested structures, removing None values,
ensuring uniqueness, and more.

## Functions

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
) -> list[Any]
```

Converts various input types into a list with optional transformations.

This function handles a wide range of input types, including iterables,
mappings, Pydantic models, and Enums. It provides options for flattening nested
structures, removing None/undefined values, ensuring uniqueness, and extracting
values from Enums/Mappings.

#### Parameters

- **input_** (`Any`): The value to convert to a list.
- **flatten** (`bool`, optional): If True, recursively flattens nested
  iterables, respecting types that should not be flattened (e.g., strings,
  dicts). Defaults to `False`.
- **dropna** (`bool`, optional): If True, removes items that are None or
  PydanticUndefined. Defaults to `False`.
- **unique** (`bool`, optional): If True, removes duplicate items from the list.
  For this to work predictably on nested structures, the list is effectively
  flattened before uniqueness is determined. Requires `flatten=True` if you want
  the initial structure to be flat before uniqueness, otherwise an internal
  flattening pass occurs for the unique logic. Defaults to `False`.
- **use_values** (`bool`, optional): If True, for Enum types, their member
  values are used. For Mapping types, their values are used. Otherwise, the Enum
  members or the Mapping itself is used. Defaults to `False`.
- **flatten_tuple_set** (`bool`, optional): If True and `flatten` is also True,
  tuples, sets, and frozensets will also be flattened. Otherwise, they are
  treated as atomic items during flattening. Defaults to `False`.

#### Returns

- `list[Any]`: A new list, processed according to the specified options.

#### Raises

- `ValueError`: If `unique=True` is specified with `flatten=False` by the
  caller, as per original design for predictable uniqueness on nested items.

#### Example

```python
from lionfuncs.to_list import to_list
from enum import Enum
from pydantic import BaseModel

# Basic usage with different types
print(to_list("hello"))  # ['hello']
print(to_list([1, 2, 3]))  # [1, 2, 3]
print(to_list({"a": 1, "b": 2}))  # [{"a": 1, "b": 2}]
print(to_list({"a": 1, "b": 2}, use_values=True))  # [1, 2]

# Flattening nested structures
nested = [1, [2, 3], [4, [5, 6]]]
print(to_list(nested))  # [1, [2, 3], [4, [5, 6]]]
print(to_list(nested, flatten=True))  # [1, 2, 3, 4, 5, 6]

# Dropping None values
with_none = [1, None, 2, None, 3]
print(to_list(with_none, dropna=True))  # [1, 2, 3]

# Ensuring uniqueness
duplicates = [1, 2, 2, 3, 3, 3]
print(to_list(duplicates, unique=True, flatten=True))  # [1, 2, 3]

# Working with Enums
class Color(Enum):
    RED = "#FF0000"
    GREEN = "#00FF00"
    BLUE = "#0000FF"

print(to_list(Color))  # [<Color.RED: '#FF0000'>, <Color.GREEN: '#00FF00'>, <Color.BLUE: '#0000FF'>]
print(to_list(Color, use_values=True))  # ['#FF0000', '#00FF00', '#0000FF']

# Working with Pydantic models
class User(BaseModel):
    name: str
    age: int

user = User(name="John", age=30)
print(to_list(user))  # [User(name='John', age=30)]

# Complex example with multiple options
complex_data = [
    1,
    [2, 2, None],
    [3, [4, None, 4]],
    None
]
result = to_list(
    complex_data,
    flatten=True,
    dropna=True,
    unique=True
)
print(result)  # [1, 2, 3, 4]
```

## Internal Functions

The following functions are used internally by the module and are not part of
the public API:

- `_initial_conversion_to_list(current_input: Any, use_values_flag: bool) -> list[Any]`:
  Converts various input types to an initial list format.
- `_recursive_process_list(input_list: list[Any], flatten_flag: bool, dropna_flag: bool, skip_flatten_types: tuple[type[Any], ...]) -> list[Any]`:
  Recursively processes list for flattening and dropping None/Undefined values.
