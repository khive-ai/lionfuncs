---
title: "Test Implementation Plan: Integration of .khive/dev/ Utilities into src/lionfuncs"
by: "@khive-implementer"
created: "2025-05-19"
updated: "2025-05-19"
version: "1.0"
doc_type: TI
output_subdir: ti
description: "Test implementation plan for the integration of selected utilities from .khive/dev/ into the src/lionfuncs library"
date: "2025-05-19"
---

# Test Implementation Plan: Integration of .khive/dev/ Utilities

## 1. Overview

### 1.1 Component Under Test

This test implementation plan covers the testing of six utility modules being
integrated from `.khive/dev/` into `src/lionfuncs`:

1. `text_utils.py` - String similarity functions
2. `parsers.py` - Fuzzy JSON parsing
3. `utils.py` (enhancement) - Dictionary conversion utilities
4. `format_utils.py` - Human-readable data formatting
5. `dict_utils.py` - Dictionary key fuzzy matching
6. `schema_utils.py` - Function schema generation

### 1.2 Test Approach

The testing approach will follow Test-Driven Development (TDD) principles:

- **Unit Tests**: Comprehensive tests for each function and helper
- **Integration Tests**: Tests for cross-module functionality
- **Edge Case Tests**: Tests for boundary conditions and error handling
- **Parametrized Tests**: Tests with multiple inputs for thorough coverage

### 1.3 Key Testing Goals

- Achieve >90% test coverage for all new code
- Verify correct behavior of all utility functions
- Ensure proper error handling for edge cases
- Validate compatibility with existing `lionfuncs` modules
- Confirm performance is acceptable for typical use cases

## 2. Test Environment

### 2.1 Test Framework

```
pytest
pytest-cov
pytest-mock
pytest-asyncio (for any async tests)
```

### 2.2 Mock Framework

```
unittest.mock
pytest-mock (fixture-based mocking)
```

### 2.3 Test Database

Not applicable for these utility functions.

## 3. Unit Tests

### 3.1 Test Suite: text_utils.py

#### 3.1.1 Test Case: string_similarity - Basic Functionality

**Purpose:** Verify that string_similarity correctly calculates similarity
scores using different algorithms.

**Setup:**

```python
@pytest.fixture
def string_pairs():
    return [
        ("kitten", "sitting"),
        ("hello", "hello"),
        ("", "test"),
        ("completely different", "not the same at all"),
    ]
```

**Test Implementation:**

```python
@pytest.mark.parametrize("method", ["levenshtein", "jaro_winkler", "hamming", "cosine", "sequence_matcher"])
def test_string_similarity_methods(string_pairs, method):
    s1, s2 = string_pairs[0]  # kitten, sitting

    # Skip hamming for different length strings
    if method == "hamming" and len(s1) != len(s2):
        pytest.skip("Hamming similarity requires strings of equal length")

    similarity = string_similarity(s1, s2, method=method)

    assert 0.0 <= similarity <= 1.0
    # Each method will have a different expected value, but should be in range
```

#### 3.1.2 Test Case: string_similarity - Edge Cases

**Purpose:** Verify that string_similarity handles edge cases correctly.

**Test Implementation:**

```python
def test_string_similarity_edge_cases():
    # Identical strings should have similarity 1.0
    assert string_similarity("hello", "hello", method="levenshtein") == 1.0

    # Empty strings
    assert string_similarity("", "", method="levenshtein") == 1.0
    assert string_similarity("test", "", method="levenshtein") == 0.0

    # Case sensitivity
    assert string_similarity("Hello", "hello", method="levenshtein") < 1.0
```

#### 3.1.3 Test Case: _cosine_similarity - Vectorization

**Purpose:** Verify that _cosine_similarity correctly vectorizes and calculates
similarity.

**Test Implementation:**

```python
def test_cosine_similarity_vectorization():
    # Test with word tokenization
    s1 = "The quick brown fox jumps over the lazy dog"
    s2 = "The brown fox jumped over the dog"

    similarity = _cosine_similarity(s1, s2)

    assert 0.0 <= similarity <= 1.0
    assert similarity > 0.7  # Should be fairly similar
```

