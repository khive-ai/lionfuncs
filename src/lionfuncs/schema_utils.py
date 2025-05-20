"""Utilities for generating and manipulating schemas."""

import inspect
import re
import types
from typing import Any, Callable, Union, get_type_hints

from pydantic import BaseModel

__all__ = ["function_to_openai_schema", "pydantic_model_to_openai_schema"]


# Python type to JSON schema type mapping
_PY_TO_JSON_TYPE_MAP = {
    "str": "string",
    "int": "integer",
    "float": "number",
    "bool": "boolean",
    "list": "array",
    "tuple": "array",
    "dict": "object",
    "None": "null",
}


def _get_type_name(annotation: Any) -> str:
    """Get a string representation of a type annotation.

    Args:
        annotation: The type annotation to convert

    Returns:
        str: String representation of the type
    """
    if annotation is inspect.Parameter.empty:
        return "any"

    if hasattr(annotation, "__origin__"):
        # Handle generic types like List[str], Dict[str, int], etc.
        origin = annotation.__origin__
        args = getattr(annotation, "__args__", [])

        if origin is list or origin is tuple:
            return "array"
        elif origin is dict:
            return "object"
        elif origin is Union or origin is getattr(types, "UnionType", None):
            # Handle Union types (including Optional)
            if type(None) in args:
                # It's an Optional type
                non_none_args = [arg for arg in args if arg is not type(None)]
                if len(non_none_args) == 1:
                    return _get_type_name(non_none_args[0])
            return "any"  # For complex unions, just use "any"

    # Handle simple types
    type_name = getattr(annotation, "__name__", str(annotation))
    return _PY_TO_JSON_TYPE_MAP.get(type_name, type_name)


def _extract_docstring_parts(docstring: str | None) -> tuple[str, dict[str, str]]:
    """Extract function description and parameter descriptions from docstring.

    Args:
        docstring: The function docstring

    Returns:
        tuple: (function_description, parameter_descriptions_dict)
    """
    if not docstring:
        return "", {}

    # Split docstring into sections
    parts = docstring.strip().split("\n\n")

    # First part is the function description
    func_description = parts[0].strip()

    # Look for Args/Parameters section
    param_descriptions = {}
    # Regex to find "Args:" or "Parameters:" section and capture content
    args_section_match = re.search(
        r"(Args|Parameters):\s*\n((?:.|\n)*?)(?=\n\n|\Z)", docstring, re.MULTILINE
    )

    if args_section_match:
        args_content = args_section_match.group(2)
        # Regex to capture individual parameters and their descriptions
        # Handles multiline descriptions by looking for lines indented more than the parameter name
        param_matches = re.finditer(
            r"^\s*([_a-zA-Z]\w*)\s*\(.*?\)?\s*:\s*(.*?)(?=\n\s*[_a-zA-Z]\w*\s*\(|\Z)",
            args_content,
            re.MULTILINE | re.DOTALL,
        )
        if not list(
            re.finditer(
                r"^\s*([_a-zA-Z]\w*)\s*\(.*?\)?\s*:\s*(.*?)(?=\n\s*[_a-zA-Z]\w*\s*\(|\Z)",
                args_content,
                re.MULTILINE | re.DOTALL,
            )
        ):  # check if any matches found
            # Fallback for simpler "param: description" format if the above doesn't match
            param_matches = re.finditer(
                r"^\s*([_a-zA-Z]\w*)\s*:\s*(.*?)(?=\n\s*[_a-zA-Z]\w*\s*:|\Z)",
                args_content,
                re.MULTILINE | re.DOTALL,
            )

        for match in param_matches:
            param_name = match.group(1).strip()
            description_lines = match.group(2).strip().split("\n")
            # Join lines, removing extra whitespace from each line before joining
            param_descriptions[param_name] = " ".join(
                line.strip() for line in description_lines
            )

    return func_description, param_descriptions


def function_to_openai_schema(func: Callable) -> dict[str, Any]:
    """Generate an OpenAI function schema from a Python function.

    Analyzes a function's signature, type hints, and docstring to generate
    a schema compatible with OpenAI's function calling API.

    Args:
        func: The function to generate a schema for

    Returns:
        dict: A schema describing the function, including its name,
              description, and parameter details
    """
    # Get function name
    func_name = func.__name__

    # Extract function description and parameter descriptions from docstring
    docstring = inspect.getdoc(func)
    func_description, param_descriptions = _extract_docstring_parts(docstring)

    # Get function signature and type hints
    sig = inspect.signature(func)
    try:
        type_hints = get_type_hints(func)
    except Exception:
        # Handle cases where get_type_hints might fail
        type_hints = {}

    # Create parameters schema
    parameters = {"type": "object", "properties": {}, "required": []}

    for name, param in sig.parameters.items():
        # Skip self/cls parameters
        if name in ("self", "cls"):
            continue

        # Get parameter type
        annotation = type_hints.get(name, param.annotation)
        param_type = _get_type_name(annotation)

        # Get parameter description
        description = param_descriptions.get(name, "")

        # Add parameter to schema
        parameters["properties"][name] = {
            "type": param_type,
            "description": description,
        }

        # Check if parameter is required
        if param.default is inspect.Parameter.empty:
            parameters["required"].append(name)

    # Create final schema
    schema = {
        "name": func_name,
        "description": func_description,
        "parameters": parameters,
    }

    return schema


def pydantic_model_to_openai_schema(model_class: type[BaseModel]) -> dict[str, Any]:
    """Convert a Pydantic model to an OpenAI parameter schema.

    Args:
        model_class: The Pydantic model class

    Returns:
        dict: A schema describing the model's fields
    """
    schema = model_class.model_json_schema()

    # Adjust schema to match OpenAI's expected format
    result = {
        "type": "object",
        "properties": schema.get("properties", {}),
    }

    if "required" in schema:
        result["required"] = schema["required"]

    return result
