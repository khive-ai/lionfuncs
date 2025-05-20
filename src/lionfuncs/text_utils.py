"""String similarity and text processing utilities."""

import re
from collections import Counter
from difflib import SequenceMatcher
from typing import Any, Callable, Literal

__all__ = ["string_similarity"]


def _levenshtein_distance(s1: str, s2: str) -> int:
    """Calculate the Levenshtein (edit) distance between two strings.

    Args:
        s1: First input string
        s2: Second input string

    Returns:
        int: Minimum number of single-character edits needed to change one
             string into the other
    """
    if not s1:
        return len(s2)
    if not s2:
        return len(s1)

    # Initialize matrix of size (len(s1)+1) x (len(s2)+1)
    m, n = len(s1), len(s2)
    d = [[0] * (n + 1) for _ in range(m + 1)]

    # Fill the first row and column
    for i in range(m + 1):
        d[i][0] = i
    for j in range(n + 1):
        d[0][j] = j

    # Fill the rest of the matrix
    for i in range(1, m + 1):
        for j in range(1, n + 1):
            cost = 0 if s1[i - 1] == s2[j - 1] else 1
            d[i][j] = min(
                d[i - 1][j] + 1,  # deletion
                d[i][j - 1] + 1,  # insertion
                d[i - 1][j - 1] + cost,  # substitution
            )

    return d[m][n]


def _levenshtein_similarity(s1: str, s2: str) -> float:
    """Calculate the Levenshtein similarity between two strings.

    Converts Levenshtein distance to a similarity score between 0 and 1.

    Args:
        s1: First input string
        s2: Second input string

    Returns:
        float: Levenshtein similarity score between 0 and 1
    """
    if not s1 and not s2:
        return 1.0
    if not s1 or not s2:
        return 0.0

    distance = _levenshtein_distance(s1, s2)
    max_len = max(len(s1), len(s2))
    return 1 - (distance / max_len)


