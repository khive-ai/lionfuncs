# Copyright (c) 2023 - 2025, HaiyangLi <quantocean.li at gmail dot com>
#
# SPDX-License-Identifier: Apache-2.0

"""
Asynchronous utilities including advanced call functions, decorators for
concurrency and throttling, and wrappers for anyio primitives.
"""

import asyncio
import functools
import time as std_time
from collections.abc import AsyncGenerator
from collections.abc import Awaitable as CAwaitable
from typing import Any, Callable, Optional, TypeVar, cast

import anyio
from pydantic import BaseModel, Field
from pydantic_core import PydanticUndefined

from lionfuncs.concurrency import CapacityLimiter, Semaphore
from lionfuncs.utils import force_async, is_coro_func, to_list

T = TypeVar("T")
R = TypeVar("R")

UNDEFINED = PydanticUndefined

__all__ = [
    "Throttle",
    "throttle",
    "max_concurrent",
    "alcall",
    "bcall",
    "ALCallParams",
    "BCallParams",
    "CallParams",
    "UNDEFINED",
    "CancelScope",
    "TaskGroup",
    "parallel_map",
]


class Throttle:
    """
    Provides a throttling mechanism for function calls.
    Ensures that the decorated function can only be called once per specified period.
    """

    def __init__(self, period: float) -> None:
        self.period = period
        self.last_called_sync: float = 0.0
        self.last_called_async: float = 0.0
        self._async_lock = asyncio.Lock()

    def __call__(
        self, func: Callable[..., T]
    ) -> Callable[..., T]:  # For synchronous functions
        """Decorate a synchronous function with the throttling mechanism."""

        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            current_time = std_time.time()
            elapsed = current_time - self.last_called_sync
            if elapsed < self.period:
                std_time.sleep(self.period - elapsed)
            self.last_called_sync = std_time.time()
            return func(*args, **kwargs)

        return wrapper

    async def call_async_throttled(
        self, func: Callable[..., CAwaitable[Any]], *args, **kwargs
    ) -> Any:
        """Helper to call an async function with throttling."""
        async with self._async_lock:
            try:
                current_time = anyio.current_time()
            except RuntimeError:  # pragma: no cover
                current_time = std_time.time()

            elapsed = current_time - self.last_called_async
            if elapsed < self.period:
                await anyio.sleep(self.period - elapsed)

            try:
                self.last_called_async = anyio.current_time()
            except RuntimeError:  # pragma: no cover
                self.last_called_async = std_time.time()

        return await func(*args, **kwargs)


def throttle(period: float) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """
    Throttle function execution to limit the rate of calls.
    Works for both synchronous and asynchronous functions.

    Args:
        period: The minimum time period (in seconds) between calls.
    """
    throttle_instance = Throttle(period)

    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        if is_coro_func(func):

            @functools.wraps(func)
            async def async_wrapper(*args, **kwargs) -> Any:
                return await throttle_instance.call_async_throttled(
                    func, *args, **kwargs
                )

            return async_wrapper
        else:
            # Apply the sync throttler
            return throttle_instance(func)

    return decorator


def max_concurrent(
    limit: int,
) -> Callable[[Callable[..., CAwaitable[Any]]], Callable[..., CAwaitable[Any]]]:
    """
    Limit the concurrency of async function execution using a semaphore.
    If the function is synchronous, it will be wrapped to run in a thread pool.

    Args:
        limit: The maximum number of concurrent executions.
    """
    if limit < 1:
        raise ValueError("Concurrency limit must be at least 1")

    semaphore = Semaphore(limit)

    def decorator(func: Callable[..., Any]) -> Callable[..., CAwaitable[Any]]:
        processed_func = func
        if not is_coro_func(processed_func):
            processed_func = force_async(processed_func)

        @functools.wraps(processed_func)
        async def wrapper(*args, **kwargs) -> Any:
            async with semaphore:
                return await processed_func(*args, **kwargs)

        return wrapper

    return decorator


class CallParams(BaseModel):
    """Base model for call parameters, allowing arbitrary args and kwargs."""

    args: tuple = Field(default_factory=tuple)
    kwargs: dict = Field(default_factory=dict)

    model_config = {"arbitrary_types_allowed": True}


