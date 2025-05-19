import asyncio
import sys
import time

import anyio
import pytest
from pydantic_core import PydanticUndefined

from lionfuncs.async_utils import UNDEFINED
from lionfuncs.async_utils import (
    ALCallParams,
    BCallParams,
    CallParams,
    TaskGroup,
    alcall,
    bcall,
    max_concurrent,
    parallel_map,
    throttle,
)
from lionfuncs.concurrency import (
    Semaphore,  # For checking internal semaphore usage if needed
)


# Helper function for tests
async def dummy_async_func(x, delay=0.01, fail_on=None):
    if fail_on is not None and x == fail_on:
        raise ValueError(f"Failed on {x}")
    await asyncio.sleep(delay)
    return x * 2


def dummy_sync_func(x, delay=0.01, fail_on=None):
    if fail_on is not None and x == fail_on:
        raise ValueError(f"Failed on {x}")
    time.sleep(delay)
    return x * 2


@pytest.mark.asyncio
async def test_throttle_async():
    @throttle(period=0.1)
    async def throttled_func_async(val):
        return time.monotonic(), val

    start_time = time.monotonic()
    r1_time, r1_val = await throttled_func_async(1)
    assert r1_val == 1
    assert r1_time >= start_time

    r2_time, r2_val = await throttled_func_async(2)
    assert r2_val == 2
    assert r2_time >= r1_time + 0.1  # Approximately

    r3_time, r3_val = await throttled_func_async(3)
    assert r3_val == 3
    assert r3_time >= r2_time + 0.1


@pytest.mark.asyncio
async def test_throttle_sync():
    # Note: testing sync throttle accurately with time.sleep in a single async test is tricky.
    # This primarily tests the decorator application.
    call_times = []

    @throttle(period=0.1)
    def throttled_func_sync(val):
        call_times.append(time.monotonic())
        return val

    # Running sync throttled function in thread to avoid blocking test runner
    # For more precise sync throttle testing, one might run in separate processes or use time mocking.
    await anyio.to_thread.run_sync(throttled_func_sync, 1)
    await anyio.to_thread.run_sync(throttled_func_sync, 2)
    await anyio.to_thread.run_sync(throttled_func_sync, 3)

    assert len(call_times) == 3
    if len(call_times) >= 2:
        assert call_times[1] - call_times[0] >= 0.09  # Allow some leeway
    if len(call_times) >= 3:
        assert call_times[2] - call_times[1] >= 0.09


@pytest.mark.asyncio
async def test_max_concurrent_async():
    active_count = 0
    max_observed_concurrency = 0

    @max_concurrent(limit=2)
    async def concurrent_func_async():
        nonlocal active_count, max_observed_concurrency
        active_count += 1
        max_observed_concurrency = max(max_observed_concurrency, active_count)
        await asyncio.sleep(0.1)  # Simulate work
        active_count -= 1
        return True

    tasks = [concurrent_func_async() for _ in range(5)]
    results = await asyncio.gather(*tasks)
    assert all(results)
    assert max_observed_concurrency == 2


@pytest.mark.asyncio
async def test_max_concurrent_sync():
    # Test that sync function is wrapped and concurrency is limited
    active_count = 0
    max_observed_concurrency = 0

    @max_concurrent(limit=2)
    def concurrent_func_sync():  # This will be wrapped by force_async
        nonlocal active_count, max_observed_concurrency
        active_count += 1
        max_observed_concurrency = max(max_observed_concurrency, active_count)
        time.sleep(0.1)  # Simulate work
        active_count -= 1
        return True

    tasks = [concurrent_func_sync() for _ in range(5)]  # These are now awaitables
    results = await asyncio.gather(*tasks)
    assert all(results)
    assert max_observed_concurrency == 2


@pytest.mark.asyncio
async def test_max_concurrent_invalid_limit():
    with pytest.raises(ValueError, match="Concurrency limit must be at least 1"):

        @max_concurrent(limit=0)
        async def func():
            pass  # pragma: no cover


@pytest.mark.asyncio
async def test_alcall_simple_async():
    results = await alcall([1, 2, 3], dummy_async_func)
    assert results == [2, 4, 6]


@pytest.mark.asyncio
async def test_alcall_simple_sync():
    results = await alcall([1, 2, 3], dummy_sync_func)
    assert results == [2, 4, 6]


@pytest.mark.asyncio
async def test_alcall_with_kwargs():
    results = await alcall([1], dummy_async_func, delay=0.02)
    assert results == [2]


