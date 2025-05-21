---
title: "lionfuncs.oai_schema_utils"
---

# lionfuncs.oai_schema_utils

The `oai_schema_utils` module provides utilities for generating and manipulating
schemas, with a focus on creating OpenAI-compatible function schemas from Python
functions and Pydantic models.

## Functions

### function_to_openai_schema

```python
def function_to_openai_schema(func: Callable) -> dict[str, Any]
```

Generate an OpenAI function schema from a Python function.

Analyzes a function's signature, type hints, and docstring to generate a schema
compatible with OpenAI's function calling API. This is particularly useful for
creating function descriptions for OpenAI's function calling features.

#### Parameters

- **func** (`Callable`): The function to generate a schema for

#### Returns

- `dict[str, Any]`: A schema describing the function, including its name,
  description, and parameter details

#### Example

```python
from lionfuncs.oai_schema_utils import function_to_openai_schema

# Define a function with type hints and docstring
def calculate_price(
    product_id: str,
    quantity: int,
    discount: float = 0.0,
    tax_rate: float = 0.0
) -> float:
    """Calculate the final price for a product order.

    Args:
        product_id: The unique identifier for the product
        quantity: Number of items to purchase
        discount: Discount rate as a decimal (e.g., 0.1 for 10% off)
        tax_rate: Tax rate as a decimal (e.g., 0.07 for 7% tax)

    Returns:
        The final price after discount and tax
    """
    # Function implementation not relevant for schema generation
    pass

# Generate OpenAI function schema
schema = function_to_openai_schema(calculate_price)
print(schema)
```

Output:

```python
{
    "name": "calculate_price",
    "description": "Calculate the final price for a product order.",
    "parameters": {
        "type": "object",
        "properties": {
            "product_id": {
                "type": "string",
                "description": "The unique identifier for the product"
            },
            "quantity": {
                "type": "integer",
                "description": "Number of items to purchase"
            },
            "discount": {
                "type": "number",
                "description": "Discount rate as a decimal (e.g., 0.1 for 10% off)"
            },
            "tax_rate": {
                "type": "number",
                "description": "Tax rate as a decimal (e.g., 0.07 for 7% tax)"
            }
        },
        "required": ["product_id", "quantity"]
    }
}
```

### pydantic_model_to_openai_schema

```python
def pydantic_model_to_openai_schema(
    model_class: type[BaseModel],
    function_name: str,
    function_description: str,
) -> dict[str, Any]
```

Convert a Pydantic model to an OpenAI parameter schema.

This function takes a Pydantic model class and converts it to a schema format
compatible with OpenAI's function calling API. It now requires a function name
and description to create a complete function schema.

#### Parameters

- **model_class** (`type[BaseModel]`): The Pydantic model class
- **function_name** (`str`): The name to use for the function in the schema
- **function_description** (`str`): The description of the function

#### Returns

- `dict[str, Any]`: A complete function schema for use with OpenAI's function
  calling API

#### Example

```python
from pydantic import BaseModel, Field
from lionfuncs.oai_schema_utils import pydantic_model_to_openai_schema

# Define a Pydantic model
class UserProfile(BaseModel):
    username: str = Field(..., description="The user's unique username")
    email: str = Field(..., description="The user's email address")
    age: int | None = Field(None, description="The user's age in years")
    interests: list[str] = Field(default_factory=list, description="List of user interests")

# Convert to OpenAI function schema
schema = pydantic_model_to_openai_schema(
    UserProfile,
    function_name="create_user",
    function_description="Create a new user profile in the system"
)
print(schema)
```

Output:

```python
{
    "type": "function",
    "function": {
        "name": "create_user",
        "description": "Create a new user profile in the system",
        "parameters": {
            "type": "object",
            "properties": {
                "username": {
                    "type": "string",
                    "description": "The user's unique username"
                },
                "email": {
                    "type": "string",
                    "description": "The user's email address"
                },
                "age": {
                    "anyOf": [
                        {"type": "integer"},
                        {"type": "null"}
                    ],
                    "description": "The user's age in years"
                },
                "interests": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of user interests"
                }
            },
            "required": ["username", "email"]
        }
    }
}
```

## Internal Functions

The following functions are used internally by the module and are not part of
the public API:

- `_get_type_name(annotation: Any) -> str`: Get a string representation of a
  type annotation.
- `_extract_docstring_parts(docstring: str | None) -> tuple[str, dict[str, str]]`:
  Extract function description and parameter descriptions from docstring.
- `_PY_TO_JSON_TYPE_MAP`: Dictionary mapping Python type names to JSON schema
  type names.

## Notes

This module was previously named `schema_utils.py` but has been renamed to
`oai_schema_utils.py` to better reflect its focus on OpenAI schema generation.