### 3.2 Test Suite: parsers.py

#### 3.2.1 Test Case: fuzzy_parse_json - Valid JSON

**Purpose:** Verify that fuzzy_parse_json correctly parses valid JSON.

**Test Implementation:**

```python
def test_fuzzy_parse_json_valid():
    valid_json = '{"name": "John", "age": 30, "city": "New York"}'

    result = fuzzy_parse_json(valid_json)

    assert result == {"name": "John", "age": 30, "city": "New York"}
```

#### 3.2.2 Test Case: fuzzy_parse_json - Common JSON Errors

**Purpose:** Verify that fuzzy_parse_json correctly fixes and parses JSON with
common errors.

**Test Implementation:**

```python
@pytest.mark.parametrize("malformed_json, expected", [
    ("{'name': 'John', 'age': 30}", {"name": "John", "age": 30}),  # Single quotes
    ('{"name": "John", "age": 30,}', {"name": "John", "age": 30}),  # Trailing comma
    ('{"name": "John", "age": None}', {"name": "John", "age": None}),  # Python None
    ('{"name": "John", "age": True}', {"name": "John", "age": True}),  # Python True
])
def test_fuzzy_parse_json_common_errors(malformed_json, expected):
    result = fuzzy_parse_json(malformed_json, attempt_fix=True)

    assert result == expected
```

#### 3.2.3 Test Case: fuzzy_parse_json - Strict Mode

**Purpose:** Verify that fuzzy_parse_json raises appropriate exceptions in
strict mode.

**Test Implementation:**

```python
def test_fuzzy_parse_json_strict():
    malformed_json = "{'name': 'John'}"

    # Should not raise in non-strict mode
    result = fuzzy_parse_json(malformed_json, attempt_fix=True, strict=False)
    assert result == {"name": "John"}

    # Should raise in strict mode
    with pytest.raises(ValueError):
        fuzzy_parse_json(malformed_json, attempt_fix=False, strict=True)
```

#### 3.2.4 Test Case: _fix_json_string - JSON Fixes

**Purpose:** Verify that _fix_json_string correctly fixes common JSON formatting
issues.

**Test Implementation:**

```python
@pytest.mark.parametrize("input_str, expected", [
    ("{'key': 'value'}", '{"key": "value"}'),  # Single quotes to double quotes
    ('{"key": "value",}', '{"key": "value"}'),  # Trailing comma
    ('{"key": True}', '{"key": true}'),  # Python True to JSON true
    ('{"key": False}', '{"key": false}'),  # Python False to JSON false
    ('{"key": None}', '{"key": null}'),  # Python None to JSON null
])
def test_fix_json_string(input_str, expected):
    result = _fix_json_string(input_str)

    assert result == expected
```

### 3.3 Test Suite: utils.py (to_dict)

#### 3.3.1 Test Case: to_dict - Pydantic Models

**Purpose:** Verify that to_dict correctly converts Pydantic models to
dictionaries.

**Setup:**

```python
@pytest.fixture
def sample_pydantic_model():
    class SampleModel(BaseModel):
        name: str
        age: int
        tags: list[str] = []

    return SampleModel(name="John", age=30, tags=["a", "b"])
```

**Test Implementation:**

```python
def test_to_dict_pydantic_model(sample_pydantic_model):
    result = to_dict(sample_pydantic_model)

    assert result == {"name": "John", "age": 30, "tags": ["a", "b"]}
```

#### 3.3.2 Test Case: to_dict - Dataclasses

**Purpose:** Verify that to_dict correctly converts dataclasses to dictionaries.

**Setup:**

```python
@pytest.fixture
def sample_dataclass():
    @dataclass
    class SampleData:
        name: str
        age: int
        tags: list[str] = field(default_factory=list)

    return SampleData(name="John", age=30, tags=["a", "b"])
```

**Test Implementation:**

