---
title: "lionfuncs.to_dict"
---

# lionfuncs.to_dict

The `to_dict` module provides robust utilities for converting various Python objects to dictionaries, with extensive support for different types and conversion options.

## Functions

### to_dict

```python
def to_dict(
    input_: Any,
    /,
    *,
    use_model_dump: bool = True,
    use_enum_values: bool = False,
    parse_strings: bool = False,
    str_type_for_parsing: Literal["json", "xml"] | None = "json",
    fuzzy_parse_strings: bool = False,
    custom_str_parser: Callable[[str], Any] | None = None,
    recursive: bool = False,
    max_recursive_depth: int = 5,
    recursive_stop_types: tuple[type[Any], ...] = (
        str,
        int,
        float,
        bool,
        bytes,
        bytearray,
        type(None),
    ),
    suppress_errors: bool = False,
    default_on_error: dict[str, Any] | None = None,
    convert_top_level_iterable_to_dict: bool = False,
    **kwargs: Any,
) -> dict[str, Any]
```

Convert various Python objects to a dictionary representation.

This function handles a wide range of input types, including Pydantic models, dataclasses, enums, mappings, and more. It provides extensive options for customizing the conversion process.

#### Parameters

- **input_** (`Any`): The object to convert to a dictionary
- **use_model_dump** (`bool`, optional): Whether to prefer `model_dump()` over `dict()` for Pydantic models. Defaults to `True`.
- **use_enum_values** (`bool`, optional): If True, enum members are converted to their values. Defaults to `False`.
- **parse_strings** (`bool`, optional): If True, attempts to parse string values as JSON or XML. Defaults to `False`.
- **str_type_for_parsing** (`Literal["json", "xml"] | None`, optional): The format to use when parsing strings. Defaults to `"json"`.
- **fuzzy_parse_strings** (`bool`, optional): If True, uses fuzzy parsing for strings. Defaults to `False`.
- **custom_str_parser** (`Callable[[str], Any] | None`, optional): Custom function for parsing strings. Defaults to `None`.
- **recursive** (`bool`, optional): If True, recursively converts nested objects. Defaults to `False`.
- **max_recursive_depth** (`int`, optional): Maximum depth for recursive conversion. Defaults to `5`.
- **recursive_stop_types** (`tuple[type[Any], ...]`, optional): Types that stop recursive conversion. Defaults to primitive types.
- **suppress_errors** (`bool`, optional): If True, returns default_on_error when errors occur. Defaults to `False`.
- **default_on_error** (`dict[str, Any] | None`, optional): Default value to return on error. Defaults to `None`.
- **convert_top_level_iterable_to_dict** (`bool`, optional): If True, converts top-level iterables to dictionaries. Defaults to `False`.
- **kwargs** (`Any`): Additional arguments passed to serialization methods.

#### Returns

- `dict[str, Any]`: A dictionary representation of the input object

#### Raises

- `ValueError`: If conversion fails and suppress_errors is False

#### Example

```python
from lionfuncs.to_dict import to_dict
from pydantic import BaseModel
from enum import Enum

# Basic usage with a dictionary
data = {"name": "John", "age": 30}
result = to_dict(data)
print(result)  # {'name': 'John', 'age': 30}

# Converting a Pydantic model
class User(BaseModel):
    name: str
    age: int
    is_active: bool = True

user = User(name="Jane", age=25)
result = to_dict(user)
print(result)  # {'name': 'Jane', 'age': 25, 'is_active': True}

# Converting an Enum with values
class Color(Enum):
    RED = "#FF0000"
    GREEN = "#00FF00"
    BLUE = "#0000FF"

result = to_dict(Color, use_enum_values=True)
print(result)  # {'RED': '#FF0000', 'GREEN': '#00FF00', 'BLUE': '#0000FF'}

# Parsing a JSON string
json_str = '{"name": "Alice", "scores": [95, 87, 92]}'
result = to_dict(json_str, parse_strings=True)
print(result)  # {'name': 'Alice', 'scores': [95, 87, 92]}

# Parsing an XML string
xml_str = '<user><name>Bob</name><age>40</age></user>'
result = to_dict(xml_str, parse_strings=True, str_type_for_parsing="xml")
print(result)  # {'name': 'Bob', 'age': '40'}

# Recursive conversion
nested_data = {
    "user": User(name="Alex", age=35),
    "preferences": {"theme": "dark", "notifications": True}
}
result = to_dict(nested_data, recursive=True)
print(result)  # {'user': {'name': 'Alex', 'age': 35, 'is_active': True}, 'preferences': {'theme': 'dark', 'notifications': True}}

# Error handling
invalid_data = object()  # An object that can't be converted to dict
result = to_dict(invalid_data, suppress_errors=True, default_on_error={"error": "Conversion failed"})
print(result)  # {'error': 'Conversion failed'}
```

## Internal Functions

The following functions are used internally by the module and are not part of the public API:

- `_internal_xml_to_dict_parser(xml_string: str, remove_root: bool = True, **kwargs: Any) -> dict[str, Any]`: Parse XML strings to dictionaries.
- `_convert_item_to_dict_element(item: Any, use_model_dump: bool, use_enum_values: bool, parse_strings: bool, str_type_for_parsing: Literal["json", "xml"] | None, fuzzy_parse_strings: bool, custom_str_parser: Callable[[str], Any] | None, **serializer_kwargs: Any) -> Any`: Convert a single item to a dictionary element.
- `_recursive_apply_to_dict(current_data: Any, current_depth: int, max_depth: int, stop_types: tuple[type[Any], ...], conversion_params: dict[str, Any]) -> Any`: Recursively apply dictionary conversion to nested structures.