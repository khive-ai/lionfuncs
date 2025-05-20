---
title: "lionfuncs.text_utils"
---

# lionfuncs.text_utils

The `text_utils` module provides utilities for string similarity calculations
and text processing.

## Functions

### string_similarity

```python
def string_similarity(
    s1: str,
    s2: str,
    method: Literal["levenshtein", "jaro_winkler", "hamming", "cosine", "sequence_matcher"] | Callable[[str, str], float] = "levenshtein",
    **kwargs: Any,
) -> float
```

Calculate the similarity between two strings using the specified method.

This function provides a unified interface to various string similarity
algorithms, returning a normalized score between 0.0 (completely different) and
1.0 (identical).

#### Parameters

- **s1** (`str`): First input string
- **s2** (`str`): Second input string
- **method**
  (`Literal["levenshtein", "jaro_winkler", "hamming", "cosine", "sequence_matcher"] | Callable[[str, str], float]`,
  optional): Similarity algorithm to use. Options:
  - `"levenshtein"`: Edit distance-based similarity
  - `"jaro_winkler"`: Jaro-Winkler similarity
  - `"hamming"`: Hamming distance-based similarity (requires equal length
    strings)
  - `"cosine"`: Cosine similarity using word tokenization
  - `"sequence_matcher"`: Python's SequenceMatcher ratio
  - Or a custom callable that takes two strings and returns a float
- **kwargs** (`Any`): Additional arguments for specific methods:
  - For `"jaro_winkler"`: `scaling_factor` (float, default 0.1)

#### Returns

- `float`: Similarity score between 0 and 1, where 1 means identical

#### Raises

- `ValueError`: If an unsupported method is specified or if hamming is used with
  strings of different lengths

#### Example

```python
from lionfuncs.text_utils import string_similarity

# Using Levenshtein distance (default)
score = string_similarity("kitten", "sitting")
print(f"Levenshtein similarity: {score:.4f}")  # Approximately 0.5714

# Using Jaro-Winkler
score = string_similarity("kitten", "sitting", method="jaro_winkler")
print(f"Jaro-Winkler similarity: {score:.4f}")  # Approximately 0.7467

# Using cosine similarity with word tokenization
s1 = "The quick brown fox jumps over the lazy dog"
s2 = "The brown fox jumped over the dog"
score = string_similarity(s1, s2, method="cosine")
print(f"Cosine similarity: {score:.4f}")  # Approximately 0.8944

# Using a custom similarity function
def custom_similarity(a: str, b: str) -> float:
    # Simple custom similarity based on common characters
    common = set(a) & set(b)
    return len(common) / max(len(set(a)), len(set(b)))

score = string_similarity("hello", "hola", method=custom_similarity)
print(f"Custom similarity: {score:.4f}")  # Approximately 0.5000
```

## Internal Functions

The following functions are used internally by the module and are not part of
the public API:

- `_levenshtein_distance(s1: str, s2: str) -> int`: Calculate the Levenshtein
  (edit) distance between two strings.
- `_levenshtein_similarity(s1: str, s2: str) -> float`: Calculate the
  Levenshtein similarity between two strings.
- `_jaro_distance(s1: str, s2: str) -> float`: Calculate the Jaro distance
  between two strings.
- `_jaro_winkler_similarity(s1: str, s2: str, scaling_factor: float = 0.1) -> float`:
  Calculate the Jaro-Winkler similarity between two strings.
- `_hamming_distance(s1: str, s2: str) -> int`: Calculate the Hamming distance
  between two strings.
- `_hamming_similarity(s1: str, s2: str) -> float`: Calculate the Hamming
  similarity between two strings.
- `_cosine_similarity(text1: str, text2: str) -> float`: Calculate the cosine
  similarity between two strings using word tokenization.
- `_sequence_matcher_similarity(s1: str, s2: str) -> float`: Calculate
  similarity using Python's SequenceMatcher.
