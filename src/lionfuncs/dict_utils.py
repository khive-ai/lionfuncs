"""Utilities for advanced dictionary manipulation."""

from collections.abc import Sequence
from typing import Any, Literal

from lionfuncs.text_utils import string_similarity

__all__ = ["fuzzy_match_keys"]


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
) -> dict[str, Any]:
    """Match dictionary keys against reference keys using string similarity.

    Validates and corrects dictionary keys based on expected keys using string similarity.
    Can handle exact matches, fuzzy matches, and various strategies for unmatched keys.

    Args:
        data_dict: The dictionary to validate and correct keys for
        reference_keys: List of expected keys or dictionary mapping keys to types
        threshold: Minimum similarity score for fuzzy matching (0.0 to 1.0)
        default_method: String similarity algorithm to use
        case_sensitive: Whether to consider case when matching
        handle_unmatched: Specifies how to handle unmatched keys:
            - "ignore": Keep unmatched keys in output
            - "raise": Raise ValueError if unmatched keys exist
            - "remove": Remove unmatched keys from output
            - "fill": Fill unmatched expected keys with default value/mapping
            - "force": Combine "fill" and "remove" behaviors
        fill_value: Default value for filling unmatched keys
        fill_mapping: Dictionary mapping unmatched keys to default values
        strict: If True, raise ValueError if any expected key is missing

    Returns:
        A new dictionary with validated and corrected keys

    Raises:
        TypeError: If input types are invalid
        ValueError: If validation fails based on specified parameters
    """
    # Input validation
    if not isinstance(data_dict, dict):
        raise TypeError("First argument must be a dictionary")
    if reference_keys is None:
        raise TypeError("Reference keys argument cannot be None")
    if not 0.0 <= threshold <= 1.0:
        raise ValueError("Threshold must be between 0.0 and 1.0")

    # Extract expected keys
    expected_keys = (
        list(reference_keys)
        if isinstance(reference_keys, Sequence)
        else list(reference_keys.keys())
    )
    if not expected_keys:
        return data_dict.copy()  # Return copy of original if no expected keys

    # Initialize output dictionary and tracking sets
    corrected_out = {}
    matched_expected = set()
    matched_input = set()

    # First pass: exact matches
    for key in data_dict:
        compare_key = key if case_sensitive else key.lower()
        for expected_key in expected_keys:
            compare_expected = expected_key if case_sensitive else expected_key.lower()
            if compare_key == compare_expected:
                corrected_out[expected_key] = data_dict[key]
                matched_expected.add(expected_key)
                matched_input.add(key)
                break

    # Second pass: fuzzy matching
    # Second pass: fuzzy matching
    remaining_input = set(data_dict.keys()) - matched_input
    remaining_expected = set(expected_keys) - matched_expected

    for key in list(remaining_input):  # Use list to avoid modifying during iteration
        if not remaining_expected:
            break

        # Find best match
        best_match = None
        best_score = 0.0

        for expected_key in list(remaining_expected):
            # Prepare strings for comparison based on case sensitivity
            compare_key = key if case_sensitive else key.lower()
            compare_expected = expected_key if case_sensitive else expected_key.lower()

            score = string_similarity(
                compare_key, compare_expected, method=default_method
            )
            if score > best_score and score >= threshold:
                best_score = score
                best_match = expected_key

        if best_match:
            corrected_out[best_match] = data_dict[key]
            matched_expected.add(best_match)
            matched_input.add(key)
            remaining_expected.remove(best_match)
        elif handle_unmatched == "ignore":
            corrected_out[key] = data_dict[key]
    # Handle unmatched keys based on handle_unmatched parameter
    unmatched_input = set(data_dict.keys()) - matched_input
    unmatched_expected = set(expected_keys) - matched_expected

    if handle_unmatched == "raise" and unmatched_input:
        raise ValueError(f"Unmatched keys found: {unmatched_input}")

    elif handle_unmatched == "ignore":
        for key in unmatched_input:
            corrected_out[key] = data_dict[key]

    elif handle_unmatched in ("fill", "force"):
        # Fill missing expected keys
        for key in unmatched_expected:
            if fill_mapping and key in fill_mapping:
                corrected_out[key] = fill_mapping[key]
            else:
                corrected_out[key] = fill_value

        # For "fill" mode, also keep unmatched original keys
        if handle_unmatched == "fill":
            for key in unmatched_input:
                corrected_out[key] = data_dict[key]

    # Check strict mode
    if strict and unmatched_expected:
        raise ValueError(f"Missing required keys: {unmatched_expected}")

    return corrected_out
