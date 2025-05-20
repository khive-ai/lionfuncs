import asyncio
import functools
import inspect
import json
import os
from collections.abc import Coroutine, Iterable, Mapping
from enum import Enum
from typing import Any, Callable, TypeVar, cast

from pydantic import BaseModel
from pydantic_core import PydanticUndefined

R = TypeVar("R")


def hash_dict(data) -> int:
    hashable_items = []
    if isinstance(data, BaseModel):
        data = data.model_dump()
    for k, v in data.items():
        if isinstance(v, (list, dict)):
            v = json.dumps(v, sort_keys=True)
        elif not isinstance(v, (str, int, float, bool, type(None))):
            v = str(v)
        hashable_items.append((k, v))
    return hash(frozenset(hashable_items))


__all__ = [
    "is_coro_func",
    "force_async",
    "get_env_bool",
    "get_env_dict",
    "to_list",
    "to_dict",
]


def is_coro_func(func: Callable[..., Any]) -> bool:
    """
    Checks if a callable is a coroutine function.

    Args:
        func: The callable to check.

    Returns:
        True if the callable is a coroutine function, False otherwise.
    """
    # For functools.partial or other wrapped callables,
    # we need to unwrap them to get to the original function.
    while isinstance(func, functools.partial):
        func = func.func
    return inspect.iscoroutinefunction(func) or inspect.isasyncgenfunction(func)


async def _run_sync_in_executor(func: Callable[..., R], *args: Any, **kwargs: Any) -> R:
    """Helper to run a sync function in the default executor."""
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, functools.partial(func, *args, **kwargs))


def force_async(func: Callable[..., R]) -> Callable[..., Coroutine[Any, Any, R]]:
    """
    Wraps a synchronous function to be called asynchronously in a thread pool.
    If the function is already async, it's returned unchanged.

    Args:
        func: The synchronous or asynchronous function to wrap.

    Returns:
        An awaitable version of the function.
    """
    if is_coro_func(func):
        return cast(Callable[..., Coroutine[Any, Any, R]], func)

    @functools.wraps(func)
    async def wrapper(*args: Any, **kwargs: Any) -> R:
        return await _run_sync_in_executor(func, *args, **kwargs)

    return wrapper


def get_env_bool(var_name: str, default: bool = False) -> bool:
    """
    Gets a boolean environment variable.
    True values (case-insensitive): 'true', '1', 'yes', 'y', 'on'.
    False values (case-insensitive): 'false', '0', 'no', 'n', 'off'.

    Args:
        var_name: The name of the environment variable.
        default: The default value if the variable is not set or is not a recognized boolean.

    Returns:
        The boolean value of the environment variable.
    """
    value = os.environ.get(var_name, "").strip().lower()
    if not value:
        return default

    if value in ("true", "1", "yes", "y", "on"):
        return True
    if value in ("false", "0", "no", "n", "off"):
        return False
    return default


def get_env_dict(
    var_name: str, default: dict[Any, Any] | None = None
) -> dict[Any, Any] | None:
    """
    Gets a dictionary environment variable (expected to be a JSON string).

    Args:
        var_name: The name of the environment variable.
        default: The default value if the variable is not set or is not valid JSON.

    Returns:
        The dictionary value of the environment variable or the default.
    """
    value_str = os.environ.get(var_name)
    if value_str is None:
        return default

    try:
        return cast(dict[Any, Any], json.loads(value_str))
    except json.JSONDecodeError:
        return default


