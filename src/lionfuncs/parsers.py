"""Robust parsing utilities for various data formats."""

import json
import logging
import re
from typing import Any

__all__ = ["fuzzy_parse_json"]


def _fix_json_string(json_string: str) -> str:
    """Fix common JSON formatting issues.

    Applies a series of transformations to fix common JSON formatting issues:
    - Converts single quotes to double quotes
    - Removes trailing commas
    - Fixes boolean and null values casing

    Args:
        json_string: The JSON string to fix

    Returns:
        str: The fixed JSON string
    """
    s = json_string.strip()

    # Convert single quotes to double quotes (not preceded by backslash)
    s = re.sub(r"(?<!\\)'", '"', s)

    # Remove trailing commas in objects and arrays
    s = re.sub(r",\s*([\}\]])", r"\1", s)

    # Fix boolean and null values casing
    s = re.sub(r"\bTrue\b", "true", s, flags=re.IGNORECASE)
    s = re.sub(r"\bFalse\b", "false", s, flags=re.IGNORECASE)
    s = re.sub(r"\bNone\b|\bNull\b", "null", s, flags=re.IGNORECASE)

    # Fix unquoted keys (basic support)
    s = re.sub(r'([{,])\s*([^"\s{}:,]+)\s*:', r'\1"\2":', s)

    return s


def fuzzy_parse_json(
    json_string: str,
    *,
    attempt_fix: bool = True,
    strict: bool = False,
    log_errors: bool = False,
) -> Any | None:
    """Parse a JSON string with optional fuzzy fixing for common errors.

    Attempts to parse a JSON string, with options to fix common formatting issues:
    1. First tries to parse the string directly
    2. If that fails and attempt_fix=True, tries to fix common issues and parse again
    3. If all parsing attempts fail, either returns None or raises an exception

    Args:
        json_string: The JSON string to parse
        attempt_fix: Whether to attempt fixing common JSON formatting issues
        strict: If True, raises exceptions on parsing failures instead of returning None
        log_errors: If True, logs parsing errors using the logging module

    Returns:
        The parsed JSON data (dict, list, or primitive types) or None if parsing fails
        and strict=False

    Raises:
        ValueError: If the string cannot be parsed and strict=True
        TypeError: If json_string is not a string
    """
    if not isinstance(json_string, str):
        raise TypeError("Input must be a string")

    if not json_string.strip():
        if strict:
            raise ValueError("Input string is empty")
        return None

    original_string = json_string

    # First attempt: direct parsing
    try:
        return json.loads(json_string)
    except json.JSONDecodeError as e:
        if log_errors:
            logging.warning(f"Direct JSON parsing failed: {e}")

        if not attempt_fix:
            if strict:
                raise ValueError(f"JSON parsing failed: {e}")
            return None

    # Second attempt: fix and parse
    try:
        fixed_string = _fix_json_string(json_string)
        return json.loads(fixed_string)
    except json.JSONDecodeError as e_fixed:
        if log_errors:
            logging.warning(f"Failed to parse fixed JSON: {e_fixed}")

        # Third attempt: try original again (in case fixing made it worse)
        try:
            return json.loads(original_string)
        except json.JSONDecodeError as e_orig:
            if log_errors:
                logging.warning(f"Failed to parse original JSON: {e_orig}")

            if strict:
                raise ValueError(f"JSON parsing failed after fix attempts: {e_orig}")
            return None
