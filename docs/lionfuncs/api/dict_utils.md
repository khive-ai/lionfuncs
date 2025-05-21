---
title: "lionfuncs.dict_utils"
---

# lionfuncs.dict_utils

The `dict_utils` module provides utilities for advanced dictionary manipulation,
with a focus on fuzzy key matching using string similarity algorithms.

## Functions

### fuzzy_match_keys

```python
def fuzzy_match_keys(
    data_dict: dict[str, Any],
    reference_keys: Sequence[str] | dict[str, Any],
    *,
    threshold: float = 0.8,
    default_method: Literal["levenshtein", "jaro_winkler", "wratio"] = "wratio",
    jaro_winkler_prefix_weight: float = 0.1,
    case_sensitive: bool = False,
    handle_unmatched: Literal["ignore", "raise", "remove", "fill", "force"] = "ignore",
    fill_value: Any = PydanticUndefined,
    fill_mapping: dict[str, Any] | None = None,
    strict: bool = False,
) -> dict[str, Any]
```

Matches dictionary keys fuzzily against reference keys, returning a new
dictionary.

This function validates and corrects dictionary keys based on expected keys
using string similarity. It leverages `rapidfuzz` for efficient similarity
calculations and matching, and can handle exact matches, fuzzy matches, and
various strategies for unmatched keys.

#### Parameters

- **data_dict** (`dict[str, Any]`): The dictionary whose keys need
  validation/correction.
- **reference_keys** (`Sequence[str] | dict[str, Any]`): A sequence (list,
  tuple) of expected key names, or a dictionary from which expected keys will be
  extracted.
- **threshold** (`float`, optional): Minimum similarity score (0.0 to 1.0) for a
  fuzzy match. Defaults to `0.8`.
- **default_method** (`Literal["levenshtein", "jaro_winkler", "wratio"]`,
  optional): String similarity algorithm for fuzzy matching via `rapidfuzz`.
  Options:
  - `"levenshtein"`: Edit distance-based similarity (ratio)
  - `"jaro_winkler"`: Jaro-Winkler similarity
  - `"wratio"`: Weighted ratio (default)
- **jaro_winkler_prefix_weight** (`float`, optional): The prefix weight for
  Jaro-Winkler similarity. Only used if `default_method` is "jaro_winkler".
  Defaults to `0.1`.
- **case_sensitive** (`bool`, optional): If False (default), comparisons are
  case-insensitive. Defaults to `False`.
- **handle_unmatched** (`Literal["ignore", "raise", "remove", "fill", "force"]`,
  optional): Strategy for keys in `data_dict` that don't match any reference
  key:
  - `"ignore"`: Keep unmatched keys in output
  - `"raise"`: Raise ValueError if unmatched keys exist
  - `"remove"`: Remove unmatched keys from output
  - `"fill"`: Fill unmatched expected keys with default value/mapping
  - `"force"`: Combine "fill" and "remove" behaviors

  Defaults to `"ignore"`.
- **fill_value** (`Any`, optional): Value for reference keys not found in
  `data_dict` if `handle_unmatched` is "fill" or "force". Defaults to
  `PydanticUndefined`.
- **fill_mapping** (`dict[str, Any] | None`, optional): Dictionary mapping
  specific reference keys to custom fill values. Defaults to `None`.
- **strict** (`bool`, optional): If True, raise ValueError if any
  `reference_key` is not present in the final corrected dictionary. Defaults to
  `False`.

#### Returns

- `dict[str, Any]`: A new dictionary with keys mapped to reference_keys where
  possible.

#### Raises

- `TypeError`: If input types are invalid.
- `ValueError`: For invalid parameters or if an unmatched key is found when
  `handle_unmatched="raise"`, or if `strict=True` and a reference key is
  missing.
- `ImportError`: If `rapidfuzz` is required for fuzzy matching but not
  installed.

#### Example

```python
from lionfuncs.dict_utils import fuzzy_match_keys
from pydantic_core import PydanticUndefined

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

# Fuzzy matching with typos using wratio (default)
data = {"nmae": "John", "aeg": 30, "ctiy": "New York"}
reference = ["name", "age", "city"]
result = fuzzy_match_keys(data, reference, threshold=0.7)
print(result)  # {'name': 'John', 'age': 30, 'city': 'New York'}

# Using different similarity method
data = {"nmae": "John", "aeg": 30, "ctiy": "New York"}
reference = ["name", "age", "city"]
result = fuzzy_match_keys(
    data,
    reference,
    threshold=0.7,
    default_method="jaro_winkler",
    jaro_winkler_prefix_weight=0.2
)
print(result)  # {'name': 'John', 'age': 30, 'city': 'New York'}

# Handling unmatched keys - remove
data = {"name": "John", "age": 30, "city": "New York", "extra": "value"}
reference = ["name", "age", "city"]
result = fuzzy_match_keys(data, reference, handle_unmatched="remove")
print(result)  # {'name': 'John', 'age': 30, 'city': 'New York'}

# Handling unmatched keys - fill with PydanticUndefined
data = {"name": "John", "age": 30}
reference = ["name", "age", "city", "country"]
result = fuzzy_match_keys(
    data,
    reference,
    handle_unmatched="fill"
)
# Result will have 'city' and 'country' keys with PydanticUndefined values

# Handling unmatched keys - fill with custom mapping
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
    print(f"Error: {e}")  # Error: Strict mode: Missing required reference keys in output: ['city']
```

## Notes

The `dict_utils` module has been refactored to focus specifically on dictionary
key matching functionality. For converting various Python objects to
dictionaries, see the [`to_dict`](./to_dict.md) module.