def to_list(
    input_: Any,
    /,
    *,
    flatten: bool = False,
    dropna: bool = False,
    unique: bool = False,
    use_values: bool = False,
    flatten_tuple_set: bool = False,
) -> list:
    """Convert input to a list with optional transformations.

    Transforms various input types into a list with configurable processing
    options for flattening, filtering, and value extraction.

    Args:
        input_: Value to convert to list.
        flatten: If True, recursively flatten nested iterables.
        dropna: If True, remove None and undefined values.
        unique: If True, remove duplicates (requires flatten=True).
        use_values: If True, extract values from enums/mappings.
        flatten_tuple_set: If True, include tuples and sets in flattening.

    Returns:
        list: Processed list based on input and specified options.

    Raises:
        ValueError: If unique=True is used without flatten=True.
    """

    def _process_list_inner(
        lst: list[Any],
        current_flatten: bool,
        current_dropna: bool,
    ) -> list[Any]:
        """Process list according to flatten and dropna options."""
        result = []
        skip_types_iter = (str, bytes, bytearray, Mapping, BaseModel)

        current_skip_types = skip_types_iter
        if not flatten_tuple_set:
            current_skip_types += (tuple, set, frozenset)

        for item in lst:
            if current_dropna and (item is None or item is PydanticUndefined):
                continue

            is_iterable = isinstance(item, Iterable)
            should_skip_flattening = isinstance(item, current_skip_types)

            if is_iterable and not should_skip_flattening:
                item_list = list(item)
                if current_flatten:
                    result.extend(
                        _process_list_inner(
                            item_list,
                            current_flatten=current_flatten,
                            current_dropna=current_dropna,
                        )
                    )
                else:
                    result.append(
                        _process_list_inner(
                            item_list,
                            current_flatten=False,
                            current_dropna=current_dropna,
                        )
                    )
            else:
                result.append(item)
        return result

    def _to_list_type_inner(current_input: Any, current_use_values: bool) -> list[Any]:
        """Convert input to initial list based on type."""
        if current_input is None or current_input is PydanticUndefined:
            return []

        if isinstance(current_input, list):
            return current_input

        if isinstance(current_input, type) and issubclass(current_input, Enum):
            members = list(current_input.__members__.values())
            return (
                [member.value for member in members] if current_use_values else members
            )

        if isinstance(current_input, (str, bytes, bytearray)):
            return [current_input]

        if isinstance(current_input, Mapping):
            return (
                list(current_input.values())
                if current_use_values and hasattr(current_input, "values")
                else [current_input]
            )

        if isinstance(current_input, BaseModel):
            return [current_input]

        if isinstance(current_input, Iterable):
            return list(current_input)

        return [current_input]

    if unique and not flatten:  # pragma: no cover
        raise ValueError("unique=True requires flatten=True")

    initial_list = _to_list_type_inner(input_, current_use_values=use_values)
    processed = _process_list_inner(
        initial_list, current_flatten=flatten, current_dropna=dropna
    )

    if unique:
        seen = set()
        out = []
        for x in processed:
            hash_val = None
            try:
                hash_val = hash(x)
            except TypeError:
                try:
                    if isinstance(x, list):
                        hash_val = hash(tuple(x))
                    elif isinstance(x, set):
                        hash_val = hash(frozenset(x))
                    elif isinstance(x, dict):
                        hash_val = hash(tuple(sorted(x.items())))
                    elif isinstance(x, BaseModel):
                        hash_val = hash(x.model_dump_json())
                    else:  # pragma: no cover
                        try:
                            hash_val = hash_dict(x)
                        except TypeError:  # pragma: no cover
                            pass
                except Exception:  # pragma: no cover
                    pass

            if hash_val is not None:
                if hash_val not in seen:
                    seen.add(hash_val)
                    out.append(x)
            else:
                is_seen_unhashable = False  # pragma: no cover
                for seen_item in out:  # pragma: no cover
                    if x is seen_item:
                        is_seen_unhashable = True
                        break
                if not is_seen_unhashable:  # pragma: no cover
                    out.append(x)
        return out

    return processed


def to_dict(
    obj: Any,
    *,
    fields: list[str] | None = None,
    exclude: list[str] | None = None,
    by_alias: bool = False,
    exclude_none: bool = False,
    exclude_unset: bool = False,
    exclude_defaults: bool = False,
) -> dict | list | Any:
    """Convert various object types to a dictionary representation.

    Handles Pydantic models, dataclasses, dictionaries, lists, and other objects.
    For Pydantic models, uses model_dump() with appropriate options.
    For other types, attempts to convert to a dictionary-like structure.

    Args:
        obj: The object to convert to a dictionary
        fields: Optional list of field names to include (for Pydantic models)
        exclude: Optional list of field names to exclude (for Pydantic models)
        by_alias: Whether to use field aliases (for Pydantic models)
        exclude_none: Whether to exclude None values (for Pydantic models)
        exclude_unset: Whether to exclude unset fields (for Pydantic models)
        exclude_defaults: Whether to exclude fields with default values (for Pydantic models)

    Returns:
        A dictionary representation of the object, or the original object if it
        cannot be converted to a dictionary

    Raises:
        TypeError: If the object cannot be converted to a dictionary
    """
    # Handle Pydantic models
    if isinstance(obj, BaseModel):
        dump_kwargs = {
            "by_alias": by_alias,
            "exclude_none": exclude_none,
            "exclude_unset": exclude_unset,
            "exclude_defaults": exclude_defaults,
        }

        # Handle include/exclude fields
        if fields is not None:
            dump_kwargs["include"] = {f: True for f in fields}
        if exclude is not None:
            dump_kwargs["exclude"] = {f: True for f in exclude}

        return obj.model_dump(**dump_kwargs)

    # Handle dataclasses
    if hasattr(obj, "__dataclass_fields__"):
        from dataclasses import asdict

        base_dict = asdict(obj)
        # Apply recursive conversion with relevant options
        return {
            k: to_dict(v, by_alias=by_alias, exclude_none=exclude_none)
            for k, v in base_dict.items()
        }

    # Handle dictionaries
    if isinstance(obj, dict):
        return {
            k: to_dict(v, by_alias=by_alias, exclude_none=exclude_none)
            for k, v in obj.items()
        }

    # Handle lists, tuples, sets
    if isinstance(obj, (list, tuple, set)):
        return type(obj)(
            to_dict(item, by_alias=by_alias, exclude_none=exclude_none) for item in obj
        )

    # Handle general objects with __dict__
    if hasattr(obj, "__dict__"):
        return {
            k: to_dict(v, by_alias=by_alias, exclude_none=exclude_none)
            for k, v in vars(obj).items()
        }

    # Handle primitive types
    if isinstance(obj, (str, int, float, bool)) or obj is None:
        return obj

    # Try to check if JSON serializable
    try:
        json.dumps(obj)
        return obj
    except TypeError:
        # If not directly serializable, raise TypeError
        raise TypeError(
            f"Object of type {type(obj)} is not automatically convertible to "
            "dict/JSON serializable structure."
        )
