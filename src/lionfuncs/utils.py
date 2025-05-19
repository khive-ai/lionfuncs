import asyncio
import functools
import inspect
import json
import os
from typing import Any, Callable, Coroutine, Dict, TypeVar, cast

R = TypeVar("R")

__all__ = [
    "is_coro_func",
    "force_async",
    "get_env_bool",
    "get_env_dict",
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

def get_env_dict(var_name: str, default: Dict[Any, Any] | None = None) -> Dict[Any, Any] | None:
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
        return cast(Dict[Any, Any], json.loads(value_str))
    except json.JSONDecodeError:
        return default