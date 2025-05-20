"""Tests for the parsers module."""

import json
import logging
import pytest

from lionfuncs.parsers import _fix_json_string, fuzzy_parse_json


class TestFuzzyParseJson:
    """Tests for fuzzy_parse_json and related functions."""

    @pytest.mark.parametrize(
        "json_string,expected",
        [
            ('{"name": "John", "age": 30}', {"name": "John", "age": 30}),
            ('{"name": "John", "age": 30, "is_active": true}', {"name": "John", "age": 30, "is_active": True}),
            ('{"name": "John", "age": 30, "data": null}', {"name": "John", "age": 30, "data": None}),
            ('{"name": "John", "tags": ["a", "b", "c"]}', {"name": "John", "tags": ["a", "b", "c"]}),
            ('{"name": "John", "address": {"city": "New York"}}', {"name": "John", "address": {"city": "New York"}}),
        ],
    )
    def test_fuzzy_parse_json_valid(self, json_string, expected):
        """Test fuzzy_parse_json with valid JSON."""
        result = fuzzy_parse_json(json_string)
        assert result == expected

    @pytest.mark.parametrize(
        "malformed_json,expected",
        [
            ("{'name': 'John', 'age': 30}", {"name": "John", "age": 30}),  # Single quotes
            ('{"name": "John", "age": 30,}', {"name": "John", "age": 30}),  # Trailing comma
            ('{"name": "John", "age": None}', {"name": "John", "age": None}),  # Python None
            ('{"name": "John", "age": True}', {"name": "John", "age": True}),  # Python True
            ('{"name": "John", "age": False}', {"name": "John", "age": False}),  # Python False
            ('{name: "John", age: 30}', {"name": "John", "age": 30}),  # Unquoted keys
        ],
    )
    def test_fuzzy_parse_json_common_errors(self, malformed_json, expected):
        """Test fuzzy_parse_json with common JSON errors."""
        result = fuzzy_parse_json(malformed_json, attempt_fix=True)
        assert result == expected

    def test_fuzzy_parse_json_strict_mode(self):
        """Test fuzzy_parse_json in strict mode."""
        # Valid JSON should parse in strict mode
        valid_json = '{"name": "John"}'
        assert fuzzy_parse_json(valid_json, strict=True) == {"name": "John"}

        # Invalid JSON should raise in strict mode
        invalid_json = "{'name': 'John'}"
        with pytest.raises(ValueError):
            fuzzy_parse_json(invalid_json, attempt_fix=False, strict=True)

        # Invalid JSON should parse with attempt_fix=True even in strict mode
        assert fuzzy_parse_json(invalid_json, attempt_fix=True, strict=True) == {"name": "John"}

    def test_fuzzy_parse_json_empty_input(self):
        """Test fuzzy_parse_json with empty input."""
        # Empty string should return None in non-strict mode
        assert fuzzy_parse_json("") is None
        assert fuzzy_parse_json("   ") is None

        # Empty string should raise in strict mode
        with pytest.raises(ValueError):
            fuzzy_parse_json("", strict=True)

    def test_fuzzy_parse_json_invalid_input_type(self):
        """Test fuzzy_parse_json with invalid input type."""
        with pytest.raises(TypeError):
            fuzzy_parse_json(123)
        with pytest.raises(TypeError):
            fuzzy_parse_json(None)
        with pytest.raises(TypeError):
            fuzzy_parse_json([])

    def test_fuzzy_parse_json_logging(self, caplog):
        """Test fuzzy_parse_json with logging enabled."""
        caplog.set_level(logging.WARNING)
        
        # Invalid JSON should log warnings when log_errors=True
        invalid_json = "{'name': 'John', invalid}"
        result = fuzzy_parse_json(invalid_json, attempt_fix=True, log_errors=True)
        
        # Should still return None for unparseable JSON
        assert result is None
        
        # Should have logged warnings
        assert len(caplog.records) > 0
        assert any("JSON parsing failed" in record.message for record in caplog.records)

    @pytest.mark.parametrize(
        "input_str,expected",
        [
            ("{'key': 'value'}", '{"key": "value"}'),  # Single quotes to double quotes
            ('{"key": "value",}', '{"key": "value"}'),  # Trailing comma
            ('{"key": True}', '{"key": true}'),  # Python True to JSON true
            ('{"key": False}', '{"key": false}'),  # Python False to JSON false
            ('{"key": None}', '{"key": null}'),  # Python None to JSON null
            ('{key: "value"}', '{"key": "value"}'),  # Unquoted keys
        ],
    )
    def test_fix_json_string(self, input_str, expected):
        """Test _fix_json_string function."""
        result = _fix_json_string(input_str)
        
        # Parse both to compare the actual JSON content
        expected_json = json.loads(expected)
        result_json = json.loads(result)
        
        assert result_json == expected_json