```python
def test_to_dict_dataclass(sample_dataclass):
    result = to_dict(sample_dataclass)

    assert result == {"name": "John", "age": 30, "tags": ["a", "b"]}
```

#### 3.3.3 Test Case: to_dict - Nested Structures

**Purpose:** Verify that to_dict correctly handles nested structures.

**Test Implementation:**

```python
def test_to_dict_nested():
    nested_dict = {
        "person": {
            "name": "John",
            "address": {
                "city": "New York",
                "zip": "10001"
            }
        },
        "tags": ["a", "b", "c"]
    }

    result = to_dict(nested_dict)

    assert result == nested_dict
```

#### 3.3.4 Test Case: to_dict - Options

**Purpose:** Verify that to_dict correctly applies options like fields, exclude,
etc.

**Setup:**

```python
@pytest.fixture
def model_with_options():
    class OptionsModel(BaseModel):
        name: str
        age: int
        email: str | None = None
        internal_id: str = "default"

    return OptionsModel(name="John", age=30, email="john@example.com")
```

**Test Implementation:**

```python
def test_to_dict_options(model_with_options):
    # Test fields option
    result = to_dict(model_with_options, fields=["name", "age"])
    assert "name" in result
    assert "age" in result
    assert "email" not in result

    # Test exclude option
    result = to_dict(model_with_options, exclude=["internal_id"])
    assert "internal_id" not in result

    # Test exclude_none option
    model_with_options.email = None
    result = to_dict(model_with_options, exclude_none=True)
    assert "email" not in result
```

### 3.4 Test Suite: format_utils.py

#### 3.4.1 Test Case: as_readable - Format Types

**Purpose:** Verify that as_readable correctly formats data in different
formats.

**Test Implementation:**

```python
@pytest.mark.parametrize("format_type", ["auto", "yaml_like", "json", "repr"])
def test_as_readable_format_types(format_type):
    data = {"name": "John", "age": 30, "tags": ["a", "b"]}

    result = as_readable(data, format_type=format_type)

    assert isinstance(result, str)
    # For JSON format, verify it's valid JSON
    if format_type == "json":
        assert json.loads(result) == data
```

#### 3.4.2 Test Case: as_readable - Nested Data

**Purpose:** Verify that as_readable correctly formats nested data structures.

**Test Implementation:**

```python
def test_as_readable_nested_data():
    nested_data = {
        "person": {
            "name": "John",
            "address": {
                "city": "New York",
                "zip": "10001"
            }
        },
        "tags": ["a", "b", "c"]
    }

    result = as_readable(nested_data, format_type="yaml_like")

    assert "person:" in result
    assert "name: John" in result
    assert "address:" in result
    assert "city: New York" in result
    assert "tags:" in result
```

#### 3.4.3 Test Case: _format_dict_yaml_like

**Purpose:** Verify that _format_dict_yaml_like correctly formats dictionaries
in YAML-like format.

**Test Implementation:**

```python
def test_format_dict_yaml_like():
    data = {
        "name": "John",
        "age": 30,
        "address": {
            "city": "New York",
            "zip": "10001"
        },
        "tags": ["a", "b", "c"],
        "bio": "This is\na multi-line\nstring"
    }

    result = _format_dict_yaml_like(data)

    assert "name: John" in result
    assert "age: 30" in result
    assert "address:" in result
    assert "city: New York" in result
    assert "tags:" in result
    assert "- a" in result
    assert "bio: |" in result  # Multi-line string format
```

#### 3.4.4 Test Case: _is_in_notebook

**Purpose:** Verify that _is_in_notebook correctly detects notebook environment.

**Test Implementation:**

