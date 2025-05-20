"""Tests for the format_utils module."""

import json
from unittest.mock import patch

import pytest
from pydantic import BaseModel

from lionfuncs.format_utils import _format_dict_yaml_like, _is_in_notebook, as_readable


class TestFormatUtils:
    """Tests for format_utils module."""

    def test_is_in_notebook_not_in_notebook(self):
        """Test _is_in_notebook when not in a notebook."""
        # Default case - not in a notebook
        assert not _is_in_notebook()

    def test_is_in_notebook_import_error(self):
        """Test _is_in_notebook when IPython import fails."""
        with patch("builtins.__import__", side_effect=ImportError):
            assert not _is_in_notebook()

    def test_is_in_notebook_in_notebook(self):
        """Test _is_in_notebook when in a notebook."""
        # Mock IPython and ZMQInteractiveShell
        class MockShellClass:
            __name__ = 'ZMQInteractiveShell'

        class MockShell:
            # This property is what _is_in_notebook actually checks
            __class__ = MockShellClass

        class MockIPython:
            @staticmethod
            def get_ipython():
                # Return an instance of MockShell, not the class itself
                return MockShell()
        
        with patch("lionfuncs.format_utils.get_ipython", MockIPython.get_ipython, create=True):
            assert _is_in_notebook()

    def test_is_in_notebook_in_terminal(self):
        """Test _is_in_notebook when in IPython terminal."""
        # Mock IPython but not in notebook
        class MockIPython:
            @staticmethod
            def get_ipython():
                class Shell:
                    def has_trait(self, trait):
                        return False
                return Shell()

        with patch("lionfuncs.format_utils.get_ipython", MockIPython.get_ipython, create=True):
            assert not _is_in_notebook()

    def test_format_dict_yaml_like_simple_dict(self):
        """Test _format_dict_yaml_like with a simple dictionary."""
        data = {"name": "John", "age": 30}
        result = _format_dict_yaml_like(data)
        
        assert "name: John" in result
        assert "age: 30" in result

    def test_format_dict_yaml_like_nested_dict(self):
        """Test _format_dict_yaml_like with a nested dictionary."""
        data = {
            "name": "John",
            "address": {
                "city": "New York",
                "zip": "10001"
            }
        }
        result = _format_dict_yaml_like(data)
        
        assert "name: John" in result
        assert "address:" in result
        assert "city: New York" in result
        assert "zip: 10001" in result

    def test_format_dict_yaml_like_with_list(self):
        """Test _format_dict_yaml_like with a list."""
        data = ["a", "b", "c"]
        result = _format_dict_yaml_like(data)
        
        assert "- a" in result
        assert "- b" in result
        assert "- c" in result

    def test_format_dict_yaml_like_dict_with_list(self):
        """Test _format_dict_yaml_like with a dictionary containing a list."""
        data = {
            "name": "John",
            "tags": ["a", "b", "c"]
        }
        result = _format_dict_yaml_like(data)
        
        assert "name: John" in result
        assert "tags:" in result
        assert "- a" in result
        assert "- b" in result
        assert "- c" in result

    def test_format_dict_yaml_like_multiline_string(self):
        """Test _format_dict_yaml_like with a multiline string."""
        data = {
            "name": "John",
            "bio": "This is\na multi-line\nstring"
        }
        result = _format_dict_yaml_like(data)
        
        assert "name: John" in result
        assert "bio: |" in result
        assert "This is" in result
        assert "multi-line" in result
        assert "string" in result

    def test_format_dict_yaml_like_empty_containers(self):
        """Test _format_dict_yaml_like with empty containers."""
        # Empty dict
        assert _format_dict_yaml_like({}) == "{}"
        
        # Empty list
        assert "[]" in _format_dict_yaml_like([])
        
        # Dict with empty list
        result = _format_dict_yaml_like({"tags": []})
        assert "tags: []" in result

    def test_format_dict_yaml_like_max_depth(self):
        """Test _format_dict_yaml_like with max_depth."""
        data = {
            "level1": {
                "level2": {
                    "level3": {
                        "level4": "value"
                    }
                }
            }
        }
        
        # With unlimited depth
        result = _format_dict_yaml_like(data)
        assert "level1:" in result
        assert "level2:" in result
        assert "level3:" in result
        assert "level4: value" in result
        
        # With max_depth=2
        result = _format_dict_yaml_like(data, max_depth=2)
        assert "level1:" in result
        assert "level2:" in result
        assert "..." in result
        assert "level4: value" not in result

    def test_as_readable_auto_format(self):
        """Test as_readable with auto format."""
        data = {"name": "John", "age": 30}
        result = as_readable(data)
        
        # Default is yaml_like
        assert "name: John" in result
        assert "age: 30" in result

    def test_as_readable_yaml_like_format(self):
        """Test as_readable with yaml_like format."""
        data = {"name": "John", "age": 30}
        result = as_readable(data, format_type="yaml_like")
        
        assert "name: John" in result
        assert "age: 30" in result

    def test_as_readable_json_format(self):
        """Test as_readable with json format."""
        data = {"name": "John", "age": 30}
        result = as_readable(data, format_type="json")
        
        # Should be valid JSON
        parsed = json.loads(result)
        assert parsed == data

    def test_as_readable_repr_format(self):
        """Test as_readable with repr format."""
        data = {"name": "John", "age": 30}
        result = as_readable(data, format_type="repr")
        
        assert result == repr(data)

    def test_as_readable_invalid_format(self):
        """Test as_readable with invalid format."""
        data = {"name": "John", "age": 30}
        with pytest.raises(ValueError):
            as_readable(data, format_type="invalid")

    def test_as_readable_indent(self):
        """Test as_readable with custom indent."""
        data = {"name": "John", "age": 30}
        
        # Default indent (2)
        default_result = as_readable(data, indent=2) # Explicitly set default indent
        
        # Custom indent (4)
        custom_result = as_readable(data, indent=4)

        # Custom indent should have more spaces
        # Check for actual space difference by comparing lines
        default_lines = default_result.split('\n')
        custom_lines = custom_result.split('\n')

        # Find the line with "age: 30" and check its indentation
        default_age_line = next(line for line in default_lines if "age: 30" in line)
        custom_age_line = next(line for line in custom_lines if "age: 30" in line)

        assert custom_age_line.startswith(" " * 4) # 4 spaces for indent=4
        assert default_age_line.startswith(" " * 2) # 2 spaces for indent=2
        assert len(custom_result) > len(default_result)


    def test_as_readable_max_depth(self):
        """Test as_readable with max_depth."""
        data = {
            "level1": {
                "level2": {
                    "level3": "value"
                }
            }
        }
        
        # With max_depth=1
        result = as_readable(data, max_depth=1)
        assert "level1:" in result
        assert "..." in result
        assert "level3: value" not in result

    def test_as_readable_with_pydantic_model(self):
        """Test as_readable with a Pydantic model."""
        class User(BaseModel):
            name: str
            age: int

        user = User(name="John", age=30)
        result = as_readable(user)
        
        assert "name: John" in result
        assert "age: 30" in result

    def test_as_readable_with_primitive_types(self):
        """Test as_readable with primitive types."""
        # String
        assert as_readable("test") == "test"
        
        # Number
        assert as_readable(123) == "123"
        
        # Boolean
        assert as_readable(True) == "True"
        
        # None
        assert as_readable(None) == "None"

    def test_as_readable_notebook_override(self):
        """Test as_readable with notebook override."""
        data = {"name": "John", "age": 30}
        
        # Test with override=True (should not affect string output)
        result = as_readable(data, in_notebook_override=True)
        assert "name: John" in result
        assert "age: 30" in result
        
        # Test with override=False (should not affect string output)
        result = as_readable(data, in_notebook_override=False)
        assert "name: John" in result
        assert "age: 30" in result