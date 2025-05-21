---
title: "lionfuncs.parsers"
---

# lionfuncs.parsers

The `parsers` module provides robust parsing utilities for various data formats,
with a focus on handling malformed or non-standard input.

## Functions

### fuzzy_parse_json

```python
def fuzzy_parse_json(str_to_parse: str, /) -> JSONOutputType
```

Attempts to parse a JSON-like string into a Python object, trying several common
fixes for non-standard JSON syntax.

The parsing strategy is tiered:

1. Direct parse with `orjson.loads()` (fastest, for valid JSON).
2. Preprocess (comments, Python constants) then `orjson.loads()`.
3. Further clean (quotes, keys, spaces, trailing commas) then `orjson.loads()`.
4. Fix brackets on the cleaned string, then `orjson.loads()`.
5. If `dirtyjson` is available, fallback to it using the preprocessed string, as
   it can handle more complex JavaScript-like "dirtiness".
6. As a last resort, try `dirtyjson` on the absolute original string.

#### Parameters

- **str_to_parse** (`str`): The string suspected to be JSON or JSON-like.

#### Returns

- `JSONOutputType`: The parsed Python object (dict, list, str, int, float, bool,
  or None).

#### Raises

- `TypeError`: If the input `str_to_parse` is not a string.
- `ValueError`: If the input string is empty or contains only whitespace, or if
  all parsing and fixing attempts fail.

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

# Parsing with comments
json_with_comments = '''
{
  // User information
  "name": "John",
  "age": 30,
  /* This is a
     multi-line comment */
  "active": true
}
'''
result = fuzzy_parse_json(json_with_comments)
print(result)  # {'name': 'John', 'age': 30, 'active': True}

# Parsing with unquoted keys
unquoted_keys = '{name: "John", age: 30}'
result = fuzzy_parse_json(unquoted_keys)
print(result)  # {'name': 'John', 'age': 30}

# Parsing with unmatched brackets
unmatched_brackets = '{"name": "John", "items": [1, 2, 3'
result = fuzzy_parse_json(unmatched_brackets)
print(result)  # {'name': 'John', 'items': [1, 2, 3]}

# Severely broken JSON will raise ValueError
try:
    severely_broken = "This is not JSON at all"
    result = fuzzy_parse_json(severely_broken)
except ValueError as e:
    print(f"Error: {e}")  # Will print the error message
```

## Internal Functions

The following functions are used internally by the module and are not part of
the public API:

- `_check_valid_input_str(str_to_parse: str, /) -> None`: Validates that the
  input is a non-empty string.
- `_preprocess_json_string(s: str) -> str`: Initial preprocessing pass that
  removes comments and converts Python constants.
- `_clean_further_json_string(s: str) -> str`: Second cleaning pass that handles
  quotes, keys, spaces, and trailing commas.
- `_fix_json_brackets(str_to_parse: str) -> Union[str, None]`: Attempts to fix
  unmatched brackets/braces in a JSON-like string.

## Type Aliases

- `JSONOutputType = Union[dict[str, Any], list[Any], str, int, float, bool, None]`:
  Type alias for possible JSON parsing output types.

## Dependencies

The module uses the following dependencies:

- `orjson`: Required for fast JSON parsing.
- `dirtyjson`: Optional, used as a fallback for handling severely malformed
  JSON.