```python
def test_is_in_notebook(monkeypatch):
    # Mock IPython not being available
    monkeypatch.setattr("builtins.__import__", lambda name, *args, **kwargs:
                       raise ImportError() if name == "IPython" else __import__(name, *args, **kwargs))
    assert not _is_in_notebook()

    # Mock IPython being available but not in notebook
    class MockIPython:
        @staticmethod
        def get_ipython():
            class Shell:
                @property
                def __class__(self):
                    class _Class:
                        __name__ = "TerminalInteractiveShell"
                    return _Class()
            return Shell()

    monkeypatch.setattr("builtins.__import__", lambda name, *args, **kwargs:
                       MockIPython if name == "IPython" else __import__(name, *args, **kwargs))
    assert not _is_in_notebook()

    # Mock IPython being available in notebook
    class MockIPythonNotebook:
        @staticmethod
        def get_ipython():
            class Shell:
                @property
                def __class__(self):
                    class _Class:
                        __name__ = "ZMQInteractiveShell"
                    return _Class()

                def has_trait(self, trait):
                    return trait == "kernel"
            return Shell()

    monkeypatch.setattr("builtins.__import__", lambda name, *args, **kwargs:
                       MockIPythonNotebook if name == "IPython" else __import__(name, *args, **kwargs))
    assert _is_in_notebook()
```

### 3.5 Test Suite: dict_utils.py

#### 3.5.1 Test Case: fuzzy_match_keys - Exact Matches

**Purpose:** Verify that fuzzy_match_keys correctly identifies exact key
matches.

**Test Implementation:**

```python
def test_fuzzy_match_keys_exact():
    data = {"name": "John", "age": 30, "city": "New York"}
    reference_keys = ["name", "age", "city"]

    result = fuzzy_match_keys(data, reference_keys)

    assert result == data
```

#### 3.5.2 Test Case: fuzzy_match_keys - Fuzzy Matches

**Purpose:** Verify that fuzzy_match_keys correctly identifies fuzzy key matches
based on threshold.

**Test Implementation:**

```python
def test_fuzzy_match_keys_fuzzy():
    data = {"Name": "John", "Age": 30, "City": "New York"}
    reference_keys = ["name", "age", "city"]

    # With case sensitivity, should not match
    result = fuzzy_match_keys(data, reference_keys, case_sensitive=True)
    assert "name" not in result

    # Without case sensitivity, should match
    result = fuzzy_match_keys(data, reference_keys, case_sensitive=False)
    assert "name" in result

    # Test with typos
    data = {"nmae": "John", "aeg": 30, "ctiy": "New York"}
    result = fuzzy_match_keys(data, reference_keys, threshold=0.7)
    assert "name" in result
    assert "age" in result
    assert "city" in result
```

#### 3.5.3 Test Case: fuzzy_match_keys - Different Similarity Algorithms

**Purpose:** Verify that fuzzy_match_keys works with different similarity
algorithms.

**Test Implementation:**

```python
@pytest.mark.parametrize("algorithm", ["levenshtein", "jaro_winkler", "sequence_matcher"])
def test_fuzzy_match_keys_algorithms(algorithm):
    data = {"nmae": "John", "aeg": 30, "ctiy": "New York"}
    reference_keys = ["name", "age", "city"]

    result = fuzzy_match_keys(data, reference_keys, default_method=algorithm, threshold=0.7)

    # All algorithms should match these keys with threshold 0.7
    assert "name" in result
    assert "age" in result
    assert "city" in result
```

#### 3.5.4 Test Case: fuzzy_match_keys - Handle Unmatched Options

**Purpose:** Verify that fuzzy_match_keys correctly handles unmatched keys based
on options.

**Test Implementation:**

```python
@pytest.mark.parametrize("handle_unmatched, expected_keys", [
    ("ignore", ["name", "age", "city", "extra"]),
    ("remove", ["name", "age", "city"]),
    ("fill", ["name", "age", "city", "extra", "missing"]),
    ("force", ["name", "age", "city", "missing"]),
])
def test_fuzzy_match_keys_handle_unmatched(handle_unmatched, expected_keys):
    data = {"name": "John", "age": 30, "city": "New York", "extra": "value"}
    reference_keys = ["name", "age", "city", "missing"]

    result = fuzzy_match_keys(
        data,
        reference_keys,
        handle_unmatched=handle_unmatched,
        fill_value="default"
    )

    assert set(result.keys()) == set(expected_keys)

    if handle_unmatched in ["fill", "force"]:
        assert result["missing"] == "default"
```

