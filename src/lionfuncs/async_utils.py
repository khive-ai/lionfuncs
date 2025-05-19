# Copyright (c) 2023 - 2025, HaiyangLi <quantocean.li at gmail dot com>
#
# SPDX-License-Identifier: Apache-2.0

"""
Asynchronous utilities including advanced call functions, decorators for
concurrency and throttling, and wrappers for anyio primitives.
"""

import asyncio
import functools
import time as std_time  # Standard library time
from collections.abc import (
    Awaitable as CAwaitable,  # To avoid clash if Awaitable is used differently
)
from typing import (
    Any,
    AsyncGenerator,
    Awaitable,
    Callable,
    List,
    Optional,
    TypeVar,
    cast,
)

import anyio
from pydantic import BaseModel, Field  # For ALCallParams, BCallParams later
from pydantic_core import PydanticUndefined  # Added import

# LionError and LionConcurrencyError might be needed for more advanced features later
# from lionfuncs.errors import LionError, LionConcurrencyError
# Concurrency primitives might be used by decorators or advanced functions
from lionfuncs.concurrency import CapacityLimiter, Semaphore  # Added CapacityLimiter
from lionfuncs.utils import force_async, is_coro_func, to_list

T = TypeVar("T")
R = TypeVar("R")

UNDEFINED = PydanticUndefined  # Define UNDEFINED