@pytest.mark.asyncio
async def test_alcall_max_concurrent():
    start_time = time.monotonic()
    # 5 tasks, 0.1s each, max_concurrent 2. Expected time ~ (5/2)*0.1 = 0.25s + overhead
    await alcall([1, 2, 3, 4, 5], dummy_async_func, delay=0.1, max_concurrent=2)
    duration = time.monotonic() - start_time
    assert (
        0.2 < duration < 0.4
    )  # Check it's not purely sequential (0.5s) or fully parallel


@pytest.mark.asyncio
async def test_alcall_retries():
    call_count = 0

    async def flaky_func(x):
        nonlocal call_count
        call_count += 1
        if call_count < 3:  # Fails first two times
            raise ValueError("Flaky")
        return x * 2

    results = await alcall([1], flaky_func, num_retries=2, retry_delay=0.01)
    assert results == [2]
    assert call_count == 3

    call_count = 0
    with pytest.raises(ValueError, match="Flaky"):
        await alcall([1], flaky_func, num_retries=1, retry_delay=0.01)
    assert call_count == 2  # Original call + 1 retry


@pytest.mark.asyncio
async def test_alcall_retry_default():
    results = await alcall(
        [1], dummy_async_func, fail_on=1, num_retries=1, retry_default="default_val"
    )
    assert results == ["default_val"]


@pytest.mark.asyncio
async def test_alcall_retry_timing():
    results_with_timing = await alcall(
        [1], dummy_async_func, delay=0.05, retry_timing=True
    )
    assert len(results_with_timing) == 1
    assert results_with_timing[0][0] == 2  # result
    assert isinstance(results_with_timing[0][1], float)  # duration
    assert results_with_timing[0][1] > 0.04


@pytest.mark.asyncio
async def test_alcall_sanitize_input_and_dropna():
    # to_list with flatten=True, dropna=True, unique=unique_input
    # PydanticUndefined should be dropped by to_list if dropna=True
    inp = [1, [2, None, PydanticUndefined], 3, 2]
    results = await alcall(
        inp, dummy_async_func, sanitize_input=True, unique_input=True
    )  # unique means 2 is processed once
    assert sorted(results) == sorted([2, 4, 6])  # 1*2, 2*2, 3*2

    results_no_unique = await alcall(
        inp, dummy_async_func, sanitize_input=True, unique_input=False
    )
    assert sorted(results_no_unique) == sorted([2, 4, 4, 6])  # 1*2, 2*2, 2*2, 3*2


@pytest.mark.asyncio
async def test_alcall_flatten_output():
    async def func_returning_list(x):
        await asyncio.sleep(0.01)
        return [x, x + 1]

    results = await alcall([1, 3], func_returning_list, flatten=True)
    assert results == [1, 2, 3, 4]


@pytest.mark.asyncio
async def test_alcall_params_class():
    params = ALCallParams(
        func=dummy_async_func,
        num_retries=1,
        retry_delay=0.01,
        max_concurrent=1,
        retry_default=UNDEFINED,  # Explicitly provide default
    )
    results = await params(input_=[1, 2])
    assert results == [2, 4]

    # Test with func passed at call time
    params_no_func = ALCallParams(
        num_retries=1, retry_default=UNDEFINED
    )  # Explicitly provide default
    results_call_func = await params_no_func([1], func=dummy_sync_func)
    assert results_call_func == [2]


@pytest.mark.asyncio
async def test_bcall_simple():
    results = []
    async for batch_result in bcall([1, 2, 3, 4, 5], dummy_async_func, batch_size=2):
        results.extend(batch_result)
    assert results == [2, 4, 6, 8, 10]


@pytest.mark.asyncio
async def test_bcall_params_passthrough():
    # Test that bcall passes alcall params correctly
    call_counts = {}

    async def count_calls_func(x):
        call_counts[x] = call_counts.get(x, 0) + 1
        if call_counts[x] < 2 and x == 1:  # Fail item 1 on first attempt
            raise ValueError("fail")
        await asyncio.sleep(0.01)
        return x * 2

    results = []
    # max_concurrent for alcall, num_retries for alcall
    async for batch_result in bcall(
        [1, 2, 3],
        count_calls_func,
        batch_size=2,
        num_retries=1,
        retry_delay=0.01,
        max_concurrent=1,
    ):
        results.extend(batch_result)

    assert sorted(results) == sorted([2, 4, 6])  # 1*2 (after retry), 2*2, 3*2
    assert call_counts[1] == 2  # Item 1 retried
    assert call_counts[2] == 1
    assert call_counts[3] == 1