### 3.6 Test Suite: schema_utils.py

#### 3.6.1 Test Case: function_to_openai_schema - Simple Functions

**Purpose:** Verify that function_to_openai_schema correctly generates schema
for simple functions.

**Test Implementation:**

```python
def test_function_to_openai_schema_simple():
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
    assert "description" in schema
    assert "parameters" in schema
    assert schema["parameters"]["type"] == "object"
    assert "a" in schema["parameters"]["properties"]
    assert "b" in schema["parameters"]["properties"]
    assert schema["parameters"]["properties"]["a"]["type"] == "number"
    assert schema["parameters"]["properties"]["b"]["type"] == "string"
    assert "required" in schema["parameters"]
    assert "a" in schema["parameters"]["required"]
    assert "b" in schema["parameters"]["required"]
```

#### 3.6.2 Test Case: function_to_openai_schema - Complex Parameter Types

**Purpose:** Verify that function_to_openai_schema correctly handles complex
parameter types.

**Test Implementation:**

```python
def test_function_to_openai_schema_complex_types():
    from typing import List, Dict, Optional, Literal

    def complex_function(
        a: List[int],
        b: Dict[str, Any],
        c: Optional[str] = None,
        d: Literal["option1", "option2"] = "option1"
    ) -> Dict[str, Any]:
        """Complex function with various parameter types."""
        return {}

    schema = function_to_openai_schema(complex_function)

    assert schema["name"] == "complex_function"
    assert "parameters" in schema
    assert "a" in schema["parameters"]["properties"]
    assert "b" in schema["parameters"]["properties"]
    assert "c" in schema["parameters"]["properties"]
    assert "d" in schema["parameters"]["properties"]

    # Check that optional parameters are not in required list
    assert "c" not in schema["parameters"]["required"]
    assert "d" not in schema["parameters"]["required"]
```

#### 3.6.3 Test Case: function_to_openai_schema - Docstrings

**Purpose:** Verify that function_to_openai_schema correctly extracts
descriptions from docstrings.

**Test Implementation:**

```python
def test_function_to_openai_schema_docstrings():
    def documented_function(a: int, b: str) -> None:
        """This is the function description.

        Args:
            a: Description for parameter a
            b: Description for parameter b
        """
        pass

    schema = function_to_openai_schema(documented_function)

    assert schema["description"] == "This is the function description."
    # If parameter descriptions are implemented:
    # assert schema["parameters"]["properties"]["a"]["description"] == "Description for parameter a"
    # assert schema["parameters"]["properties"]["b"]["description"] == "Description for parameter b"
```

#### 3.6.4 Test Case: function_to_openai_schema - Pydantic Models

**Purpose:** Verify that function_to_openai_schema correctly handles Pydantic
models in type hints.

**Test Implementation:**

```python
def test_function_to_openai_schema_pydantic_models():
    class UserModel(BaseModel):
        name: str
        age: int
        email: str | None = None

    def create_user(user: UserModel) -> dict:
        """Create a new user."""
        return {}

    schema = function_to_openai_schema(create_user)

    assert schema["name"] == "create_user"
    assert "parameters" in schema
    assert "user" in schema["parameters"]["properties"]
    # The exact structure will depend on implementation details
```

## 4. Integration Tests

### 4.1 Test Suite: Cross-Module Integration

#### 4.1.1 Test Case: fuzzy_match_keys using string_similarity

**Purpose:** Verify that fuzzy_match_keys correctly uses string_similarity
functions.

**Test Implementation:**

```python
def test_fuzzy_match_keys_with_string_similarity():
    data = {"nmae": "John", "aeg": 30, "ctiy": "New York"}
    reference_keys = ["name", "age", "city"]

    # Test with different similarity algorithms
    for algorithm in ["levenshtein", "jaro_winkler", "sequence_matcher"]:
        result = fuzzy_match_keys(data, reference_keys, default_method=algorithm, threshold=0.7)

        # All should match these keys with threshold 0.7
        assert "name" in result
        assert "age" in result
        assert "city" in result
```

