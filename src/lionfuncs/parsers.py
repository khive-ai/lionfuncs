"""Robust parsing utilities for various data formats."""

import re
from typing import Any

__all__ = ("fuzzy_parse_json",)


from typing import Union

import orjson

try:
    import dirtyjson

    DIRTYJSON_AVAILABLE = True
except ImportError:
    DIRTYJSON_AVAILABLE = False

# --- Compiled Regexes for Cleaning Logic ---
# Pre-compiling regexes improves performance if the function is called frequently.
RE_LINE_COMMENT = re.compile(r"//.*")
RE_BLOCK_COMMENT = re.compile(r"/\*.*?\*/", re.DOTALL)
RE_PYTHON_NONE = re.compile(r"\bNone\b")
RE_PYTHON_TRUE = re.compile(r"\bTrue\b")
RE_PYTHON_FALSE = re.compile(r"\bFalse\b")
RE_UNESCAPED_SINGLE_QUOTE = re.compile(r"(?<!\\)'")  # For ' -> " if not escaped
RE_UNQUOTED_KEY = re.compile(
    r"([\{\[,])\s*([a-zA-Z_][a-zA-Z0-9_]*)\s*:"
)  # For {key: -> {"key":
RE_NORMALIZE_SPACE = re.compile(r"\s\s+")  # For multiple spaces to one
RE_TRAILING_COMMA_OBJECT = re.compile(r",\s*(\})")  # For, } -> }
RE_TRAILING_COMMA_ARRAY = re.compile(r",\s*(\])")  # For, ] -> ]

# --- Type Alias for JSON Output ---
# orjson can parse valid JSON into these primitive types at the top level.
JSONOutputType = Union[dict[str, Any], list[Any], str, int, float, bool, None]

# --- Helper Functions ---


def _check_valid_input_str(str_to_parse: str, /) -> None:
    """Validates that the input is a non-empty string."""
    if not isinstance(str_to_parse, str):
        raise TypeError("Input for fuzzy parsing must be a string.")
    if not str_to_parse.strip():
        raise ValueError("Input string is empty or contains only whitespace.")


def _preprocess_json_string(s: str) -> str:
    """
    Initial preprocessing pass:
    - Removes common comment types (// and /* ... */).
    - Converts Python's None, True, False to JSON's null, true, false.
    """
    s = RE_LINE_COMMENT.sub("", s)
    s = RE_BLOCK_COMMENT.sub("", s)
    s = RE_PYTHON_NONE.sub("null", s)
    s = RE_PYTHON_TRUE.sub("true", s)
    s = RE_PYTHON_FALSE.sub("false", s)
    return s


def _clean_further_json_string(s: str) -> str:
    """
    Second cleaning pass on an already preprocessed string:
    - Converts likely single-quoted strings to double-quoted strings.
    - Attempts to double-quote unquoted object keys.
    - Normalizes multiple whitespace characters to a single space.
    - Removes trailing commas in objects and arrays.
    """
    # Replace ' with " if used as a delimiter (and not escaped)
    s = RE_UNESCAPED_SINGLE_QUOTE.sub('"', s)

    # Add quotes around unquoted keys (e.g., {key: value} -> {"key": value})
    s = RE_UNQUOTED_KEY.sub(r'\1"\2":', s)

    # Normalize whitespace and strip leading/trailing
    s = RE_NORMALIZE_SPACE.sub(" ", s.strip())

    # Remove trailing commas
    s = RE_TRAILING_COMMA_OBJECT.sub(r"\1", s)
    s = RE_TRAILING_COMMA_ARRAY.sub(r"\1", s)
    return s


def _fix_json_brackets(str_to_parse: str) -> Union[str, None]:
    """
    Attempts to fix unmatched brackets/braces in a JSON-like string.
    Skips content within string literals and handles escaped characters.
    Returns the potentially fixed string, or None if an unrecoverable structural
    error (like mismatched bracket types or an unterminated string) is found.
    """
    if not str_to_parse:  # Should be caught earlier, but good guard.
        return None

    brackets_map: dict[str, str] = {"{": "}", "[": "]"}
    open_brackets_stack: list[str] = []  # Stores expected closing characters

    pos = 0
    length = len(str_to_parse)

    while pos < length:
        char = str_to_parse[pos]

        if char == "\\":  # Skip current and next character (escaped sequence)
            pos += 2
            continue

        if char == '"':  # Start of a string literal
            pos += 1  # Move past the opening quote
            # Iterate until the closing double quote, respecting escapes
            while pos < length:
                if str_to_parse[pos] == "\\":
                    pos += 2  # Skip escaped char
                    continue
                if str_to_parse[pos] == '"':
                    break  # End of string literal
                pos += 1

            if pos == length:  # Reached end of string without finding closing quote
                return None  # Unterminated string literal is unrecoverable here
            pos += 1  # Move past the closing quote of the string literal
            continue  # Continue to next character in main loop

        if char in brackets_map:  # Opening bracket/brace
            open_brackets_stack.append(brackets_map[char])
        elif char in brackets_map.values():  # Potential closing bracket/brace
            if not open_brackets_stack or open_brackets_stack[-1] != char:
                # Extra closing bracket or mismatched bracket type
                return None  # Unrecoverable structural error
            open_brackets_stack.pop()

        pos += 1  # Move to the next character

    # If there are unclosed brackets, append the corresponding closing ones
    if open_brackets_stack:
        return str_to_parse + "".join(reversed(open_brackets_stack))

    return str_to_parse  # String was balanced or already fixed


