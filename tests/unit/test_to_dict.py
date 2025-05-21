"""Tests for the to_dict function in utils module."""

from dataclasses import dataclass, field
from typing import Optional

import pytest
from pydantic import BaseModel, Field

from lionfuncs.to_dict import to_dict


class TestToDict:
    """Tests for to_dict function."""

    def test_to_dict_pydantic_model(self):
        """Test to_dict with Pydantic models."""

        class User(BaseModel):
            name: str
            age: int
            email: Optional[str] = None
            tags: list[str] = Field(default_factory=list)

        user = User(name="John", age=30, email="john@example.com", tags=["a", "b"])
        result = to_dict(user)

        assert result == {
            "name": "John",
            "age": 30,
            "email": "john@example.com",
            "tags": ["a", "b"],
        }

    def test_to_dict_pydantic_model_options(self):
        """Test to_dict with Pydantic models and various options."""

        class User(BaseModel):
            name: str
            age: int
            email: Optional[str] = None
            internal_id: str = "default"

        user = User(name="John", age=30, email="john@example.com")

        # Test fields option
        result = to_dict(user, fields=["name", "age"])
        assert "name" in result
        assert "age" in result
        assert "email" not in result
        assert "internal_id" not in result

        # Test exclude option
        result = to_dict(user, exclude=["internal_id"])
        assert "name" in result
        assert "age" in result
        assert "email" in result
        assert "internal_id" not in result

        # Test exclude_none option
        user.email = None
        result = to_dict(user, exclude_none=True)
        assert "email" not in result

        # Test exclude_defaults option
        result = to_dict(user, exclude_defaults=True)
        assert "internal_id" not in result

    def test_to_dict_nested_pydantic_models(self):
        """Test to_dict with nested Pydantic models."""

        class Address(BaseModel):
            city: str
            country: str

        class User(BaseModel):
            name: str
            address: Address

        user = User(name="John", address=Address(city="New York", country="USA"))
        result = to_dict(user)

        assert result == {
            "name": "John",
            "address": {"city": "New York", "country": "USA"},
        }

    def test_to_dict_dataclass(self):
        """Test to_dict with dataclasses."""

        @dataclass
        class User:
            name: str
            age: int
            tags: list[str] = field(default_factory=list)

        user = User(name="John", age=30, tags=["a", "b"])
        result = to_dict(user)

        assert result == {"name": "John", "age": 30, "tags": ["a", "b"]}

    def test_to_dict_nested_dataclass(self):
        """Test to_dict with nested dataclasses."""

        @dataclass
        class Address:
            city: str
            country: str

        @dataclass
        class User:
            name: str
            address: Address

        user = User(name="John", address=Address(city="New York", country="USA"))
        result = to_dict(user)

        assert result == {
            "name": "John",
            "address": {"city": "New York", "country": "USA"},
        }

    def test_to_dict_dict(self):
        """Test to_dict with dictionaries."""
        data = {"name": "John", "age": 30, "tags": ["a", "b"]}
        result = to_dict(data)
        assert result == data

    def test_to_dict_nested_dict(self):
        """Test to_dict with nested dictionaries."""
        data = {
            "name": "John",
            "address": {"city": "New York", "country": "USA"},
            "tags": ["a", "b"],
        }
        result = to_dict(data)
        assert result == data

    def test_to_dict_list(self):
        """Test to_dict with lists."""
        data = ["a", "b", "c"]
        result = to_dict(data)
        assert result == data

    def test_to_dict_nested_list(self):
        """Test to_dict with nested lists."""
        data = [{"name": "John", "age": 30}, {"name": "Jane", "age": 25}]
        result = to_dict(data)
        assert result == data

    def test_to_dict_primitive_types(self):
        """Test to_dict with primitive types."""
        assert to_dict("string") == "string"
        assert to_dict(123) == 123
        assert to_dict(123.45) == 123.45
        assert to_dict(True) is True
        assert to_dict(None) is None

    def test_to_dict_general_object(self):
        """Test to_dict with general objects."""

        class User:
            def __init__(self, name, age):
                self.name = name
                self.age = age

        user = User("John", 30)
        result = to_dict(user)
        assert result == {"name": "John", "age": 30}

    def test_to_dict_unconvertible_type(self):
        """Test to_dict with unconvertible types."""

        # Create an object without __dict__ that can't be converted to dict
        class Unconvertible:
            __slots__ = ()

            def __repr__(self):
                return "Unconvertible()"

        obj = Unconvertible()
        with pytest.raises(TypeError):
            to_dict(obj)

    def test_to_dict_mixed_types(self):
        """Test to_dict with mixed types."""

        @dataclass
        class Address:
            city: str
            country: str

        class User(BaseModel):
            name: str
            address: Address
            tags: list[str] = []

        user = User(
            name="John",
            address=Address(city="New York", country="USA"),
            tags=["a", "b"],
        )
        result = to_dict(user)

        assert result == {
            "name": "John",
            "address": {"city": "New York", "country": "USA"},
            "tags": ["a", "b"],
        }