def _jaro_distance(s1: str, s2: str) -> float:
    """Calculate the Jaro distance between two strings.

    Args:
        s1: First input string
        s2: Second input string

    Returns:
        float: Jaro distance score between 0 and 1
    """
    s1_len = len(s1)
    s2_len = len(s2)

    if s1_len == 0 and s2_len == 0:
        return 1.0
    elif s1_len == 0 or s2_len == 0:
        return 0.0

    match_distance = (max(s1_len, s2_len) // 2) - 1
    match_distance = max(0, match_distance)  # Ensure non-negative

    s1_matches = [False] * s1_len
    s2_matches = [False] * s2_len

    matches = 0
    transpositions = 0

    # Identify matches
    for i in range(s1_len):
        start = max(0, i - match_distance)
        end = min(i + match_distance + 1, s2_len)

        for j in range(start, end):
            if s2_matches[j] or s1[i] != s2[j]:
                continue
            s1_matches[i] = s2_matches[j] = True
            matches += 1
            break

    if matches == 0:
        return 0.0

    # Count transpositions
    k = 0
    for i in range(s1_len):
        if not s1_matches[i]:
            continue
        while not s2_matches[k]:
            k += 1
        if s1[i] != s2[k]:
            transpositions += 1
        k += 1

    transpositions //= 2

    return (
        matches / s1_len + matches / s2_len + (matches - transpositions) / matches
    ) / 3.0


def _jaro_winkler_similarity(s1: str, s2: str, scaling_factor: float = 0.1) -> float:
    """Calculate the Jaro-Winkler similarity between two strings.

    Args:
        s1: First input string
        s2: Second input string
        scaling_factor: Scaling factor for common prefix adjustment

    Returns:
        float: Jaro-Winkler similarity score between 0 and 1

    Raises:
        ValueError: If scaling factor is not between 0 and 0.25
    """
    if not 0 <= scaling_factor <= 0.25:
        raise ValueError("Scaling factor must be between 0 and 0.25")

    jaro_sim = _jaro_distance(s1, s2)

    # Find length of common prefix (up to 4 chars)
    prefix_len = 0
    for s_char, t_char in zip(s1, s2):
        if s_char != t_char:
            break
        prefix_len += 1
        if prefix_len == 4:
            break

    return jaro_sim + (prefix_len * scaling_factor * (1 - jaro_sim))


def _hamming_distance(s1: str, s2: str) -> int:
    """Calculate the Hamming distance between two strings.

    The strings must be of equal length.

    Args:
        s1: First input string
        s2: Second input string

    Returns:
        int: Number of positions at which corresponding symbols differ

    Raises:
        ValueError: If strings have different lengths
    """
    if len(s1) != len(s2):
        raise ValueError("Hamming distance requires strings of equal length")

    return sum(c1 != c2 for c1, c2 in zip(s1, s2))


def _hamming_similarity(s1: str, s2: str) -> float:
    """Calculate the Hamming similarity between two strings.

    The strings must be of equal length. Returns the proportion of positions
    at which corresponding symbols are the same.

    Args:
        s1: First input string
        s2: Second input string

    Returns:
        float: Hamming similarity score between 0 and 1

    Raises:
        ValueError: If strings have different lengths
    """
    if not s1 and not s2:
        return 1.0
    if not s1 or not s2 or len(s1) != len(s2):
        return 0.0

    matches = sum(c1 == c2 for c1, c2 in zip(s1, s2))
    return matches / len(s1)


def _cosine_similarity(text1: str, text2: str) -> float:
    """Calculate the cosine similarity between two strings using word tokenization.

    Args:
        text1: First input text
        text2: Second input text

    Returns:
        float: Cosine similarity score between 0 and 1
    """
    # Process strings: remove punctuation and convert to lowercase
    s1_processed = re.sub(r"[^\w\s]", "", text1).lower()
    s2_processed = re.sub(r"[^\w\s]", "", text2).lower()

    # Tokenize into words
    tokens1 = s1_processed.split()
    tokens2 = s2_processed.split()

    # Create vectors using Counter
    vec1 = Counter(tokens1)
    vec2 = Counter(tokens2)

    # Get all unique words
    all_words = set(vec1.keys()) | set(vec2.keys())

    # Calculate dot product
    dot_product = sum(vec1.get(word, 0) * vec2.get(word, 0) for word in all_words)

    # Calculate magnitudes
    magnitude1 = sum(vec1.get(word, 0) ** 2 for word in all_words) ** 0.5
    magnitude2 = sum(vec2.get(word, 0) ** 2 for word in all_words) ** 0.5

    # Handle zero magnitudes
    if magnitude1 == 0 or magnitude2 == 0:
        return 0.0

    return dot_product / (magnitude1 * magnitude2)


def _sequence_matcher_similarity(s1: str, s2: str) -> float:
    """Calculate similarity using Python's SequenceMatcher.

    Args:
        s1: First input string
        s2: Second input string

    Returns:
        float: Similarity score between 0 and 1
    """
    return SequenceMatcher(None, s1, s2).ratio()


def string_similarity(
    s1: str,
    s2: str,
    method: Literal[
        "levenshtein", "jaro_winkler", "hamming", "cosine", "sequence_matcher"
    ]
    | Callable[[str, str], float] = "levenshtein",
    **kwargs: Any,
) -> float:
    """Calculate the similarity between two strings using the specified method.

    Args:
        s1: First input string
        s2: Second input string
        method: Similarity algorithm to use. Options:
            - "levenshtein": Edit distance-based similarity
            - "jaro_winkler": Jaro-Winkler similarity
            - "hamming": Hamming distance-based similarity (requires equal length strings)
            - "cosine": Cosine similarity using word tokenization
            - "sequence_matcher": Python's SequenceMatcher ratio
            - Or a custom callable that takes two strings and returns a float
        **kwargs: Additional arguments for specific methods:
            - For "jaro_winkler": scaling_factor (float, default 0.1)

    Returns:
        float: Similarity score between 0 and 1, where 1 means identical

    Raises:
        ValueError: If an unsupported method is specified or if hamming is used
                   with strings of different lengths
    """
    method_name = method if isinstance(method, str) else method.__name__
    method_name = method_name.lower()

    if method_name == "levenshtein":
        return _levenshtein_similarity(s1, s2)
    elif method_name == "jaro_winkler":
        scaling_factor = kwargs.get("scaling_factor", 0.1)
        return _jaro_winkler_similarity(s1, s2, scaling_factor)
    elif method_name == "hamming":
        if len(s1) != len(s2):
            raise ValueError("Hamming distance requires strings of equal length")
        return _hamming_similarity(s1, s2)
    elif method_name == "cosine":
        return _cosine_similarity(s1, s2)
    elif method_name == "sequence_matcher":
        return _sequence_matcher_similarity(s1, s2)
    elif callable(method):
        return method(s1, s2)
    else:
        raise ValueError(f"Unsupported similarity method: {method}")
