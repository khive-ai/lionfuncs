"""Tests for the schema_utils module."""

from typing import Any, Optional, Union

from pydantic import BaseModel, Field

from lionfuncs.oai_schema_utils import (
    _extract_docstring_parts,
    _get_type_name,
    function_to_openai_schema,
    pydantic_model_to_openai_schema,
)


class TestSchemaUtils:
    """Tests for schema_utils module."""

    def test_get_type_name_simple_types(self):
        """Test _get_type_name with simple types."""
        assert _get_type_name(str) == "string"
        assert _get_type_name(int) == "integer"
        assert _get_type_name(float) == "number"
        assert _get_type_name(bool) == "boolean"
        assert _get_type_name(dict) == "object"
        assert _get_type_name(list) == "array"
        assert _get_type_name(tuple) == "array"

    def test_get_type_name_complex_types(self):
        """Test _get_type_name with complex types."""
        assert _get_type_name(list[str]) == "array"
        assert _get_type_name(dict[str, int]) == "object"
        assert _get_type_name(Optional[str]) == "string"
        assert _get_type_name(Union[str, int]) == "any"

    def test_extract_docstring_parts_empty(self):
        """Test _extract_docstring_parts with empty docstring."""
        desc, params = _extract_docstring_parts(None)
        assert desc == ""
        assert params == {}

        desc, params = _extract_docstring_parts("")
        assert desc == ""
        assert params == {}

    def test_extract_docstring_parts_simple(self):
        """Test _extract_docstring_parts with simple docstring."""
        docstring = "This is a function description."
        desc, params = _extract_docstring_parts(docstring)
        assert desc == "This is a function description."
        assert params == {}

    def test_extract_docstring_parts_with_params(self):
        """Test _extract_docstring_parts with parameters."""
        docstring = """This is a function description.

        Args:
            param1: Description of param1
            param2: Description of param2
        """
        desc, params = _extract_docstring_parts(docstring)
        assert desc == "This is a function description."
        assert "param1" in params
        assert "param2" in params
        assert "Description of param1" in params["param1"]
        assert "Description of param2" in params["param2"]

    def test_extract_docstring_parts_multiline_params(self):
        """Test _extract_docstring_parts with multiline parameter descriptions."""
        docstring = """This is a function description.

        Args:
            param1: Description of param1
                that spans multiple lines
            param2: Description of param2
        """
        desc, params = _extract_docstring_parts(docstring)
        assert desc == "This is a function description."
        assert "param1" in params
        assert "that spans multiple lines" in params["param1"]

    def test_pydantic_model_to_schema(self):  # Test private function indirectly
        """Test _pydantic_model_to_schema function."""

        class User(BaseModel):
            name: str
            age: int
            email: Optional[str] = None

        raw_schema = pydantic_model_to_openai_schema(
            User,
            function_name="test_user_func",
            function_description="Test user function description",
        )
        # The actual schema for parameters is nested
        assert raw_schema["type"] == "function"
        assert "function" in raw_schema
        assert raw_schema["function"]["name"] == "test_user_func"
        assert raw_schema["function"]["description"] == "Test user function description"

        schema = raw_schema["function"]["parameters"]

        assert schema["type"] == "object"
        assert "properties" in schema
        assert "name" in schema["properties"]
        assert "age" in schema["properties"]
        assert "email" in schema["properties"]
        assert "required" in schema
        assert "name" in schema["required"]
        assert "age" in schema["required"]
        assert "email" not in schema["required"]

    def test_function_to_openai_schema_simple(self):
        """Test function_to_openai_schema with a simple function."""

        def sample_function(a: int, b: str) -> bool:
            """Sample function for testing.

            Args:
                a: An integer parameter
                b: A string parameter

            Returns:
                A boolean result
            """
            return True

        schema = function_to_openai_schema(sample_function)

        assert schema["name"] == "sample_function"
        assert "Sample function for testing" in schema["description"]
        assert "parameters" in schema
        assert schema["parameters"]["type"] == "object"
        assert "properties" in schema["parameters"]
        assert "a" in schema["parameters"]["properties"]
        assert "b" in schema["parameters"]["properties"]
        assert schema["parameters"]["properties"]["a"]["type"] == "integer"
        assert schema["parameters"]["properties"]["b"]["type"] == "string"
        assert "required" in schema["parameters"]
        assert "a" in schema["parameters"]["required"]
        assert "b" in schema["parameters"]["required"]

    def test_function_to_openai_schema_with_defaults(self):
        """Test function_to_openai_schema with default parameters."""

        def sample_function(a: int, b: str = "default") -> bool:
            """Sample function with default parameter."""
            return True

        schema = function_to_openai_schema(sample_function)

        assert "a" in schema["parameters"]["required"]
        assert "b" not in schema["parameters"]["required"]

    def test_function_to_openai_schema_complex_types(self):
        """Test function_to_openai_schema with complex parameter types."""

        def complex_function(
            a: list[int],
            b: dict[str, Any],
            c: Optional[str] = None,
            d: Union[int, str] = 0,
        ) -> dict[str, Any]:
            """Complex function with various parameter types."""
            return {}

        schema = function_to_openai_schema(complex_function)

        assert schema["parameters"]["properties"]["a"]["type"] == "array"
        assert schema["parameters"]["properties"]["b"]["type"] == "object"
        assert schema["parameters"]["properties"]["c"]["type"] == "string"
        assert schema["parameters"]["properties"]["d"]["type"] == "any"
        assert "a" in schema["parameters"]["required"]
        assert "b" in schema["parameters"]["required"]
        assert "c" not in schema["parameters"]["required"]
        assert "d" not in schema["parameters"]["required"]

    def test_function_to_openai_schema_with_pydantic_model(self):
        """Test function_to_openai_schema with Pydantic model parameter."""

        class UserModel(BaseModel):
            name: str
            age: int
            email: Optional[str] = None
            tags: list[str] = Field(default_factory=list)

        def create_user(user: UserModel) -> dict:
            """Create a new user."""
            return {}

        schema = function_to_openai_schema(create_user)

        assert schema["name"] == "create_user"
        assert "parameters" in schema
        assert "user" in schema["parameters"]["properties"]
        assert "required" in schema["parameters"]
        assert "user" in schema["parameters"]["required"]

    def test_function_to_openai_schema_with_self_cls(self):
        """Test function_to_openai_schema with self/cls parameters."""

        class TestClass:
            def instance_method(self, a: int, b: str) -> bool:
                """Instance method."""
                return True

            @classmethod
            def class_method(cls, a: int, b: str) -> bool:
                """Class method."""
                return True

        # Instance method
        schema = function_to_openai_schema(TestClass.instance_method)
        assert "parameters" in schema
        assert "a" in schema["parameters"]["properties"]
        assert "b" in schema["parameters"]["properties"]
        assert "self" not in schema["parameters"]["properties"]

        # Class method
        schema = function_to_openai_schema(TestClass.class_method)
        assert "parameters" in schema
        assert "a" in schema["parameters"]["properties"]
        assert "b" in schema["parameters"]["properties"]
        assert "cls" not in schema["parameters"]["properties"]

    def test_function_to_openai_schema_without_annotations(self):
        """Test function_to_openai_schema with function without type annotations."""

        def untyped_function(a, b=None):
            """Untyped function."""
            return True

        schema = function_to_openai_schema(untyped_function)

        assert schema["name"] == "untyped_function"
        assert "parameters" in schema
        assert "a" in schema["parameters"]["properties"]
        assert "b" in schema["parameters"]["properties"]
        assert "a" in schema["parameters"]["required"]
        assert "b" not in schema["parameters"]["required"]