__all__ = [
    "Throttle",
    "throttle",
    "max_concurrent",
    "alcall",
    "bcall",
    "ALCallParams",
    "BCallParams",
    "CallParams",  # Added CallParams
    "UNDEFINED",  # Added UNDEFINED
    "CancelScope",
    "TaskGroup",
    "parallel_map",  # Added parallel_map
    # To be added:
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
        self._async_lock = asyncio.Lock()  # For async throttling coordination

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
                # Use anyio's clock for consistency if an event loop is running
                current_time = anyio.current_time()
            except RuntimeError:  # pragma: no cover
                # Fallback if no anyio event loop (e.g. called from sync context without anyio.run)
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

    # Use lionfuncs.concurrency.Semaphore which wraps anyio.Semaphore
    semaphore = Semaphore(limit)

    def decorator(func: Callable[..., Any]) -> Callable[..., CAwaitable[Any]]:
        processed_func = func
        if not is_coro_func(processed_func):
            # force_async from lionfuncs.utils should handle running sync func in thread
            processed_func = force_async(processed_func)

        @functools.wraps(processed_func)
        async def wrapper(*args, **kwargs) -> Any:
            async with semaphore:  # Use the Semaphore as an async context manager
                return await processed_func(*args, **kwargs)

        return wrapper

    return decorator


class CallParams(BaseModel):
    """Base model for call parameters, allowing arbitrary args and kwargs."""

    args: tuple = Field(default_factory=tuple)
    kwargs: dict = Field(default_factory=dict)

    model_config = {"arbitrary_types_allowed": True}


class ALCallParams(CallParams):
    func: Optional[Callable[..., Any]] = (
        None  # Make func optional as it can be passed to __call__
    )
    sanitize_input: bool = False
    unique_input: bool = False
    num_retries: int = 0
    initial_delay: float = 0.0  # Corrected from int to float
    retry_delay: float = 0.0  # Corrected from int to float
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
    input_: List[Any],
    func: Callable[..., T],
    /,
    *,
    sanitize_input: bool = False,
    unique_input: bool = False,
    num_retries: int = 0,
    initial_delay: float = 0.0,
    retry_delay: float = 0.0,
    backoff_factor: float = 1.0,
    retry_default: Any = UNDEFINED,  # This will now use the global UNDEFINED
    retry_timeout: Optional[float] = None,
    retry_timing: bool = False,
    max_concurrent: Optional[int] = None,
    throttle_period: Optional[float] = None,
    flatten: bool = False,
    dropna: bool = False,
    unique_output: bool = False,
    flatten_tuple_set: bool = False,
    **kwargs: Any,
) -> List[
    Any
]:  # Return type changed to List[Any] to accommodate retry_default and timing tuple
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

    processed_input_: List[Any]
    if sanitize_input:
        processed_input_ = to_list(
            input_,
            flatten=True,  # alcall's sanitize implies deep flatten and clean
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

    if initial_delay > 0:  # Allow zero initial_delay
        await anyio.sleep(initial_delay)

    # Use lionfuncs.concurrency.Semaphore
    semaphore: Optional[Semaphore] = (
        Semaphore(max_concurrent) if max_concurrent and max_concurrent > 0 else None
    )

    async def call_func_internal(item_internal: Any) -> T:
        if is_coro_func(func):
            if retry_timeout is not None:
                with anyio.move_on_after(retry_timeout):
                    return await func(item_internal, **kwargs)
                # If timeout occurs, anyio raises TimeoutError (or specific backend error)
                # This will be caught by the broader Exception in execute_task
                raise asyncio.TimeoutError(
                    f"Call to {func.__name__} timed out after {retry_timeout}s"
                )  # Should be caught
            else:
                return await func(item_internal, **kwargs)
        else:
            # Run synchronous function in a thread
            if retry_timeout is not None:
                with anyio.move_on_after(retry_timeout):
                    return await anyio.to_thread.run_sync(func, item_internal, **kwargs)  # type: ignore
                raise asyncio.TimeoutError(
                    f"Call to {func.__name__} timed out after {retry_timeout}s"
                )  # Should be caught
            else:
                return await anyio.to_thread.run_sync(func, item_internal, **kwargs)  # type: ignore

    async def execute_task(i: Any, index: int) -> Any:  # Return type Any for tuple
        # Use anyio's clock
        start_time = anyio.current_time()
        attempts = 0
        current_delay_val = retry_delay  # Renamed to avoid conflict
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
            except Exception as e:  # Catch broad exceptions for retry logic
                attempts += 1
                if attempts <= num_retries:
                    if current_delay_val > 0:  # Allow zero retry_delay
                        await anyio.sleep(current_delay_val)
                        current_delay_val *= backoff_factor
                else:
                    if (
                        retry_default is not UNDEFINED
                    ):  # This will now use the global UNDEFINED
                        if retry_timing:
                            end_time = anyio.current_time()
                            duration = end_time - start_time
                            return index, retry_default, duration
                        else:
                            return index, retry_default
                    raise  # Re-raise the last exception if all retries fail and no default

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

    # Using anyio.TaskGroup for structured concurrency
    # completed_results: List[Any] = [None] * len(tasks) # Pre-allocate for sorting
    # async with anyio.create_task_group() as tg:
    #     for i, task_coro in enumerate(tasks):
    #         # Need a way to store result with original index if using TaskGroup like this
    #         # Or, gather results and sort, which is simpler.
    #         # tg.start_soon(async def() completed_results[i] = await task_coro)
    # For simplicity and to match original structure of sorting after gather:

    # return_exceptions=False means exceptions will propagate from asyncio.gather
    # This is generally good, as the retry logic in execute_task should handle retriable errors.
    # If an error escapes execute_task (e.g. after all retries), gather will raise it.
    try:
        completed_results_with_indices = await asyncio.gather(*tasks)
    except Exception as e:  # pragma: no cover
        # This block would catch non-retriable errors that escape execute_task
        # or errors from asyncio.gather itself.
        # Depending on desired behavior, could re-raise or handle.
        # For now, let it propagate as per original implicit behavior.
        raise e

    completed_results_with_indices.sort(key=lambda x: x[0])  # Sort by original index

    final_results: List[Any]
    if retry_timing:
        # item is (original_index, result_value, duration)
        final_results = [
            (r_val[1], r_val[2])
            for r_val in completed_results_with_indices
            if not (
                dropna and (r_val[1] is None or r_val[1] is UNDEFINED)
            )  # This will now use the global UNDEFINED
        ]
    else:
        # item is (original_index, result_value)
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
    func: Optional[Callable[..., Any]] = None  # Make func optional
    batch_size: int
    sanitize_input: bool = False
    unique_input: bool = False  # Applies to alcall's sanitize_input for each batch
    num_retries: int = 0
    initial_delay: float = 0.0
    retry_delay: float = 0.0
    backoff_factor: float = 1.0
    retry_default: Any = Field(default_factory=lambda: UNDEFINED)
    retry_timeout: Optional[float] = None
    retry_timing: bool = False
    max_concurrent: Optional[int] = None  # Applies to alcall for each batch
    throttle_period: Optional[float] = None  # Applies to alcall for each batch
    flatten: bool = False  # Applies to alcall's output for each batch
    dropna: bool = False  # Applies to alcall's output for each batch
    unique_output: bool = False  # Applies to alcall's output for each batch
    flatten_tuple_set: bool = False  # Applies to alcall's output for each batch

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

        # bcall itself is an async generator
        # The __call__ should return this generator
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
    retry_default: Any = UNDEFINED,  # This will now use the global UNDEFINED
    retry_timeout: Optional[float] = None,
    retry_timing: bool = False,
    max_concurrent: Optional[int] = None,
    throttle_period: Optional[float] = None,
    flatten: bool = False,
    dropna: bool = False,
    unique_output: bool = False,
    flatten_tuple_set: bool = False,
    **kwargs: Any,
) -> AsyncGenerator[List[Any], None]:  # Return type matches alcall's output list
    # Input to bcall should be pre-processed if needed before batching
    # The original `dev/concurrency.py` bcall used to_list(input_, flatten=True, dropna=True)
    # This implies the main input_ to bcall is fully flattened and cleaned first.
    processed_bcall_input = to_list(
        input_, flatten=True, dropna=True, unique=False
    )  # unique applies per batch if sanitize_input is true for alcall

    if batch_size <= 0:
        raise ValueError("batch_size must be positive.")  # pragma: no cover

    for i in range(0, len(processed_bcall_input), batch_size):
        batch = processed_bcall_input[i : i + batch_size]
        yield await alcall(
            batch,
            func,
            sanitize_input=sanitize_input,  # Passed to alcall for per-batch sanitization
            unique_input=unique_input,  # Passed to alcall for per-batch uniqueness
            num_retries=num_retries,
            initial_delay=initial_delay,
            retry_delay=retry_delay,
            backoff_factor=backoff_factor,
            retry_default=retry_default,
            retry_timeout=retry_timeout,
            retry_timing=retry_timing,
            max_concurrent=max_concurrent,
            throttle_period=throttle_period,
            flatten=flatten,  # Controls flattening of alcall's *output* for this batch
            dropna=dropna,  # Controls dropna of alcall's *output* for this batch
            unique_output=unique_output,  # Controls unique on alcall's *output* for this batch
            flatten_tuple_set=flatten_tuple_set,  # Passed to alcall for its to_list calls
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
        self._cancel_called_before_enter: bool = (
            False  # To mimic anyio behavior if cancel() is called early
        )

    def cancel(self) -> None:
        if self._internal_anyio_scope_instance:
            self._internal_anyio_scope_instance.cancel()
        else:
            # If the scope hasn't been entered, mark that cancel was called.
            # anyio.CancelScope itself doesn't error if cancel() is called before __aenter__,
            # it just means the scope will be immediately cancelled upon entry.
            self._cancel_called_before_enter = True

    async def __aenter__(self) -> "CancelScope":
        self._internal_anyio_scope_instance = anyio.CancelScope(
            deadline=self._deadline, shield=self._shield
        )
        # If cancel was called before entering, apply it now.
        if self._cancel_called_before_enter:
            self._internal_anyio_scope_instance.cancel()

        # Now, correctly enter the internal anyio.CancelScope
        # The `async with` statement on *our* CancelScope handles its own __aenter__/__aexit__.
        # We are managing the *internal* scope here.
        await self._internal_anyio_scope_instance.__aenter__()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> Optional[bool]:
        if self._internal_anyio_scope_instance:
            # Exit the internal anyio.CancelScope
            return await self._internal_anyio_scope_instance.__aexit__(
                exc_type, exc_val, exc_tb
            )
        return False  # Should not happen if used correctly

    @property
    def cancelled_caught(self) -> bool:  # pragma: no cover
        if self._internal_anyio_scope_instance:
            return self._internal_anyio_scope_instance.cancelled_caught
        return False  # Or perhaps True if _cancel_called_before_enter and it was a timeout? anyio is subtle.

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
    ) -> None:  # Changed to sync
        if self._anyio_task_group is None:  # pragma: no cover
            raise RuntimeError(
                "Task group is not active. Use 'async with TaskGroup():'"
            )
        self._anyio_task_group.start_soon(
            func, *args, name=name
        )  # anyio's start_soon is sync

    # anyio's TaskGroup.start method is for tasks that signal readiness.
    # Not directly wrapping it unless a clear use case emerges for it in lionfuncs.
    # async def start(self, func: Callable[..., CAwaitable[R]], *args: Any, name: Any = None) -> R:
    #     if self._anyio_task_group is None: # pragma: no cover
    #         raise RuntimeError("Task group is not active. Use 'async with TaskGroup():'")
    #     return await self._anyio_task_group.start(func, *args, name=name) # type: ignore

    async def __aenter__(self) -> "TaskGroup":
        # import anyio # Already imported
        # anyio.create_task_group() returns an anyio.abc.TaskGroup
        self._anyio_task_group = anyio.create_task_group()
        await self._anyio_task_group.__aenter__()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> Optional[bool]:
        if self._anyio_task_group:
            return await self._anyio_task_group.__aexit__(exc_type, exc_val, exc_tb)
        return False  # pragma: no cover


async def parallel_map(
    func: Callable[[T], CAwaitable[R]],  # Use CAwaitable for Async TypedDict
    items: List[T],
    max_concurrency: int = 10,
) -> List[R]:
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
    exceptions: list[Optional[Exception]] = [None] * len(items)  # To store exceptions

    async def _worker(index: int, item: T) -> None:
        async with limiter:
            try:
                results[index] = await func(item)
            except Exception as exc:  # pylint: disable=broad-except
                exceptions[index] = exc

    async with TaskGroup() as tg:  # Using the TaskGroup wrapper
        for i, item_val in enumerate(items):
            tg.start_soon(_worker, i, item_val)  # Use start_soon from TaskGroup wrapper

    # After task group exits, check for exceptions
    first_exception = None
    for exc in exceptions:
        if exc is not None:
            first_exception = exc
            break

    if first_exception:
        raise first_exception

    # All results should be populated if no exception was raised and propagated
    # Cast is safe here if no exception was raised.
    return cast(List[R], results)