#### 4.1.2 Test Case: as_readable using to_dict

**Purpose:** Verify that as_readable correctly uses to_dict for complex data
structures.

**Test Implementation:**

```python
def test_as_readable_with_to_dict():
    class SampleModel(BaseModel):
        name: str
        age: int
        nested: dict

    model = SampleModel(name="John", age=30, nested={"key": "value"})

    result = as_readable(model)

    assert "name" in result
    assert "John" in result
    assert "age" in result
    assert "30" in result
    assert "nested" in result
    assert "key" in result
    assert "value" in result
```

## 5. Mock Implementation Details

```python
class MockIPython:
    @staticmethod
    def get_ipython():
        class Shell:
            @property
            def __class__(self):
                class _Class:
                    __name__ = "ZMQInteractiveShell"
                return _Class()

            def has_trait(self, trait):
                return trait == "kernel"
        return Shell()
```

## 6. Test Data

```python
# Sample data for string similarity tests
string_similarity_test_data = [
    ("kitten", "sitting", 0.5714285714285714),  # levenshtein
    ("hello", "hello", 1.0),
    ("", "test", 0.0),
    ("completely different", "not the same at all", 0.0),
]

# Sample JSON data for fuzzy parsing tests
json_test_data = [
    ('{"name": "John", "age": 30}', {"name": "John", "age": 30}),
    ("{'name': 'John', 'age': 30}", {"name": "John", "age": 30}),
    ('{"name": "John", "age": 30,}', {"name": "John", "age": 30}),
    ('{"name": "John", "age": None}', {"name": "John", "age": None}),
    ('{"name": "John", "age": True}', {"name": "John", "age": True}),
]

# Sample dictionary data for fuzzy key matching tests
dict_test_data = {
    "exact": {"name": "John", "age": 30, "city": "New York"},
    "case_diff": {"Name": "John", "Age": 30, "City": "New York"},
    "typos": {"nmae": "John", "aeg": 30, "ctiy": "New York"},
}
```

## 7. Helper Functions

```python
def create_sample_pydantic_model():
    """Create a sample Pydantic model for testing."""
    class SampleModel(BaseModel):
        name: str
        age: int
        tags: list[str] = []

    return SampleModel(name="John", age=30, tags=["a", "b"])

def create_sample_dataclass():
    """Create a sample dataclass for testing."""
    @dataclass
    class SampleData:
        name: str
        age: int
        tags: list[str] = field(default_factory=list)

    return SampleData(name="John", age=30, tags=["a", "b"])
```

## 11. Test Coverage Targets

- **Line Coverage Target:** 90%
- **Branch Coverage Target:** 85%
- **Critical Functions:**
  - `string_similarity`: 95% coverage
  - `fuzzy_parse_json`: 95% coverage
  - `to_dict`: 95% coverage
  - `function_to_openai_schema`: 90% coverage

## 12. Continuous Integration

The tests will be run as part of the CI pipeline using pytest:

```bash
# Run all tests with coverage
uv run pytest tests/ --cov=src/lionfuncs --cov-report=xml --cov-report=term

# Run specific test modules
uv run pytest tests/unit/test_text_utils.py
uv run pytest tests/unit/test_parsers.py
```

## 13. Notes and Caveats

### 13.1 Known Limitations

- The `_is_in_notebook` function relies on IPython internals which may change in
  future versions
- String similarity algorithms have different performance characteristics and
  may not be suitable for very large strings
- The `to_dict` function may not handle all possible object types, especially
  custom classes with complex structures

### 13.2 Future Improvements

- Add more comprehensive performance tests for string similarity algorithms
- Enhance docstring parsing in `function_to_openai_schema` to extract parameter
  descriptions
- Add benchmarks for common operations to track performance over time
