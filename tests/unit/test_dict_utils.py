"""Tests for the dict_utils module."""

import pytest

from lionfuncs.dict_utils import fuzzy_match_keys


class TestFuzzyMatchKeys:
    """Tests for fuzzy_match_keys function."""

    def test_fuzzy_match_keys_exact_matches(self):
        """Test fuzzy_match_keys with exact matches."""
        data = {"name": "John", "age": 30, "city": "New York"}
        reference_keys = ["name", "age", "city"]

        result = fuzzy_match_keys(data, reference_keys)

        assert result == data

    def test_fuzzy_match_keys_case_sensitivity(self):
        """Test fuzzy_match_keys with case sensitivity."""
        data = {"Name": "John", "Age": 30, "City": "New York"}
        reference_keys = ["name", "age", "city"]

        # With case sensitivity, should not match (using a high threshold to prevent fuzzy match of "Name" to "name")
        result = fuzzy_match_keys(
            data, reference_keys, case_sensitive=True, threshold=0.99
        )
        assert (
            "Name" in result
        )  # Original keys preserved because "Name" didn't exactly or fuzzily match "name"
        assert "name" not in result  # "name" (lowercase) should not be a key

        # Without case sensitivity, should match
        result = fuzzy_match_keys(data, reference_keys, case_sensitive=False)
        assert "name" in result  # Keys corrected to reference
        assert "Name" not in result

    def test_fuzzy_match_keys_fuzzy_matches(self):
        """Test fuzzy_match_keys with fuzzy matches."""
        data = {"nmae": "John", "aeg": 30, "ctiy": "New York"}
        reference_keys = ["name", "age", "city"]

        # With high threshold, should not match
        result = fuzzy_match_keys(data, reference_keys, threshold=0.9)
        assert "nmae" in result  # Original keys preserved
        assert "name" not in result

        # With lower threshold, should match some keys
        # Note: The actual behavior depends on the similarity algorithm
        # and the specific implementation of fuzzy_match_keys
        result = fuzzy_match_keys(data, reference_keys, threshold=0.5)
        # At least one key should be matched with a low threshold
        assert any(key in result for key in reference_keys)

    @pytest.mark.parametrize(
        "algorithm",
        ["levenshtein", "jaro_winkler", "wratio"],  # Changed sequence_matcher to wratio
    )
    def test_fuzzy_match_keys_algorithms(self, algorithm):
        """Test fuzzy_match_keys with different similarity algorithms."""
        data = {"nmae": "John", "aeg": 30, "ctiy": "New York"}
        reference_keys = ["name", "age", "city"]

        result = fuzzy_match_keys(
            data, reference_keys, default_method=algorithm, threshold=0.5
        )

        # With a lower threshold, at least one key should be matched
        assert any(key in result for key in reference_keys)

    def test_fuzzy_match_keys_handle_unmatched_ignore(self):
        """Test fuzzy_match_keys with handle_unmatched='ignore'."""
        data = {"name": "John", "age": 30, "extra": "value"}
        reference_keys = ["name", "age", "city"]

        result = fuzzy_match_keys(data, reference_keys, handle_unmatched="ignore")

        assert "name" in result
        assert "age" in result
        assert "extra" in result  # Unmatched key preserved
        assert "city" not in result  # Missing reference key not added

    def test_fuzzy_match_keys_handle_unmatched_raise(self):
        """Test fuzzy_match_keys with handle_unmatched='raise'."""
        data = {"name": "John", "age": 30, "extra": "value"}
        reference_keys = ["name", "age", "city"]

        with pytest.raises(ValueError) as excinfo:
            fuzzy_match_keys(data, reference_keys, handle_unmatched="raise")

        assert "Unmatched keys found" in str(excinfo.value)
        assert "extra" in str(excinfo.value)

    def test_fuzzy_match_keys_handle_unmatched_remove(self):
        """Test fuzzy_match_keys with handle_unmatched='remove'."""
        data = {"name": "John", "age": 30, "extra": "value"}
        reference_keys = ["name", "age", "city"]

        result = fuzzy_match_keys(data, reference_keys, handle_unmatched="remove")

        assert "name" in result
        assert "age" in result
        assert "extra" not in result  # Unmatched key removed
        assert "city" not in result  # Missing reference key not added

    def test_fuzzy_match_keys_handle_unmatched_fill(self):
        """Test fuzzy_match_keys with handle_unmatched='fill'."""
        data = {"name": "John", "age": 30, "extra": "value"}
        reference_keys = ["name", "age", "city"]

        result = fuzzy_match_keys(
            data, reference_keys, handle_unmatched="fill", fill_value="default"
        )

        assert "name" in result
        assert "age" in result
        assert "extra" in result  # Unmatched key preserved
        assert "city" in result  # Missing reference key added
        assert result["city"] == "default"  # With default value

    def test_fuzzy_match_keys_handle_unmatched_force(self):
        """Test fuzzy_match_keys with handle_unmatched='force'."""
        data = {"name": "John", "age": 30, "extra": "value"}
        reference_keys = ["name", "age", "city"]

        result = fuzzy_match_keys(
            data, reference_keys, handle_unmatched="force", fill_value="default"
        )

        assert "name" in result
        assert "age" in result
        assert "extra" not in result  # Unmatched key removed
        assert "city" in result  # Missing reference key added
        assert result["city"] == "default"  # With default value

    def test_fuzzy_match_keys_fill_mapping(self):
        """Test fuzzy_match_keys with fill_mapping."""
        data = {"name": "John", "age": 30}
        reference_keys = ["name", "age", "city", "country"]
        fill_mapping = {"city": "New York", "country": "USA"}

        result = fuzzy_match_keys(
            data,
            reference_keys,
            handle_unmatched="fill",
            fill_value="default",
            fill_mapping=fill_mapping,
        )

        assert result["city"] == "New York"
        assert result["country"] == "USA"

    def test_fuzzy_match_keys_strict_mode(self):
        """Test fuzzy_match_keys with strict=True."""
        data = {"name": "John", "age": 30}
        reference_keys = ["name", "age", "city"]

        # Without strict, missing keys are allowed
        result = fuzzy_match_keys(data, reference_keys)
        assert "name" in result
        assert "age" in result
        assert "city" not in result

        # With strict, missing keys raise error
        with pytest.raises(ValueError) as excinfo:
            fuzzy_match_keys(data, reference_keys, strict=True)

        assert "Missing required keys" in str(excinfo.value)
        assert "city" in str(excinfo.value)

    def test_fuzzy_match_keys_dict_reference(self):
        """Test fuzzy_match_keys with dictionary reference."""
        data = {"name": "John", "age": 30}
        reference_keys = {"name": str, "age": int, "city": str}

        result = fuzzy_match_keys(data, reference_keys)

        assert "name" in result
        assert "age" in result
        assert "city" not in result

    def test_fuzzy_match_keys_input_validation(self):
        """Test fuzzy_match_keys input validation."""
        # First argument must be a dictionary
        with pytest.raises(TypeError):
            fuzzy_match_keys("not a dict", ["name"])

        # Reference keys cannot be None
        with pytest.raises(TypeError):
            fuzzy_match_keys({}, None)

        # Threshold must be between 0 and 1
        with pytest.raises(ValueError):
            fuzzy_match_keys({}, [], threshold=1.5)

        # Empty reference keys returns copy of input
        data = {"name": "John"}
        result = fuzzy_match_keys(data, [])
        assert result == data
        assert result is not data  # Should be a copy
