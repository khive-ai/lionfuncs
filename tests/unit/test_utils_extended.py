"""
Extended unit tests for the utils module to increase coverage.
"""

import pytest
from enum import Enum
from pydantic import BaseModel
from pydantic_core import PydanticUndefined

from lionfuncs import utils


# Test cases for to_list
class SampleEnum(Enum):
    A = "a"
    B = "b"


class SampleModel(BaseModel):
    name: str
    value: int


def test_hash_dict_with_mapping():
    """Test hash_dict with a mapping."""
    d1 = {"a": 1, "b": 2}
    d2 = {"b": 2, "a": 1}  # Same content, different order
    
    # Same dictionaries should have the same hash
    assert utils.hash_dict(d1) == utils.hash_dict(d2)
    
    d3 = {"a": 1, "c": 3}  # Different content
    assert utils.hash_dict(d1) != utils.hash_dict(d3)


def test_to_list_with_none():
    """Test to_list with None input."""
    result = utils.to_list(None)
    assert result == []


def test_to_list_with_pydantic_undefined():
    """Test to_list with PydanticUndefined input."""
    result = utils.to_list(PydanticUndefined)
    assert result == []


def test_to_list_with_enum_class():
    """Test to_list with an Enum class."""
    result = utils.to_list(SampleEnum)
    assert len(result) == 2
    assert SampleEnum.A in result
    assert SampleEnum.B in result
    
    # With use_values=True
    result_values = utils.to_list(SampleEnum, use_values=True)
    assert len(result_values) == 2
    assert "a" in result_values
    assert "b" in result_values


def test_to_list_with_mapping():
    """Test to_list with a mapping."""
    d = {"a": 1, "b": 2}
    
    # Default behavior (treat as single item)
    result = utils.to_list(d)
    assert result == [d]
    
    # With use_values=True
    result_values = utils.to_list(d, use_values=True)
    assert result_values == [1, 2]


def test_to_list_with_pydantic_model():
    """Test to_list with a Pydantic model."""
    model = SampleModel(name="test", value=42)
    result = utils.to_list(model)
    assert result == [model]


def test_to_list_with_unique_and_unhashable():
    """Test to_list with unique=True and unhashable types."""
    # List of lists (unhashable)
    data = [[1, 2], [3, 4], [1, 2]]  # Duplicate [1, 2]
    result = utils.to_list(data, flatten=True, unique=True)
    # The implementation flattens the lists, so we need to check for individual elements
    assert 1 in result
    assert 2 in result
    assert 3 in result
    assert 4 in result
    
    # List of dicts (unhashable)
    data = [{"a": 1}, {"b": 2}, {"a": 1}]  # Duplicate {"a": 1}
    result = utils.to_list(data, flatten=True, unique=True)
    assert len(result) == 2
    assert {"a": 1} in result
    assert {"b": 2} in result
    
    # List of sets (unhashable)
    data = [{1, 2}, {3, 4}, {1, 2}]  # Duplicate {1, 2}
    result = utils.to_list(data, flatten=True, unique=True)
    assert len(result) == 2
    assert {1, 2} in result
    assert {3, 4} in result


def test_to_list_with_pydantic_model_unique():
    """Test to_list with unique=True and Pydantic models."""
    model1 = SampleModel(name="test", value=42)
    model2 = SampleModel(name="test", value=42)  # Same content
    model3 = SampleModel(name="other", value=99)  # Different content
    
    data = [model1, model2, model3]
    result = utils.to_list(data, flatten=True, unique=True)
    
    # Should deduplicate model1 and model2
    assert len(result) == 2
    
    # Check if model3 is in the result
    assert any(m.name == "other" and m.value == 99 for m in result)


def test_to_list_with_flatten_tuple_set():
    """Test to_list with flatten_tuple_set=True."""
    data = [1, (2, 3), {4, 5}]
    
    # Default behavior (don't flatten tuples and sets)
    result = utils.to_list(data, flatten=True)
    assert result == [1, (2, 3), {4, 5}]
    
    # With flatten_tuple_set=True
    result_flatten = utils.to_list(data, flatten=True, flatten_tuple_set=True)
    assert sorted(result_flatten) == [1, 2, 3, 4, 5]


def test_to_list_with_dropna():
    """Test to_list with dropna=True."""
    data = [1, None, 2, PydanticUndefined, 3]
    
    # Default behavior
    result = utils.to_list(data)
    assert result == [1, None, 2, PydanticUndefined, 3]
    
    # With dropna=True
    result_dropna = utils.to_list(data, dropna=True)
    assert result_dropna == [1, 2, 3]


def test_to_list_with_nested_iterables():
    """Test to_list with nested iterables."""
    data = [1, [2, [3, 4]], 5]
    
    # Default behavior (don't flatten)
    result = utils.to_list(data)
    assert result == [1, [2, [3, 4]], 5]
    
    # With flatten=True
    result_flatten = utils.to_list(data, flatten=True)
    assert result_flatten == [1, 2, 3, 4, 5]


def test_to_list_with_unique_requires_flatten():
    """Test that to_list raises ValueError when unique=True without flatten=True."""
    with pytest.raises(ValueError, match="unique=True requires flatten=True"):
        utils.to_list([1, 2, 1], unique=True, flatten=False)