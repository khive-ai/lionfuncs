---
title: "lionfuncs.parsers"
---

# lionfuncs.parsers

The `parsers` module provides robust parsing utilities for various data formats,
with a focus on handling malformed or non-standard input.

## Functions

### fuzzy_parse_json

```python
def fuzzy_parse_json(
    json_string: str,
    *,
    attempt_fix: bool = True,
    strict: bool = False,
    log_errors: bool = False,
) -> Any | None
```

Parse a JSON string with optional fuzzy fixing for common errors.

Attempts to parse a JSON string, with options to fix common formatting issues:

1. First tries to parse the string directly
2. If that fails and attempt_fix=True, tries to fix common issues and parse
   again
3. If all parsing attempts fail, either returns None or raises an exception

#### Parameters

- **json_string** (`str`): The JSON string to parse
- **attempt_fix** (`bool`, optional): Whether to attempt fixing common JSON
  formatting issues. Defaults to `True`.
- **strict** (`bool`, optional): If True, raises exceptions on parsing failures
  instead of returning None. Defaults to `False`.
- **log_errors** (`bool`, optional): If True, logs parsing errors using the
  logging module. Defaults to `False`.

#### Returns

- `Any | None`: The parsed JSON data (dict, list, or primitive types) or None if
  parsing fails and strict=False

#### Raises

- `ValueError`: If the string cannot be parsed and strict=True
- `TypeError`: If json_string is not a string

#### Example

```python
from lionfuncs.parsers import fuzzy_parse_json

# Standard JSON parsing
valid_json = '{"name": "John", "age": 30}'
result = fuzzy_parse_json(valid_json)
print(result)  # {'name': 'John', 'age': 30}

# Parsing with common errors (single quotes, trailing comma)
malformed_json = "{'name': 'John', 'items': [1, 2, 3,], 'active': True}"
result = fuzzy_parse_json(malformed_json)
print(result)  # {'name': 'John', 'items': [1, 2, 3], 'active': True}

# Parsing with Python-style values
python_style = '{"name": "John", "value": None, "active": True}'
result = fuzzy_parse_json(python_style)
print(result)  # {'name': 'John', 'value': None, 'active': True}

# Strict mode will raise exceptions
try:
    severely_broken = "This is not JSON at all"
    result = fuzzy_parse_json(severely_broken, strict=True)
except ValueError as e:
    print(f"Error: {e}")  # Will print the error message

# Without strict mode, it returns None for unparseable input
result = fuzzy_parse_json("This is not JSON at all")
print(result)  # None

# With logging enabled
result = fuzzy_parse_json("{'broken': 'json',}", log_errors=True)
# Will log warnings about parsing issues but still return the fixed result
print(result)  # {'broken': 'json'}
```

## Internal Functions

The following functions are used internally by the module and are not part of
the public API:

- `_fix_json_string(json_string: str) -> str`: Fix common JSON formatting issues
  such as single quotes, trailing commas, and Python-style boolean/null values.
