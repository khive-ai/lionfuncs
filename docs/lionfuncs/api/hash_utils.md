---
title: "lionfuncs.hash_utils"
---

# lionfuncs.hash_utils

The `hash_utils` module provides utilities for creating deterministic hashes for complex Python data structures, including dictionaries, lists, sets, and Pydantic models.

## Functions

### hash_dict

```python
def hash_dict(data: any, strict: bool = False) -> int
```

Computes a deterministic hash for various Python data structures.

This function creates a stable, deterministic hash for complex data structures including dictionaries, Pydantic BaseModels, lists, tuples, sets, frozensets, and primitives. It's particularly useful for finding unique objects within a collection or implementing caching mechanisms.

The hash is deterministic within the same Python process run (respecting PYTHONHASHSEED for built-in hash behavior on strings, bytes, etc.). It's suitable for tasks like finding unique objects within a collection during a single program execution.

#### Parameters

- **data** (`any`): The Python object to hash.
- **strict** (`bool`, optional): If True, will make a deep copy of the input data to ensure immutability. Defaults to `False`.

#### Returns

- `int`: An integer hash value.

#### Raises

- `TypeError`: If the generated internal representation of the data is not hashable, though this is unlikely with the current implementation.

#### Example

```python
from lionfuncs.hash_utils import hash_dict
from pydantic import BaseModel

# Hashing dictionaries
dict1 = {"a": 1, "b": 2, "c": 3}
dict2 = {"c": 3, "b": 2, "a": 1}  # Same content, different order
dict3 = {"a": 1, "b": 2, "c": 4}  # Different content

print(hash_dict(dict1) == hash_dict(dict2))  # True - order doesn't matter
print(hash_dict(dict1) == hash_dict(dict3))  # False - content differs

# Hashing nested structures
nested = {
    "name": "John",
    "scores": [95, 87, 92],
    "metadata": {
        "active": True,
        "joined": "2023-01-15"
    }
}
print(hash_dict(nested))  # Consistent hash value for the nested structure

# Hashing Pydantic models
class User(BaseModel):
    name: str
    age: int

user1 = User(name="Alice", age=30)
user2 = User(name="Alice", age=30)
user3 = User(name="Bob", age=25)

print(hash_dict(user1) == hash_dict(user2))  # True - same content
print(hash_dict(user1) == hash_dict(user3))  # False - different content

# Using strict mode for mutable data
mutable_data = {"list": [1, 2, 3]}
hash_value = hash_dict(mutable_data, strict=True)
# Now we can modify the original data without affecting the hash calculation
mutable_data["list"].append(4)
```

## Internal Functions

The following functions are used internally by the module and are not part of the public API:

- `_generate_hashable_representation(item: any) -> any`: Recursively converts a Python object into a stable, hashable representation. This ensures that logically identical but structurally different inputs (e.g., dicts with different key orders) produce the same representation.