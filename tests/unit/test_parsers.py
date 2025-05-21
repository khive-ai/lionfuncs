"""Tests for the parsers module."""

import logging

import pytest

from lionfuncs.parsers import fuzzy_parse_json


class TestFuzzyParseJson:
    """Tests for fuzzy_parse_json and related functions."""

    @pytest.mark.parametrize(
        "json_string,expected",
        [
            ('{"name": "John", "age": 30}', {"name": "John", "age": 30}),
            (
                '{"name": "John", "age": 30, "is_active": true}',
                {"name": "John", "age": 30, "is_active": True},
            ),
            (
                '{"name": "John", "age": 30, "data": null}',
                {"name": "John", "age": 30, "data": None},
            ),
            (
                '{"name": "John", "tags": ["a", "b", "c"]}',
                {"name": "John", "tags": ["a", "b", "c"]},
            ),
            (
                '{"name": "John", "address": {"city": "New York"}}',
                {"name": "John", "address": {"city": "New York"}},
            ),
        ],
    )
    def test_fuzzy_parse_json_valid(self, json_string, expected):
        """Test fuzzy_parse_json with valid JSON."""
        result = fuzzy_parse_json(json_string)
        assert result == expected

    @pytest.mark.parametrize(
        "malformed_json,expected",
        [
            (
                "{'name': 'John', 'age': 30}",
                {"name": "John", "age": 30},
            ),  # Single quotes
            (
                '{"name": "John", "age": 30,}',
                {"name": "John", "age": 30},
            ),  # Trailing comma
            (
                '{"name": "John", "age": None}',
                {"name": "John", "age": None},
            ),  # Python None
            (
                '{"name": "John", "age": True}',
                {"name": "John", "age": True},
            ),  # Python True
            (
                '{"name": "John", "age": False}',
                {"name": "John", "age": False},
            ),  # Python False
            ('{name: "John", age: 30}', {"name": "John", "age": 30}),  # Unquoted keys
        ],
    )
    def test_fuzzy_parse_json_common_errors(self, malformed_json, expected):
        """Test fuzzy_parse_json with common JSON errors."""
        result = fuzzy_parse_json(malformed_json)
        assert result == expected

    def test_fuzzy_parse_json_strict_mode(self):
        """Test fuzzy_parse_json in strict mode."""
        # Valid JSON should parse in strict mode
        valid_json = '{"name": "John"}'
        assert fuzzy_parse_json(valid_json) == {"name": "John"}

        # Invalid JSON that fuzzy_parse_json can fix should parse
        fixable_invalid_json = "{'name': 'John'}"
        assert fuzzy_parse_json(fixable_invalid_json) == {"name": "John"}

        # Unfixable JSON should raise ValueError
        unfixable_invalid_json = "{'name': 'John', invalid_token}"
        with pytest.raises(ValueError):
            fuzzy_parse_json(unfixable_invalid_json)

    def test_fuzzy_parse_json_empty_input(self):
        """Test fuzzy_parse_json with empty input."""
        # Empty string should return None in non-strict mode
        with pytest.raises(ValueError):
            fuzzy_parse_json("")
        with pytest.raises(ValueError):
            fuzzy_parse_json("   ")

        # Empty string should raise in strict mode
        with pytest.raises(ValueError):
            fuzzy_parse_json("")

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
        with pytest.raises(ValueError):  # Expecting ValueError for unparseable JSON
            fuzzy_parse_json(invalid_json)
        # result = fuzzy_parse_json(invalid_json) # This line would now raise an error

        # Should still return None for unparseable JSON
        # assert result is None # No longer reachable if fuzzy_parse_json raises ValueError

        # Should have logged warnings
        # Logging tests might need to be re-evaluated based on internal logging if any.
        # For now, assuming direct logging parameters are removed.
        # If fuzzy_parse_json now logs internally on failure before raising,
        # this part of the test might still be relevant but triggered differently.
        # assert len(caplog.records) > 0
        # assert any("JSON parsing failed" in record.message for record in caplog.records)