class ALCallParams(CallParams):
    func: Optional[Callable[..., Any]] = None
    sanitize_input: bool = False
    unique_input: bool = False
    num_retries: int = 0
    initial_delay: float = 0.0
    retry_delay: float = 0.0
    backoff_factor: float = 1.0
    retry_default: Any = Field(default_factory=lambda: UNDEFINED)
    retry_timeout: Optional[float] = None
    retry_timing: bool = False
    max_concurrent: Optional[int] = None
    throttle_period: Optional[float] = None
    flatten: bool = False
    dropna: bool = False
    unique_output: bool = False
    flatten_tuple_set: bool = False

    async def __call__(
        self,
        input_: Any,
        func: Optional[Callable[..., Any]] = None,
        **additional_kwargs,
    ):
        if self.func is None and func is None:
            raise ValueError(
                "A sync/async func must be provided either at initialization or call time."
            )  # pragma: no cover

        # Merge kwargs from initialization and call time
        merged_kwargs = {**self.kwargs, **additional_kwargs}

        return await alcall(
            input_,
            func or self.func,  # type: ignore
            *self.args,
            sanitize_input=self.sanitize_input,
            unique_input=self.unique_input,
            num_retries=self.num_retries,
            initial_delay=self.initial_delay,
            retry_delay=self.retry_delay,
            backoff_factor=self.backoff_factor,
            retry_default=self.retry_default,
            retry_timeout=self.retry_timeout,
            retry_timing=self.retry_timing,
            max_concurrent=self.max_concurrent,
            throttle_period=self.throttle_period,
            flatten=self.flatten,
            dropna=self.dropna,
            unique_output=self.unique_output,
            flatten_tuple_set=self.flatten_tuple_set,
            **merged_kwargs,
        )


async def alcall(
    input_: list[Any],
    func: Callable[..., T],
    /,
    *,
    sanitize_input: bool = False,
    unique_input: bool = False,
    num_retries: int = 0,
    initial_delay: float = 0.0,
    retry_delay: float = 0.0,
    backoff_factor: float = 1.0,
    retry_default: Any = UNDEFINED,
    retry_timeout: Optional[float] = None,
    retry_timing: bool = False,
    max_concurrent: Optional[int] = None,
    throttle_period: Optional[float] = None,
    flatten: bool = False,
    dropna: bool = False,
    unique_output: bool = False,
    flatten_tuple_set: bool = False,
    **kwargs: Any,
) -> list[Any]:
    if not callable(func):  # pragma: no cover
        try:
            func_list = list(func)  # type: ignore
        except TypeError:
            raise ValueError(
                "func must be callable or an iterable containing one callable."
            )
        if len(func_list) != 1 or not callable(func_list[0]):
            raise ValueError("Only one callable function is allowed.")
        func = func_list[0]

    processed_input_: list[Any]
    if sanitize_input:
        processed_input_ = to_list(
            input_,
            flatten=True,
            dropna=True,
            unique=unique_input,
            flatten_tuple_set=flatten_tuple_set,
        )
    else:
        if not isinstance(input_, list):  # pragma: no cover
            if isinstance(input_, BaseModel):
                processed_input_ = [input_]
            else:
                try:
                    iter(input_)
                    processed_input_ = list(input_)
                except TypeError:
                    processed_input_ = [input_]
        else:
            processed_input_ = input_

    if initial_delay > 0:
        await anyio.sleep(initial_delay)

    semaphore: Optional[Semaphore] = (
        Semaphore(max_concurrent) if max_concurrent and max_concurrent > 0 else None
    )

    async def call_func_internal(item_internal: Any) -> T:
        if is_coro_func(func):
            if retry_timeout is not None:
                with anyio.move_on_after(retry_timeout):
                    return await func(item_internal, **kwargs)
                raise asyncio.TimeoutError(
                    f"Call to {func.__name__} timed out after {retry_timeout}s"
                )
            else:
                return await func(item_internal, **kwargs)
        else:
            if retry_timeout is not None:
                with anyio.move_on_after(retry_timeout):
                    return await anyio.to_thread.run_sync(func, item_internal, **kwargs)  # type: ignore
                raise asyncio.TimeoutError(
                    f"Call to {func.__name__} timed out after {retry_timeout}s"
                )
            else:
                return await anyio.to_thread.run_sync(func, item_internal, **kwargs)  # type: ignore

    async def execute_task(i: Any, index: int) -> Any:
        start_time = anyio.current_time()
        attempts = 0
        current_delay_val = retry_delay
        while True:
            try:
                result = await call_func_internal(i)
                if retry_timing:
                    end_time = anyio.current_time()
                    return index, result, end_time - start_time
                else:
                    return index, result
            except asyncio.CancelledError:  # pragma: no cover
                raise
            except Exception:  # Catch broad exceptions for retry logic
                attempts += 1
                if attempts <= num_retries:
                    if current_delay_val > 0:
                        await anyio.sleep(current_delay_val)
                        current_delay_val *= backoff_factor
                else:
                    if retry_default is not UNDEFINED:
                        if retry_timing:
                            end_time = anyio.current_time()
                            duration = end_time - start_time
                            return index, retry_default, duration
                        else:
                            return index, retry_default
                    raise

    async def task_wrapper(item_wrapper: Any, idx_wrapper: int) -> Any:
        task_result: Any
        if semaphore:
            async with semaphore:
                task_result = await execute_task(item_wrapper, idx_wrapper)
        else:
            task_result = await execute_task(item_wrapper, idx_wrapper)

        if throttle_period and throttle_period > 0:
            await anyio.sleep(throttle_period)
        return task_result

    tasks = [task_wrapper(item, idx) for idx, item in enumerate(processed_input_)]

    try:
        completed_results_with_indices = await asyncio.gather(*tasks)
    except Exception as e:  # pragma: no cover
        raise e

    completed_results_with_indices.sort(key=lambda x: x[0])

    final_results: list[Any]
    if retry_timing:
        final_results = [
            (r_val[1], r_val[2])
            for r_val in completed_results_with_indices
            if not (dropna and (r_val[1] is None or r_val[1] is UNDEFINED))
        ]
    else:
        output_list = [r_val[1] for r_val in completed_results_with_indices]
        final_results = to_list(
            output_list,
            flatten=flatten,
            dropna=dropna,
            unique=unique_output,
            flatten_tuple_set=flatten_tuple_set,
        )
    return final_results


