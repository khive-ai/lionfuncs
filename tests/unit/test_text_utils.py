"""Tests for the text_utils module."""

import pytest

from lionfuncs.text_utils import (
    _cosine_similarity,
    _hamming_distance,
    _hamming_similarity,
    _jaro_winkler_similarity,
    _levenshtein_distance,
    _levenshtein_similarity,
    _sequence_matcher_similarity,
    string_similarity,
)


class TestStringSimilarity:
    """Tests for string_similarity and related functions."""

    @pytest.mark.parametrize(
        "s1,s2,expected",
        [
            ("kitten", "sitting", 0.5714285714285714),
            ("hello", "hello", 1.0),
            ("", "", 1.0),
            ("", "test", 0.0),
            ("test", "", 0.0),
            ("completely different", "not the same at all", 0.1),
        ],
    )
    def test_levenshtein_similarity(self, s1, s2, expected):
        """Test levenshtein_similarity function."""
        assert _levenshtein_similarity(s1, s2) == pytest.approx(expected)

    @pytest.mark.parametrize(
        "s1,s2,expected",
        [
            ("kitten", "sitting", 3),
            ("hello", "hello", 0),
            ("", "", 0),
            ("", "test", 4),
            ("test", "", 4),
        ],
    )
    def test_levenshtein_distance(self, s1, s2, expected):
        """Test levenshtein_distance function."""
        assert _levenshtein_distance(s1, s2) == expected

    @pytest.mark.parametrize(
        "s1,s2,expected",
        [
            ("hello", "hello", 1.0),
            ("hello", "hallo", 0.8),
            ("", "", 1.0),
            ("", "test", 0.0),
            ("test", "", 0.0),
        ],
    )
    def test_jaro_winkler_similarity(self, s1, s2, expected):
        """Test jaro_winkler_similarity function."""
        assert _jaro_winkler_similarity(s1, s2) == pytest.approx(expected, abs=0.1)

    def test_jaro_winkler_similarity_scaling_factor(self):
        """Test jaro_winkler_similarity with different scaling factors."""
        s1, s2 = "hello", "hallo"
        # Default scaling factor
        default = _jaro_winkler_similarity(s1, s2)
        # Higher scaling factor should increase similarity for strings with common prefix
        higher = _jaro_winkler_similarity(s1, s2, scaling_factor=0.2)
        assert higher > default

        # Invalid scaling factor
        with pytest.raises(ValueError):
            _jaro_winkler_similarity(s1, s2, scaling_factor=0.3)

    @pytest.mark.parametrize(
        "s1,s2,expected",
        [
            ("hello", "hello", 0),
            ("hello", "hallo", 1),
            ("hello", "world", 4),
        ],
    )
    def test_hamming_distance(self, s1, s2, expected):
        """Test hamming_distance function."""
        if len(s1) != len(s2):
            with pytest.raises(ValueError):
                _hamming_distance(s1, s2)
        else:
            assert _hamming_distance(s1, s2) == expected

    @pytest.mark.parametrize(
        "s1,s2,expected",
        [
            ("hello", "hello", 1.0),
            ("hello", "hallo", 0.8),
            ("", "", 1.0),
            ("", "test", 0.0),
            ("test", "", 0.0),
            ("hello", "world", 0.2),
        ],
    )
    def test_hamming_similarity(self, s1, s2, expected):
        """Test hamming_similarity function."""
        if len(s1) != len(s2) and s1 and s2:
            # Skip test for different length strings that aren't empty
            return
        assert _hamming_similarity(s1, s2) == pytest.approx(expected, abs=0.1)

    @pytest.mark.parametrize(
        "s1,s2,expected",
        [
            ("hello world", "hello world", 1.0),
            ("hello world", "world hello", 1.0),  # Same words, different order
            ("hello world", "hello there", 0.5),  # One word in common
            ("", "", 0.0),  # Empty strings
            ("hello", "", 0.0),  # One empty string
        ],
    )
    def test_cosine_similarity(self, s1, s2, expected):
        """Test cosine_similarity function."""
        assert _cosine_similarity(s1, s2) == pytest.approx(expected, abs=0.1)

    @pytest.mark.parametrize(
        "s1,s2,expected",
        [
            ("hello", "hello", 1.0),
            ("hello", "hallo", 0.8),
            ("hello world", "hello there", 0.64),
        ],
    )
    def test_sequence_matcher_similarity(self, s1, s2, expected):
        """Test sequence_matcher_similarity function."""
        assert _sequence_matcher_similarity(s1, s2) == pytest.approx(expected, abs=0.1)

    @pytest.mark.parametrize(
        "method",
        [
            "levenshtein",
            "jaro_winkler",
            "sequence_matcher",
            "cosine",
        ],
    )
    def test_string_similarity_methods(self, method):
        """Test string_similarity with different methods."""
        s1, s2 = "hello", "hallo"
        similarity = string_similarity(s1, s2, method=method)
        assert 0.0 <= similarity <= 1.0

    def test_string_similarity_hamming_method(self):
        """Test string_similarity with hamming method."""
        # Equal length strings
        s1, s2 = "hello", "hallo"
        similarity = string_similarity(s1, s2, method="hamming")
        assert 0.0 <= similarity <= 1.0

        # Different length strings should raise ValueError
        s1, s2 = "hello", "hi"
        with pytest.raises(ValueError):
            string_similarity(s1, s2, method="hamming")

    def test_string_similarity_custom_callable(self):
        """Test string_similarity with custom callable."""

        def custom_similarity(s1, s2):
            return 0.5  # Always return 0.5

        s1, s2 = "hello", "world"
        similarity = string_similarity(s1, s2, method=custom_similarity)
        assert similarity == 0.5

    def test_string_similarity_invalid_method(self):
        """Test string_similarity with invalid method."""
        s1, s2 = "hello", "world"
        with pytest.raises(ValueError):
            string_similarity(s1, s2, method="invalid_method")