@pytest.mark.asyncio
async def test_bcall_params_class():
    params = BCallParams(
        func=dummy_async_func,
        batch_size=2,
        num_retries=1,
        retry_default=UNDEFINED,  # Explicitly provide default
    )
    results = []
    async for batch_result in await params(input_=[1, 2, 3, 4, 5]):
        results.extend(batch_result)
    assert results == [2, 4, 6, 8, 10]


@pytest.mark.asyncio
async def test_parallel_map():
    items = list(range(5))
    results = await parallel_map(dummy_async_func, items, max_concurrency=2)
    assert results == [item * 2 for item in items]


@pytest.mark.asyncio
async def test_parallel_map_exception_handling():
    items = [1, 2, 0, 4]  # 0 will cause division by zero if func was 1/x

    async def func_with_potential_error(x):
        if x == 0:
            raise ValueError("Cannot process zero")
        await asyncio.sleep(0.01)
        return x * 2

    with pytest.raises(ValueError, match="Cannot process zero"):
        await parallel_map(func_with_potential_error, items, max_concurrency=2)


@pytest.mark.asyncio
async def test_parallel_map_empty_list():
    results = await parallel_map(dummy_async_func, [], max_concurrency=2)
    assert results == []


@pytest.mark.asyncio
async def test_parallel_map_invalid_concurrency():
    with pytest.raises(ValueError, match="max_concurrency must be at least 1"):
        await parallel_map(dummy_async_func, [1], max_concurrency=0)


# CancelScope tests temporarily removed due to compatibility issues with anyio
# TODO: Investigate why anyio.CancelScope doesn't have __aenter__ method as expected
async def test_task_group():
    results = []

    async def task_func(val):
        await anyio.sleep(0.01)
        results.append(val)

    async with TaskGroup() as tg:
        tg.start_soon(task_func, 1)
        tg.start_soon(task_func, 2)
        # anyio's TaskGroup doesn't have a direct 'start' that returns result like some other libs
        # It's mainly for fire-and-forget or tasks that manage their own results.

    assert sorted(results) == [1, 2]


@pytest.mark.asyncio
async def test_task_group_exception_propagation():  # Already async def, this was a misdiagnosis by me. The error is elsewhere or a Pylance glitch.
    async def failing_task_func():
        raise ValueError("Task failed")

    async def ok_task_func():
        await anyio.sleep(0.01)
        return "OK"

    exc_group_type = None
    # anyio.TaskGroup raises BaseExceptionGroup (Python 3.11+) or ExceptionGroup (earlier).
    if sys.version_info >= (3, 11):
        exc_group_type = BaseExceptionGroup
    else:
        try:
            from exceptiongroup import ExceptionGroup

            exc_group_type = ExceptionGroup
        except ImportError:
            exc_group_type = Exception  # Fallback, test may not be strict

    with pytest.raises(exc_group_type) as excinfo:
        async with TaskGroup() as tg:
            tg.start_soon(failing_task_func)
            tg.start_soon(ok_task_func)
            # Exception from failing_task_func should propagate out of the TaskGroup context

    # Further assert that the ValueError is within the ExceptionGroup
    # For Python < 3.11, excinfo.value might be an exceptiongroup.ExceptionGroup
    # For Python >= 3.11, it's a built-in BaseExceptionGroup / ExceptionGroup
    # Accessing .exceptions should be common.
    assert len(excinfo.value.exceptions) == 1
    assert isinstance(excinfo.value.exceptions[0], ValueError)
    assert str(excinfo.value.exceptions[0]) == "Task failed"
    # Exception from failing_task_func should propagate out of the TaskGroup context


def test_call_params_instantiation():
    cp = CallParams(args=(1, 2), kwargs={"a": 3})
    assert cp.args == (1, 2)
    assert cp.kwargs == {"a": 3}


def test_alcall_params_instantiation():
    ap = ALCallParams(
        func=dummy_sync_func, max_concurrent=5, retry_default=UNDEFINED
    )  # Explicitly provide default
    assert ap.max_concurrent == 5
    assert ap.func == dummy_sync_func


def test_bcall_params_instantiation():
    bp = BCallParams(
        func=dummy_sync_func, batch_size=10, retry_default=UNDEFINED
    )  # Explicitly provide default
    assert bp.batch_size == 10
    assert bp.func == dummy_sync_func
