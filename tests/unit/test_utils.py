import asyncio
import functools
import json
import os
from unittest import mock

import pytest

from lionfuncs import utils

# Test cases for is_coro_func
async def sample_async_func():
    pass

def sample_sync_func():
    pass

async def sample_async_gen_func():
    yield 1

class SampleClass:
    async def async_method(self):
        pass
    def sync_method(self):
        pass

@pytest.mark.parametrize(
    "func, expected",
    [
        (sample_async_func, True),
        (sample_sync_func, False),
        (sample_async_gen_func, True),
        (SampleClass().async_method, True), # Bound async method
        (SampleClass.async_method, True),   # Unbound async method
        (SampleClass().sync_method, False), # Bound sync method
        (SampleClass.sync_method, False),   # Unbound sync method
        (functools.partial(sample_async_func), True),
        (functools.partial(sample_sync_func), False),
        (lambda: "sync", False),
        (None, False), # Test with None
        (123, False), # Test with non-callable
    ],
)
def test_is_coro_func(func, expected):
    """Tests utils.is_coro_func with various inputs."""
    if func is None or not callable(func): # Handle non-callable cases for the test itself
        assert utils.is_coro_func(func) == expected
    else:
        assert utils.is_coro_func(func) == expected

# Test cases for force_async
def sync_task_simple():
    return "done"

def sync_task_with_args(a: int, b: str):
    return f"{a}-{b}"

def sync_task_raises_exception():
    raise ValueError("Sync error")

async def async_task_simple():
    await asyncio.sleep(0.01)
    return "async_done"

@pytest.mark.asyncio
async def test_force_async_with_sync_function():
    """Tests that force_async wraps a sync function correctly."""
    forced_async_task = utils.force_async(sync_task_simple)
    assert utils.is_coro_func(forced_async_task)
    result = await forced_async_task()
    assert result == "done"

@pytest.mark.asyncio
async def test_force_async_with_sync_function_args():
    """Tests force_async with a sync function that takes arguments."""
    forced_async_task = utils.force_async(sync_task_with_args)
    assert utils.is_coro_func(forced_async_task)
    result = await forced_async_task(1, b="test")
    assert result == "1-test"

@pytest.mark.asyncio
async def test_force_async_with_sync_function_raises_exception():
    """Tests force_async with a sync function that raises an exception."""
    forced_async_task = utils.force_async(sync_task_raises_exception)
    assert utils.is_coro_func(forced_async_task)
    with pytest.raises(ValueError, match="Sync error"):
        await forced_async_task()

@pytest.mark.asyncio
async def test_force_async_with_async_function():
    """Tests that force_async returns an async function unchanged."""
    forced_async_task = utils.force_async(async_task_simple)
    assert utils.is_coro_func(forced_async_task)
    assert forced_async_task is async_task_simple # Should be the same object
    result = await forced_async_task()
    assert result == "async_done"


# Test cases for get_env_bool
@pytest.mark.parametrize(
    "env_value, default, expected",
    [
        ("true", False, True),
        ("TRUE", False, True),
        ("1", False, True),
        ("yes", False, True),
        ("Y", False, True),
        ("on", False, True),
        ("false", True, False),
        ("FALSE", True, False),
        ("0", True, False),
        ("no", True, False),
        ("N", True, False),
        ("off", True, False),
        ("", False, False),      # Empty string, use default
        ("", True, True),        # Empty string, use default
        ("random", False, False),# Unrecognized, use default
        ("random", True, True),  # Unrecognized, use default
        (None, False, False),    # Variable not set, use default
        (None, True, True),      # Variable not set, use default
    ],
)
def test_get_env_bool(env_value, default, expected):
    """Tests utils.get_env_bool with various environment variable values."""
    var_name = "TEST_BOOL_VAR"
    if env_value is None: # Simulate variable not being set
        with mock.patch.dict(os.environ, clear=True): # Ensure var is not set
            if var_name in os.environ: # Defensive pop if somehow still there
                os.environ.pop(var_name)
            assert utils.get_env_bool(var_name, default) == expected
    else:
        with mock.patch.dict(os.environ, {var_name: env_value}):
            assert utils.get_env_bool(var_name, default) == expected

# Test cases for get_env_dict
@pytest.mark.parametrize(
    "env_value, default, expected",
    [
        ('{"key": "value", "num": 1}', None, {"key": "value", "num": 1}),
        ('{"nested": {"a": true}}', None, {"nested": {"a": True}}),
        ("invalid_json", {"default": "dict"}, {"default": "dict"}), # Invalid JSON, use default
        ("", {"default": "dict"}, {"default": "dict"}),             # Empty string, use default
        (None, None, None),                                         # Not set, default is None
        (None, {"default": "val"}, {"default": "val"}),             # Not set, use provided default
        ('{"key": "value"}', {"override": "me"}, {"key": "value"}), # Valid JSON overrides default
    ],
)
def test_get_env_dict(env_value, default, expected):
    """Tests utils.get_env_dict with various environment variable values."""
    var_name = "TEST_DICT_VAR"
    if env_value is None: # Simulate variable not being set
         with mock.patch.dict(os.environ, clear=True):
            if var_name in os.environ:
                os.environ.pop(var_name)
            assert utils.get_env_dict(var_name, default) == expected
    else:
        with mock.patch.dict(os.environ, {var_name: env_value}):
            assert utils.get_env_dict(var_name, default) == expected

def test_get_env_dict_json_decode_error_uses_default():
    """Tests that get_env_dict returns default on JSONDecodeError."""
    var_name = "TEST_DICT_VAR_ERROR"
    default_dict = {"error_default": True}
    with mock.patch.dict(os.environ, {var_name: "not_json"}), \
         mock.patch("json.loads", side_effect=json.JSONDecodeError("err", "doc", 0)):
        assert utils.get_env_dict(var_name, default_dict) == default_dict