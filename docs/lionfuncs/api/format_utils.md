---
title: "lionfuncs.format_utils"
---

# lionfuncs.format_utils

The `format_utils` module provides utilities for formatting data into
human-readable strings, with support for various output formats and special
handling for Jupyter notebooks.

## Functions

### as_readable

```python
def as_readable(
    data: Any,
    *,
    format_type: str = "auto",
    indent: int = 2,
    max_depth: int | None = None,
    in_notebook_override: bool | None = None,
) -> str
```

Convert data into a human-readable string format.

Formats data in a human-readable way, with options for different formats:

- "yaml_like": A YAML-like format with proper indentation
- "json": JSON format with indentation
- "repr": Python's repr() format
- "auto": Defaults to "yaml_like"

The function automatically detects if it's running in a Jupyter notebook
environment and can adjust the output format accordingly (adding markdown code
blocks).

#### Parameters

- **data** (`Any`): The data to format (can be any type)
- **format_type** (`str`, optional): The format to use ("auto", "yaml_like",
  "json", or "repr"). Defaults to `"auto"`.
- **indent** (`int`, optional): Number of spaces per indentation level. Defaults
  to `2`.
- **max_depth** (`int | None`, optional): Maximum recursion depth for nested
  structures. Defaults to `None`.
- **in_notebook_override** (`bool | None`, optional): Override notebook
  detection (for testing). Defaults to `None`.

#### Returns

- `str`: A formatted string representation of the data

#### Raises

- `ValueError`: If an unsupported format_type is specified

#### Example

```python
from lionfuncs.format_utils import as_readable
from pydantic import BaseModel

# Simple dictionary
data = {
    "name": "John",
    "age": 30,
    "address": {
        "street": "123 Main St",
        "city": "New York",
        "zip": "10001"
    },
    "tags": ["developer", "python", "data science"]
}

# Default YAML-like format
print(as_readable(data))
# Output:
#   name: John
#   age: 30
#   address:
#     street: 123 Main St
#     city: New York
#     zip: 10001
#   tags:
#     - developer
#     - python
#     - data science

# JSON format
print(as_readable(data, format_type="json"))
# Output:
# {
#   "name": "John",
#   "age": 30,
#   "address": {
#     "street": "123 Main St",
#     "city": "New York",
#     "zip": "10001"
#   },
#   "tags": [
#     "developer",
#     "python",
#     "data science"
#   ]
# }

# With max_depth to limit nesting
print(as_readable(data, max_depth=1))
# Output:
#   name: John
#   age: 30
#   address: ...
#   tags: ...

# Works with Pydantic models too
class User(BaseModel):
    name: str
    age: int
    email: str | None = None

user = User(name="Jane", age=28, email="jane@example.com")
print(as_readable(user))
# Output:
#   name: Jane
#   age: 28
#   email: jane@example.com

# Multi-line strings are handled specially
data_with_multiline = {
    "name": "Report",
    "content": "This is a\nmulti-line\nstring"
}
print(as_readable(data_with_multiline))
# Output:
#   name: Report
#   content: |
#     This is a
#     multi-line
#     string
```

## Internal Functions

The following functions are used internally by the module and are not part of
the public API:

- `_is_in_notebook() -> bool`: Check if code is running in a Jupyter notebook
  environment.
- `_format_dict_yaml_like(data_dict: dict, indent_level: int = 0, base_indent: int = 2, max_depth: int | None = None, current_depth: int = 0) -> str`:
  Format a dictionary in a YAML-like readable format.