class BCallParams(CallParams):
    func: Optional[Callable[..., Any]] = None
    batch_size: int
    sanitize_input: bool = False
    unique_input: bool = False
    num_retries: int = 0
    initial_delay: float = 0.0
    retry_delay: float = 0.0
    backoff_factor: float = 1.0
    retry_default: Any = Field(default_factory=lambda: UNDEFINED)
    retry_timeout: Optional[float] = None
    retry_timing: bool = False
    max_concurrent: Optional[int] = None
    throttle_period: Optional[float] = None
    flatten: bool = False
    dropna: bool = False
    unique_output: bool = False
    flatten_tuple_set: bool = False

    async def __call__(
        self,
        input_: Any,
        func: Optional[Callable[..., Any]] = None,
        **additional_kwargs,
    ):
        if self.func is None and func is None:
            raise ValueError(
                "A sync/async func must be provided either at initialization or call time."
            )  # pragma: no cover

        merged_kwargs = {**self.kwargs, **additional_kwargs}

        return bcall(
            input_,
            func or self.func,  # type: ignore
            self.batch_size,
            *self.args,
            sanitize_input=self.sanitize_input,
            unique_input=self.unique_input,
            num_retries=self.num_retries,
            initial_delay=self.initial_delay,
            retry_delay=self.retry_delay,
            backoff_factor=self.backoff_factor,
            retry_default=self.retry_default,
            retry_timeout=self.retry_timeout,
            retry_timing=self.retry_timing,
            max_concurrent=self.max_concurrent,
            throttle_period=self.throttle_period,
            flatten=self.flatten,
            dropna=self.dropna,
            unique_output=self.unique_output,
            flatten_tuple_set=self.flatten_tuple_set,
            **merged_kwargs,
        )


async def bcall(
    input_: Any,
    func: Callable[..., T],
    /,
    batch_size: int,
    *,
    sanitize_input: bool = False,
    unique_input: bool = False,
    num_retries: int = 0,
    initial_delay: float = 0.0,
    retry_delay: float = 0.0,
    backoff_factor: float = 1.0,
    retry_default: Any = UNDEFINED,
    retry_timeout: Optional[float] = None,
    retry_timing: bool = False,
    max_concurrent: Optional[int] = None,
    throttle_period: Optional[float] = None,
    flatten: bool = False,
    dropna: bool = False,
    unique_output: bool = False,
    flatten_tuple_set: bool = False,
    **kwargs: Any,
) -> AsyncGenerator[list[Any], None]:
    processed_bcall_input = to_list(input_, flatten=True, dropna=True, unique=False)

    if batch_size <= 0:
        raise ValueError("batch_size must be positive.")  # pragma: no cover

    for i in range(0, len(processed_bcall_input), batch_size):
        batch = processed_bcall_input[i : i + batch_size]
        yield await alcall(
            batch,
            func,
            sanitize_input=sanitize_input,
            unique_input=unique_input,
            num_retries=num_retries,
            initial_delay=initial_delay,
            retry_delay=retry_delay,
            backoff_factor=backoff_factor,
            retry_default=retry_default,
            retry_timeout=retry_timeout,
            retry_timing=retry_timing,
            max_concurrent=max_concurrent,
            throttle_period=throttle_period,
            flatten=flatten,
            dropna=dropna,
            unique_output=unique_output,
            flatten_tuple_set=flatten_tuple_set,
            **kwargs,
        )