# --- Main Fuzzy Parsing Function ---


def fuzzy_parse_json(str_to_parse: str, /) -> JSONOutputType:
    """
    Attempts to parse a JSON-like string into a Python object, trying several
    common fixes for non-standard JSON syntax.

    The parsing strategy is tiered:
    1. Direct parse with `orjson.loads()` (fastest, for valid JSON).
    2. Preprocess (comments, Python constants) then `orjson.loads()`.
    3. Further clean (quotes, keys, spaces, trailing commas) then `orjson.loads()`.
    4. Fix brackets on the cleaned string, then `orjson.loads()`.
    5. If `dirtyjson` is available, fallback to it using the preprocessed string,
       as it can handle more complex JavaScript-like "dirtiness".
    6. As a last resort, try `dirtyjson` on the absolute original string.

    Args:
        str_to_parse: The string suspected to be JSON or JSON-like.

    Returns:
        The parsed Python object (dict, list, str, int, float, bool, or None).

    Raises:
        TypeError: If the input `str_to_parse` is not a string.
        ValueError: If the input string is empty or contains only whitespace,
                    or if all parsing and fixing attempts fail.
    """
    _check_valid_input_str(str_to_parse)

    # Keep the absolute original for a final fallback with dirtyjson if all else fails
    absolute_original_string = str_to_parse

    # Pass 0: Initial preprocessing (comments, Python constants)
    # This helps all subsequent parsers.
    s_preprocessed = _preprocess_json_string(absolute_original_string)

    # Pass 1: Try parsing the preprocessed string directly with orjson
    try:
        return orjson.loads(s_preprocessed)
    except orjson.JSONDecodeError:
        pass  # Continue to more aggressive fixes

    # Pass 2: Apply further cleaning (quotes, keys, spaces, trailing commas)
    s_cleaned = _clean_further_json_string(s_preprocessed)
    try:
        return orjson.loads(s_cleaned)
    except orjson.JSONDecodeError:
        pass

    # Pass 3: Try fixing brackets on the already cleaned string
    s_brackets_fixed_on_cleaned = _fix_json_brackets(s_cleaned)
    if s_brackets_fixed_on_cleaned is not None:
        try:
            return orjson.loads(s_brackets_fixed_on_cleaned)
        except orjson.JSONDecodeError:
            pass

    # Pass 4 (Optional, if cleaning might have broken bracket logic): Fix brackets on preprocessed string
    # This is useful if _clean_further_json_string was too aggressive for _fix_json_brackets.
    if s_cleaned != s_preprocessed:  # Only if cleaning pass actually changed the string
        s_brackets_fixed_on_preprocessed = _fix_json_brackets(s_preprocessed)
        if (
            s_brackets_fixed_on_preprocessed is not None
            and s_brackets_fixed_on_preprocessed != s_brackets_fixed_on_cleaned
        ):  # Avoid re-parsing identical string
            try:
                return orjson.loads(s_brackets_fixed_on_preprocessed)
            except orjson.JSONDecodeError:
                pass

    # Pass 5: Fallback to dirtyjson if available, using the preprocessed string first
    # (as it handles Python constants which dirtyjson might not)
    if DIRTYJSON_AVAILABLE:
        try:
            return dirtyjson.loads(s_preprocessed)  # type: ignore
        except Exception:  # dirtyjson can raise various error types
            # As a very final attempt, try dirtyjson on the absolute original string
            try:
                return dirtyjson.loads(absolute_original_string)  # type: ignore
            except Exception:
                pass  # Fall through to the final ValueError

    # If all attempts fail, raise an error.
    # The "last tried" string for the error message can be chosen based on the last successful modification.
    last_attempted_custom_fix = (
        s_brackets_fixed_on_cleaned
        if s_brackets_fixed_on_cleaned is not None
        else s_cleaned
        if s_cleaned != s_preprocessed
        else s_preprocessed
    )
    raise ValueError(
        f"Input string could not be parsed as JSON after multiple fuzzy fixing attempts. "
        f"Original (first 100 chars): '{absolute_original_string[:100]}{'...' if len(absolute_original_string) > 100 else ''}'. "
        f"Last custom variant tried (first 100 chars): '{last_attempted_custom_fix[:100]}{'...' if len(last_attempted_custom_fix) > 100 else ''}'"
    )
