---
title: "Contributing to lionfuncs"
---

# Contributing to lionfuncs

Thank you for your interest in contributing to `lionfuncs`! This guide will help
you get started with the development environment, coding standards, and the pull
request process.

## Setting Up the Development Environment

### Prerequisites

- Python 3.9 or higher
- [uv](https://github.com/astral-sh/uv) for dependency management
- Git

### Clone the Repository

```bash
git clone https://github.com/khive-ai/lionfuncs.git
cd lionfuncs
```

### Create a Virtual Environment

We use `uv` for dependency management:

```bash
# Create a virtual environment
uv venv

# Activate the virtual environment
# On Windows:
.venv\Scripts\activate
# On macOS/Linux:
source .venv/bin/activate
```

### Install Dependencies

```bash
# Install the package in development mode with all extras
uv pip install -e ".[dev,test,media]"
```

## Development Workflow

### Branching Strategy

- `main` branch is the stable branch
- Create feature branches from `main` for new features or bug fixes
- Use the naming convention `feature/<issue-number>-<brief-description>` for
  feature branches
- Use the naming convention `fix/<issue-number>-<brief-description>` for bug fix
  branches

Example:

```bash
git checkout -b feature/42-add-new-adapter
```

### Running Tests

We use `pytest` for testing:

```bash
# Run all tests
pytest

# Run tests with coverage
pytest --cov=lionfuncs

# Run specific tests
pytest tests/unit/test_utils.py
```

### Code Formatting and Linting

We use `pre-commit` to enforce code formatting and linting:

```bash
# Install pre-commit hooks
uv run pre-commit install

# Run pre-commit on all files
uv run pre-commit run --all-files
```

The pre-commit hooks include:

- `black` for code formatting
- `ruff` for linting
- `mypy` for type checking

## Pull Request Process

1. **Create an Issue**: Before starting work, create an issue describing the
   feature or bug fix.
2. **Create a Branch**: Create a branch from `main` with the naming convention
   described above.
3. **Make Changes**: Make your changes, following the coding standards.
4. **Write Tests**: Add tests for your changes.
5. **Run Tests**: Make sure all tests pass.
6. **Run Pre-commit**: Make sure all pre-commit hooks pass.
7. **Commit Changes**: Commit your changes with a descriptive commit message.
8. **Push Changes**: Push your changes to your fork.
9. **Create a Pull Request**: Create a pull request from your branch to `main`.

### Commit Message Format

We follow the [Conventional Commits](https://www.conventionalcommits.org/)
format:

```
<type>(<scope>): <subject>

<body>

<footer>
```

Types:

- `feat`: A new feature
- `fix`: A bug fix
- `docs`: Documentation changes
- `style`: Changes that do not affect the meaning of the code (formatting, etc.)
- `refactor`: Code changes that neither fix a bug nor add a feature
- `perf`: Code changes that improve performance
- `test`: Adding or modifying tests
- `build`: Changes to the build system or dependencies
- `ci`: Changes to CI configuration files and scripts
- `chore`: Other changes that don't modify src or test files

Example:

```
feat(network): add OpenAI adapter

Add an adapter for the OpenAI API to the network module.

Closes #42
```

## Coding Standards

### Python Style Guide

We follow the [PEP 8](https://www.python.org/dev/peps/pep-0008/) style guide
with some modifications:

- Line length: 88 characters (enforced by `black`)
- Use double quotes for strings
- Use type hints for function signatures
- Use docstrings for all public functions, classes, and methods

### Docstring Format

We use the
[Google style](https://google.github.io/styleguide/pyguide.html#38-comments-and-docstrings)
for docstrings:

```python
def function_with_types_in_docstring(param1: int, param2: str) -> bool:
    """Example function with types documented in the docstring.

    Args:
        param1: The first parameter.
        param2: The second parameter.

    Returns:
        True if successful, False otherwise.

    Raises:
        ValueError: If param1 is negative.
    """
    if param1 < 0:
        raise ValueError("param1 must be non-negative.")
    return param1 < len(param2)
```

### Type Hints

We use type hints for all function signatures:

```python
def greet(name: str) -> str:
    return f"Hello, {name}!"
```

For more complex types, use the `typing` module:

```python
from typing import List, Dict, Optional, Union, Callable, Any

def process_items(items: List[Dict[str, Any]]) -> Optional[str]:
    ...
```

### Imports

Organize imports in the following order:

1. Standard library imports
2. Related third-party imports
3. Local application/library specific imports

Within each group, imports should be sorted alphabetically.

```python
# Standard library imports
import asyncio
import os
from typing import Dict, List, Optional

# Third-party imports
import httpx
from pydantic import BaseModel

# Local imports
from lionfuncs.errors import LionError
from lionfuncs.utils import is_coro_func
```

## Adding New Features

When adding new features, follow these guidelines:

1. **Backward Compatibility**: Ensure that new features don't break existing
   functionality.
2. **Documentation**: Add documentation for new features, including docstrings
   and examples.
3. **Tests**: Add tests for new features, aiming for high test coverage.
4. **Type Hints**: Add type hints for all new functions and classes.
5. **Error Handling**: Use appropriate error handling and raise specific
   exceptions.

## Adding New Dependencies

When adding new dependencies:

1. **Minimize Dependencies**: Only add dependencies that are absolutely
   necessary.
2. **Optional Dependencies**: Use extras for optional dependencies.
3. **Update pyproject.toml**: Add the dependency to the appropriate section in
   `pyproject.toml`.
4. **Update Documentation**: Update the documentation to mention the new
   dependency.

## Testing

We aim for high test coverage and use the following testing tools:

- `pytest` for running tests
- `pytest-cov` for measuring test coverage
- `pytest-asyncio` for testing async code

### Test Structure

- Unit tests go in the `tests/unit` directory
- Integration tests go in the `tests/integration` directory
- Test files should be named `test_*.py`
- Test functions should be named `test_*`

### Test Guidelines

- Each test should test a single functionality
- Use fixtures for setup and teardown
- Use parametrized tests for testing multiple inputs
- Mock external dependencies
- Aim for high test coverage, but focus on testing behavior, not implementation
  details

## Documentation

We use Markdown for documentation:

- API documentation goes in the `docs/lionfuncs/api` directory
- Usage guides go in the `docs/lionfuncs/guides` directory
- Examples go in the `docs/lionfuncs/examples` directory

When adding new features, update the documentation accordingly.

## License

By contributing to `lionfuncs`, you agree that your contributions will be
licensed under the project's
[MIT License](https://github.com/khive-ai/lionfuncs/blob/main/LICENSE).

## Code of Conduct

Please follow our
[Code of Conduct](https://github.com/khive-ai/lionfuncs/blob/main/CODE_OF_CONDUCT.md)
in all your interactions with the project.

## Questions?

If you have any questions, feel free to open an issue or reach out to the
maintainers.

Thank you for contributing to `lionfuncs`!