class CancelScope:
    """
    A context manager for controlling cancellation of tasks, wrapping anyio.CancelScope.
    """

    def __init__(self, *, deadline: float = float("inf"), shield: bool = False):
        self._deadline = deadline
        self._shield = shield
        self._internal_anyio_scope_instance: Optional[anyio.CancelScope] = None
        self._cancel_called_before_enter: bool = False

    def cancel(self) -> None:
        if self._internal_anyio_scope_instance:
            self._internal_anyio_scope_instance.cancel()
        else:
            self._cancel_called_before_enter = True

    async def __aenter__(self) -> "CancelScope":
        self._internal_anyio_scope_instance = anyio.CancelScope(
            deadline=self._deadline, shield=self._shield
        )
        if self._cancel_called_before_enter:
            self._internal_anyio_scope_instance.cancel()

        await self._internal_anyio_scope_instance.__aenter__()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> Optional[bool]:
        if self._internal_anyio_scope_instance:
            return await self._internal_anyio_scope_instance.__aexit__(
                exc_type, exc_val, exc_tb
            )
        return False

    @property
    def cancelled_caught(self) -> bool:  # pragma: no cover
        if self._internal_anyio_scope_instance:
            return self._internal_anyio_scope_instance.cancelled_caught
        return False

    @property
    def deadline(self) -> float:  # pragma: no cover
        if self._internal_anyio_scope_instance:
            return self._internal_anyio_scope_instance.deadline
        return self._deadline

    @deadline.setter
    def deadline(self, value: float) -> None:  # pragma: no cover
        self._deadline = value
        if self._internal_anyio_scope_instance:
            self._internal_anyio_scope_instance.deadline = value

    @property
    def shield(self) -> bool:  # pragma: no cover
        if self._internal_anyio_scope_instance:
            return self._internal_anyio_scope_instance.shield
        return self._shield

    @shield.setter
    def shield(self, value: bool) -> None:  # pragma: no cover
        self._shield = value
        if self._internal_anyio_scope_instance:
            self._internal_anyio_scope_instance.shield = value


class TaskGroup:
    """
    A group of tasks that are treated as a unit, wrapping anyio.abc.TaskGroup.
    """

    def __init__(self):
        self._anyio_task_group: Optional[anyio.abc.TaskGroup] = None

    def start_soon(
        self, func: Callable[..., CAwaitable[Any]], *args: Any, name: Any = None
    ) -> None:
        if self._anyio_task_group is None:  # pragma: no cover
            raise RuntimeError(
                "Task group is not active. Use 'async with TaskGroup():'"
            )
        self._anyio_task_group.start_soon(func, *args, name=name)

    async def __aenter__(self) -> "TaskGroup":
        self._anyio_task_group = anyio.create_task_group()
        await self._anyio_task_group.__aenter__()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> Optional[bool]:
        if self._anyio_task_group:
            return await self._anyio_task_group.__aexit__(exc_type, exc_val, exc_tb)
        return False  # pragma: no cover


async def parallel_map(
    func: Callable[[T], CAwaitable[R]],
    items: list[T],
    max_concurrency: int = 10,
) -> list[R]:
    """
    Apply an async function to each item in a list in parallel, with limited concurrency.

    Args:
        func: The asynchronous function to apply to each item.
        items: The list of items to process.
        max_concurrency: The maximum number of concurrent executions.

    Returns:
        A list of results in the same order as the input items.

    Raises:
        Exception: Propagates the first exception encountered from any of the tasks.
    """
    if max_concurrency < 1:
        raise ValueError("max_concurrency must be at least 1")  # pragma: no cover

    limiter = CapacityLimiter(max_concurrency)
    results: list[Optional[R]] = [None] * len(items)
    exceptions: list[Optional[Exception]] = [None] * len(items)

    async def _worker(index: int, item: T) -> None:
        async with limiter:
            try:
                results[index] = await func(item)
            except Exception as exc:  # pylint: disable=broad-except
                exceptions[index] = exc

    async with TaskGroup() as tg:
        for i, item_val in enumerate(items):
            tg.start_soon(_worker, i, item_val)

    first_exception = None
    for exc in exceptions:
        if exc is not None:
            first_exception = exc
            break

    if first_exception:
        raise first_exception

    return cast(list[R], results)
