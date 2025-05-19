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


# Placeholder for hash_dict
# A more robust implementation might be needed depending on usage.
def hash_dict(data: Any) -> int:
    """Simple hash for dict-like objects for to_list's unique functionality."""
    if isinstance(data, Mapping):
        return hash(tuple(sorted(data.items())))
    if isinstance(data, BaseModel):  # pragma: no cover
        return hash(data.model_dump_json())  # pragma: no cover
    # Fallback for other unhashable types if necessary, or let it raise TypeError
    raise TypeError(f"Unhashable type: {type(data)}")  # pragma: no cover


__all__ = [
    "is_coro_func",
    "force_async",
    "get_env_bool",
    "get_env_dict",
    "to_list",
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

    # Inner functions _process_list and _to_list_type are defined here
    # as per the user-provided code.

    def _process_list_inner(
        lst: list[Any],
        current_flatten: bool,  # Renamed to avoid conflict with outer scope
        current_dropna: bool,  # Renamed
    ) -> list[Any]:
        """Process list according to flatten and dropna options."""
        result = []
        # Define skip_types for iterables that should not be flattened further by default
        skip_types_iter = (str, bytes, bytearray, Mapping, BaseModel)

        # Add tuple and set to skip_types if flatten_tuple_set is False
        current_skip_types = skip_types_iter
        if not flatten_tuple_set:
            current_skip_types += (tuple, set, frozenset)

        for item in lst:
            if current_dropna and (item is None or item is PydanticUndefined):
                continue

            is_iterable = isinstance(item, Iterable)
            should_skip_flattening = isinstance(item, current_skip_types)

            if is_iterable and not should_skip_flattening:
                # Item is an iterable and not in skip_types (e.g., a list to be potentially flattened)
                item_list = list(item)  # Convert generic iterable to list
                if current_flatten:
                    # Recursively call _process_list_inner for items of the nested list
                    result.extend(
                        _process_list_inner(  # Recursive call
                            item_list,
                            current_flatten=current_flatten,
                            current_dropna=current_dropna,
                        )
                    )
                else:
                    # If not flattening this level, process the inner list (e.g., for dropna)
                    # and append it as a sublist.
                    result.append(
                        _process_list_inner(  # Recursive call
                            item_list,
                            current_flatten=False,
                            current_dropna=current_dropna,
                        )
                    )
            else:
                # Item is not an iterable to be flattened, or it's a type we explicitly skip for flattening
                result.append(item)
        return result

    def _to_list_type_inner(
        current_input: Any, current_use_values: bool
    ) -> list[Any]:  # Renamed
        """Convert input to initial list based on type."""
        if current_input is None or current_input is PydanticUndefined:
            return []

        if isinstance(current_input, list):
            return current_input

        if isinstance(current_input, type) and issubclass(current_input, Enum):
            members = list(current_input.__members__.values())  # Ensure it's a list
            return (
                [member.value for member in members] if current_use_values else members
            )

        # For str, bytes, bytearray, treat them as single items unless use_values and flatten are involved
        # The original logic for str/bytes/bytearray with use_values was a bit ambiguous.
        # If use_values is true for a string, should it be list(string) or [string]?
        # Assuming [string] unless flatten is also true, which _process_list_inner handles.
        if isinstance(current_input, (str, bytes, bytearray)):
            return [current_input]  # Typically, a string is treated as a single item.

        if isinstance(current_input, Mapping):
            return (
                list(current_input.values())
                if current_use_values and hasattr(current_input, "values")
                else [current_input]  # Treat mapping as a single item if not use_values
            )

        if isinstance(current_input, BaseModel):
            return [current_input]  # Treat BaseModel instance as a single item

        # For other iterables (not str, bytes, bytearray, Mapping, BaseModel)
        if isinstance(current_input, Iterable):
            return list(current_input)

        return [current_input]  # Default: treat as a single-item list

    if unique and not flatten:  # pragma: no cover
        raise ValueError("unique=True requires flatten=True")

    initial_list = _to_list_type_inner(input_, current_use_values=use_values)
    # Call _process_list_inner with its defined parameter names
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
                    # Attempt to hash common unhashable collection types by converting to frozenset of items
                    if isinstance(x, list):
                        hash_val = hash(tuple(x))
                    elif isinstance(x, set):
                        hash_val = hash(frozenset(x))
                    elif isinstance(x, dict):
                        hash_val = hash(tuple(sorted(x.items())))
                    elif isinstance(x, BaseModel):
                        hash_val = hash(x.model_dump_json())
                    else:  # pragma: no cover
                        # If still unhashable, it's a complex case not handled by this simple unique logic
                        # For production, a more robust unique handling for unhashable types might be needed
                        # or to_list might need to restrict unique to hashable items.
                        # For now, we let it pass through if unhashable and not a known collection.
                        # Or, re-raise, or use a custom hash_dict as originally intended.
                        # Using the provided hash_dict structure:
                        try:
                            hash_val = hash_dict(x)
                        except TypeError:  # pragma: no cover
                            # If hash_dict also fails, this item cannot be added to 'seen' set with hashing.
                            # A more complex unique check (e.g., deep comparison) would be needed.
                            # For simplicity, we'll skip adding unhashable items to 'seen' if hash_dict fails,
                            # meaning duplicates of such unhashable items might pass through.
                            # Or, we can raise an error. Let's allow it to pass for now.
                            pass  # Fall through, item won't be added to seen, effectively allowing it.
                except Exception:  # pragma: no cover
                    # Broad exception if custom hashing fails, treat as unhashable for uniqueness.
                    pass

            if hash_val is not None:
                if hash_val not in seen:
                    seen.add(hash_val)
                    out.append(x)
            else:  # Item was unhashable by standard hash and custom attempts
                # To maintain uniqueness for unhashable items, one might compare by string representation
                # or implement a more sophisticated check. For now, append if truly unhashable.
                # This part is tricky; a robust general unique for unhashables is complex.
                # A simple approach: if it's not hashable, it's unique in its own right for this list.
                # However, the original intent of `seen.add(x)` would fail.
                # Let's try to add based on object identity or skip if unhashable.
                # For simplicity, if unhashable and not processed by hash_dict, we add it.
                # This means true duplicates of unhashable objects might appear if not identical objects.
                is_seen_unhashable = False  # pragma: no cover
                for seen_item in out:  # pragma: no cover
                    if (
                        x is seen_item
                    ):  # Check for identity for unhashable items already added
                        is_seen_unhashable = True
                        break
                if not is_seen_unhashable:  # pragma: no cover
                    out.append(x)
        return out

    return processed
