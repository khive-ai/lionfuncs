---
title: "lionfuncs.dict_utils"
---

# lionfuncs.dict_utils

The `dict_utils` module provides utilities for advanced dictionary manipulation,
including fuzzy key matching and dictionary transformation.

## Functions

### fuzzy_match_keys

```python
def fuzzy_match_keys(
    data_dict: dict[str, Any],
    reference_keys: Sequence[str] | dict[str, Any],
    *,
    threshold: float = 0.8,
    default_method: str = "levenshtein",
    case_sensitive: bool = False,
    handle_unmatched: Literal["ignore", "raise", "remove", "fill", "force"] = "ignore",
    fill_value: Any = None,
    fill_mapping: dict[str, Any] | None = None,
    strict: bool = False,
) -> dict[str, Any]
```

Match dictionary keys against reference keys using string similarity.

Validates and corrects dictionary keys based on expected keys using string
similarity. Can handle exact matches, fuzzy matches, and various strategies for
unmatched keys.

#### Parameters

- **data_dict** (`dict[str, Any]`): The dictionary to validate and correct keys
  for
- **reference_keys** (`Sequence[str] | dict[str, Any]`): List of expected keys
  or dictionary mapping keys to types
- **threshold** (`float`, optional): Minimum similarity score for fuzzy matching
  (0.0 to 1.0). Defaults to `0.8`.
- **default_method** (`str`, optional): String similarity algorithm to use.
  Defaults to `"levenshtein"`.
- **case_sensitive** (`bool`, optional): Whether to consider case when matching.
  Defaults to `False`.
- **handle_unmatched** (`Literal["ignore", "raise", "remove", "fill", "force"]`,
  optional): Specifies how to handle unmatched keys:
  - `"ignore"`: Keep unmatched keys in output
  - `"raise"`: Raise ValueError if unmatched keys exist
  - `"remove"`: Remove unmatched keys from output
  - `"fill"`: Fill unmatched expected keys with default value/mapping
  - `"force"`: Combine "fill" and "remove" behaviors

  Defaults to `"ignore"`.
- **fill_value** (`Any`, optional): Default value for filling unmatched keys.
  Defaults to `None`.
- **fill_mapping** (`dict[str, Any] | None`, optional): Dictionary mapping
  unmatched keys to default values. Defaults to `None`.
- **strict** (`bool`, optional): If True, raise ValueError if any expected key
  is missing. Defaults to `False`.

#### Returns

- `dict[str, Any]`: A new dictionary with validated and corrected keys

#### Raises

- `TypeError`: If input types are invalid
- `ValueError`: If validation fails based on specified parameters

#### Example

```python
from lionfuncs.dict_utils import fuzzy_match_keys

# Basic usage - exact matches
data = {"name": "John", "age": 30, "city": "New York"}
reference = ["name", "age", "city"]
result = fuzzy_match_keys(data, reference)
print(result)  # {'name': 'John', 'age': 30, 'city': 'New York'}

# Fuzzy matching with case differences
data = {"Name": "John", "Age": 30, "City": "New York"}
reference = ["name", "age", "city"]
result = fuzzy_match_keys(data, reference, case_sensitive=False)
print(result)  # {'name': 'John', 'age': 30, 'city': 'New York'}

# Fuzzy matching with typos
data = {"nmae": "John", "aeg": 30, "ctiy": "New York"}
reference = ["name", "age", "city"]
result = fuzzy_match_keys(data, reference, threshold=0.7)
print(result)  # {'name': 'John', 'age': 30, 'city': 'New York'}

# Handling unmatched keys - remove
data = {"name": "John", "age": 30, "city": "New York", "extra": "value"}
reference = ["name", "age", "city"]
result = fuzzy_match_keys(data, reference, handle_unmatched="remove")
print(result)  # {'name': 'John', 'age': 30, 'city': 'New York'}

# Handling unmatched keys - fill
data = {"name": "John", "age": 30}
reference = ["name", "age", "city", "country"]
result = fuzzy_match_keys(
    data,
    reference,
    handle_unmatched="fill",
    fill_mapping={"city": "Unknown", "country": "USA"}
)
print(result)  # {'name': 'John', 'age': 30, 'city': 'Unknown', 'country': 'USA'}

# Strict mode
try:
    data = {"name": "John", "age": 30}
    reference = ["name", "age", "city"]
    result = fuzzy_match_keys(data, reference, strict=True)
except ValueError as e:
    print(f"Error: {e}")  # Error: Missing required keys: {'city'}
```
