"""Utilities for formatting data into human-readable strings."""

import json
from typing import Any

from lionfuncs.utils import to_dict

__all__ = ["as_readable"]


def _is_in_notebook() -> bool:
    """Check if code is running in a Jupyter notebook environment.

    Uses IPython's get_ipython() function to detect if we're in a notebook.

    Returns:
        bool: True if running in a Jupyter notebook, False otherwise
    """
    try:
        from IPython import get_ipython

        ip = get_ipython()
        if ip is not None and hasattr(ip, "has_trait") and ip.has_trait("kernel"):
            return True  # Jupyter notebook, lab, qtconsole
    except (NameError, ImportError):
        pass
    return False


def _format_dict_yaml_like(
    data_dict: dict,
    indent_level: int = 0,
    base_indent: int = 2,
    max_depth: int | None = None,
    current_depth: int = 0,
) -> str:
    """Format a dictionary in a YAML-like readable format.

    Recursively formats Python data (dicts, lists, strings, etc.) into a
    YAML-like readable string with proper indentation.

    Args:
        data_dict: The dictionary to format
        indent_level: Current indentation level
        base_indent: Number of spaces per indentation level
        max_depth: Maximum recursion depth (None for unlimited)
        current_depth: Current recursion depth

    Returns:
        str: A YAML-like formatted string representation of the data
    """
    if max_depth is not None and current_depth >= max_depth:
        return f"{' ' * (indent_level * base_indent)}..."

    lines = []
    prefix = " " * (indent_level * base_indent)

    if isinstance(data_dict, dict):
        if not data_dict:
            return f"{prefix}{{}}"

        for key, value in data_dict.items():
            if isinstance(value, dict):
                # Nested dict
                lines.append(f"{prefix}{key}:")  # Apply prefix here
                lines.append(
                    _format_dict_yaml_like(
                        value,
                        indent_level + 1,  # Increase indent for nested content
                        base_indent,
                        max_depth,
                        current_depth + 1,
                    )
                )
            elif isinstance(value, (list, tuple, set)):
                # List under a key
                if not value:
                    lines.append(f"{prefix}{key}: []")
                    continue

                lines.append(f"{prefix}{key}:")  # Apply prefix here
                for item in value:
                    # For list items, the '-' acts as part of the indent,
                    # so the content itself starts at indent_level + 1 (relative to the key)
                    # and the '-' is at indent_level + 1 (relative to the key's prefix)
                    item_str = _format_dict_yaml_like(
                        item,
                        indent_level + 1,  # Content of list item
                        base_indent,
                        max_depth,
                        current_depth + 1,
                    ).lstrip()
                    lines.append(f"{prefix}{' ' * base_indent}- {item_str}")
            elif isinstance(value, str) and "\n" in value:
                # Multi-line string
                lines.append(f"{prefix}{key}: |")  # Apply prefix here
                subprefix = " " * ((indent_level + 1) * base_indent)
                for line in value.splitlines():
                    lines.append(f"{subprefix}{line}")
            else:
                # Simple single-line scalar
                if isinstance(value, str):
                    # Add quotes if string contains special characters
                    if (
                        ":" in value
                        or "{" in value
                        or "}" in value
                        or "[" in value
                        or "]" in value
                    ):
                        value = f'"{value}"'
                lines.append(f"{prefix}{key}: {value}")  # Apply prefix here
        return "\n".join(lines)

    elif isinstance(data_dict, (list, tuple, set)):
        if not data_dict:
            return f"{prefix}[]"  # Apply prefix here

        # For top-level or nested lists
        for item in data_dict:
            # For list items, the content starts at the current indent_level
            # and the '-' is part of that indent_level's prefix
            item_str = _format_dict_yaml_like(
                item,
                indent_level,  # Content of list item at current indent
                base_indent,
                max_depth,
                current_depth + 1,
            )
            # The item_str already includes its own prefix if it's a complex type.
            # If it's a simple scalar, it will just be the value.
            # We need to ensure the '-' is correctly prefixed.
            if item_str.startswith(
                prefix + " "
            ):  # if it's already indented (e.g. nested list/dict)
                lines.append(f"{prefix}- {item_str.lstrip()}")
            else:  # simple scalar
                lines.append(f"{prefix}- {item_str}")
        return "\n".join(lines)

    # Base case: single-line scalar
    if isinstance(data_dict, str):
        # Add quotes if string contains special characters
        if (
            ":" in data_dict
            or "{" in data_dict
            or "}" in data_dict
            or "[" in data_dict
            or "]" in data_dict
        ):
            data_dict = f'"{data_dict}"'
    return f"{prefix}{data_dict}"  # Apply prefix here


def as_readable(
    data: Any,
    *,
    format_type: str = "auto",
    indent: int = 2,
    max_depth: int | None = None,
    in_notebook_override: bool | None = None,
) -> str:
    """Convert data into a human-readable string format.

    Formats data in a human-readable way, with options for different formats:
    - "yaml_like": A YAML-like format with proper indentation
    - "json": JSON format with indentation
    - "repr": Python's repr() format
    - "auto": Defaults to "yaml_like"

    Args:
        data: The data to format (can be any type)
        format_type: The format to use ("auto", "yaml_like", "json", or "repr")
        indent: Number of spaces per indentation level
        max_depth: Maximum recursion depth for nested structures
        in_notebook_override: Override notebook detection (for testing)

    Returns:
        str: A formatted string representation of the data
    """
    # Check if we're in a notebook
    use_rich_display = (
        in_notebook_override if in_notebook_override is not None else _is_in_notebook()
    )

    # Convert data to a dict/list structure first for consistent formatting
    try:
        processed_data = to_dict(data, exclude_none=True)
    except TypeError:
        # If to_dict fails for the root object, use original
        processed_data = data

    # Determine effective format
    effective_format = format_type.lower()
    if effective_format == "auto":
        effective_format = "yaml_like"

    # Format based on selected format type
    if effective_format == "yaml_like":
        if not isinstance(processed_data, (dict, list, tuple, set)):
            formatted_str = str(processed_data)
        else:
            formatted_str = _format_dict_yaml_like(
                processed_data,
                indent_level=1 if indent > 0 else 0,
                base_indent=indent,
                max_depth=max_depth,
            )
        if use_rich_display:
            return f"```yaml\n{formatted_str}\n```"
        return formatted_str
    elif effective_format == "json":
        try:
            formatted_str = json.dumps(
                processed_data, indent=indent, ensure_ascii=False, default=str
            )
        except Exception:
            formatted_str = str(processed_data)
        if use_rich_display:
            return f"```json\n{formatted_str}\n```"
        return formatted_str
    elif effective_format == "repr":
        return repr(processed_data)
    else:
        raise ValueError(f"Unsupported format_type: {format_type}")
