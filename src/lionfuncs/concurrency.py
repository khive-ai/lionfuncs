# Copyright (c) 2023 - 2025, HaiyangLi <quantocean.li at gmail dot com>
#
# SPDX-License-Identifier: Apache-2.0

"""
Concurrency utilities for lionfuncs, including Bounded Queues and AnyIO wrappers.
"""

import asyncio
import logging
from collections.abc import Awaitable
from enum import Enum
from types import TracebackType
from typing import Any, Callable, Generic, Optional, TypeVar

import anyio
from pydantic import BaseModel, field_validator

from lionfuncs.errors import QueueStateError

T = TypeVar("T")
logger = logging.getLogger(__name__)

__all__ = [
    "BoundedQueue",
    "WorkQueue",
    "QueueStatus",
    "QueueConfig",
    "Lock",
    "Semaphore",
    "CapacityLimiter",
    "Event",
    "Condition",
]


class QueueStatus(str, Enum):
    """Possible states of the queue."""

    IDLE = "idle"
    PROCESSING = "processing"
    STOPPING = "stopping"
    STOPPED = "stopped"


class QueueConfig(BaseModel):
    """Configuration options for work queues."""

    queue_capacity: int = 100
    capacity_refresh_time: float = 1.0
    concurrency_limit: int | None = None

    @field_validator("queue_capacity")
    def validate_queue_capacity(cls, v):
        """Validate that queue capacity is at least 1."""
        if v < 1:
            raise ValueError("Queue capacity must be at least 1")
        return v

    @field_validator("capacity_refresh_time")
    def validate_capacity_refresh_time(cls, v):
        """Validate that capacity refresh time is positive."""
        if v <= 0:
            raise ValueError("Capacity refresh time must be positive")
        return v

    @field_validator("concurrency_limit")
    def validate_concurrency_limit(cls, v):
        """Validate that concurrency limit is at least 1 if provided."""
        if v is not None and v < 1:
            raise ValueError("Concurrency limit must be at least 1")
        return v


class BoundedQueue(Generic[T]):
    """
    Bounded async queue with backpressure support.

    This implementation wraps asyncio.Queue with additional functionality
    for worker management, backpressure, and lifecycle control.
    """

    def __init__(
        self,
        maxsize: int = 100,
        timeout: float = 0.1,
        logger: logging.Logger | None = None,
    ):
        """
        Initialize the bounded queue.

        Args:
            maxsize: Maximum queue size (must be > 0)
            timeout: Timeout for queue operations in seconds
            logger: Optional logger
        """
        if maxsize < 1:
            raise ValueError("Queue maxsize must be at least 1")

        self.maxsize = maxsize
        self.timeout = timeout
        self.logger = logger or logging.getLogger(__name__)
        self.queue = asyncio.Queue(maxsize=maxsize)
        self._status = QueueStatus.IDLE
        self._workers: list[asyncio.Task] = []
        self._stop_event = asyncio.Event()
        self._lock = (
            asyncio.Lock()
        )  # Using asyncio.Lock as anyio.Lock wrapper is defined below
        self._metrics: dict[str, int] = {
            "enqueued": 0,
            "processed": 0,
            "errors": 0,
            "backpressure_events": 0,
        }

        self.logger.debug(
            f"Initialized BoundedQueue with maxsize={maxsize}, timeout={timeout}"
        )

    @property
    def status(self) -> QueueStatus:
        """Get the current queue status."""
        return self._status

    @property
    def metrics(self) -> dict[str, int]:
        """Get queue metrics."""
        return self._metrics.copy()

    @property
    def size(self) -> int:
        """Get the current queue size."""
        return self.queue.qsize()

    @property
    def is_full(self) -> bool:
        """Check if the queue is full."""
        return self.queue.full()

    @property
    def is_empty(self) -> bool:
        """Check if the queue is empty."""
        return self.queue.empty()

    @property
    def worker_count(self) -> int:
        """Get the current number of active workers."""
        return len([w for w in self._workers if not w.done()])

    async def put(self, item: T, timeout: float | None = None) -> bool:
        """
        Add an item to the queue with backpressure.

        Args:
            item: The item to enqueue
            timeout: Operation timeout (overrides default)

        Returns:
            True if the item was enqueued, False if backpressure was applied

        Raises:
            QueueStateError: If the queue is not in PROCESSING state
        """
        if self._status != QueueStatus.PROCESSING:
            raise QueueStateError(
                f"Cannot put items when queue is {self._status.value}",
                current_state=self._status.value,
            )

        try:
            await asyncio.wait_for(
                self.queue.put(item), timeout=timeout or self.timeout
            )
            self._metrics["enqueued"] += 1
            self.logger.debug(f"Item enqueued. Queue size: {self.size}/{self.maxsize}")
            return True
        except asyncio.TimeoutError:
            self._metrics["backpressure_events"] += 1
            self.logger.warning(
                f"Backpressure applied - queue full ({self.size}/{self.maxsize})"
            )
            return False

    async def get(self) -> T:
        """
        Get an item from the queue.

        Returns:
            The next item from the queue

        Raises:
            QueueStateError: If the queue is not in PROCESSING state
        """
        if self._status != QueueStatus.PROCESSING:
            raise QueueStateError(
                f"Cannot get items when queue is {self._status.value}",
                current_state=self._status.value,
            )
        return await self.queue.get()

    def task_done(self) -> None:
        """Mark a task as done."""
        self.queue.task_done()
        self._metrics["processed"] += 1

    async def join(self) -> None:
        """Wait for all queue items to be processed."""
        await self.queue.join()

    async def start(self) -> None:
        """Start the queue for processing."""
        async with self._lock:
            if self._status in (QueueStatus.PROCESSING, QueueStatus.STOPPING):
                return

            self._stop_event.clear()
            self._status = QueueStatus.PROCESSING
            self.logger.info(f"Queue started with maxsize {self.maxsize}")

    async def stop(self, timeout: float | None = None) -> None:
        """
        Stop the queue and all worker tasks.

        Args:
            timeout: Maximum time to wait for pending tasks
        """
        async with self._lock:
            if self._status == QueueStatus.STOPPED:
                return

            self._status = QueueStatus.STOPPING
            self.logger.info("Stopping queue and workers...")
            self._stop_event.set()

            if self._workers:
                if timeout is not None:
                    try:
                        done, pending = await asyncio.wait(
                            self._workers, timeout=timeout
                        )
                        for task in pending:
                            task.cancel()
                    except Exception:
                        self.logger.exception("Error waiting for workers")
                else:
                    try:
                        await asyncio.gather(*self._workers, return_exceptions=True)
                    except Exception:
                        self.logger.exception("Error waiting for workers")

            self._workers.clear()
            self._status = QueueStatus.STOPPED
            self.logger.info("Queue stopped")

    async def start_workers(
        self,
        worker_func: Callable[[T], Awaitable[Any]],
        num_workers: int,
        error_handler: Callable[[Exception, T], Awaitable[None]] | None = None,
    ) -> None:
        """
        Start worker tasks to process queue items.

        Args:
            worker_func: Async function that processes each queue item
            num_workers: Number of worker tasks to start
            error_handler: Optional async function to handle worker errors

        Raises:
            ValueError: If num_workers is less than 1
        """
        if num_workers < 1:
            raise ValueError("Number of workers must be at least 1")

        if self._status != QueueStatus.PROCESSING:
            await self.start()

        async with self._lock:
            if self._workers:
                self.logger.warning(
                    "Stopping existing workers before starting new ones"
                )
                for task in self._workers:
                    if not task.done():
                        task.cancel()
                self._workers.clear()

            for i in range(num_workers):
                task = asyncio.create_task(
                    self._worker_loop(i, worker_func, error_handler)
                )
                self._workers.append(task)
            self.logger.info(f"Started {num_workers} worker tasks")

    async def _worker_loop(
        self,
        worker_id: int,
        worker_func: Callable[[T], Awaitable[Any]],
        error_handler: Callable[[Exception, T], Awaitable[None]] | None = None,
    ) -> None:
        """Worker loop that processes queue items."""
        self.logger.debug(f"Worker {worker_id} started")
        while not self._stop_event.is_set():
            try:
                try:
                    item = await asyncio.wait_for(self.get(), timeout=0.1)
                except asyncio.TimeoutError:
                    continue

                try:
                    await worker_func(item)
                except Exception as e:
                    self._metrics["errors"] += 1
                    if error_handler:
                        try:
                            await error_handler(e, item)
                        except Exception:
                            self.logger.exception(
                                f"Error in error handler. Original error: {e}"
                            )
                    else:
                        self.logger.exception("Error processing item")
                finally:
                    self.task_done()
            except asyncio.CancelledError:
                self.logger.debug(f"Worker {worker_id} cancelled")
                break
        self.logger.debug(f"Worker {worker_id} stopped")

    async def __aenter__(self) -> "BoundedQueue[T]":
        """Enter async context."""
        await self.start()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Exit async context."""
        await self.stop()


class WorkQueue(Generic[T]):
    """High-level wrapper around BoundedQueue with additional functionality."""

    def __init__(
        self,
        maxsize: int = 100,
        timeout: float = 0.1,
        concurrency_limit: int | None = None,
        logger: logging.Logger | None = None,
    ):
        self.queue = BoundedQueue(maxsize=maxsize, timeout=timeout, logger=logger)
        self.concurrency_limit = concurrency_limit
        self.logger = logger or logging.getLogger(__name__)
        self.logger.debug(
            f"Initialized WorkQueue with maxsize={maxsize}, "
            f"timeout={timeout}, concurrency_limit={concurrency_limit}"
        )

    async def __aenter__(self) -> "WorkQueue[T]":
        await self.start()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        await self.stop()

    @property
    def is_full(self) -> bool:
        return self.queue.is_full

    @property
    def is_empty(self) -> bool:
        return self.queue.is_empty

    @property
    def metrics(self) -> dict[str, int]:
        return self.queue.metrics

    @property
    def size(self) -> int:
        return self.queue.size

    async def start(self) -> None:
        await self.queue.start()

    async def stop(self, timeout: float | None = None) -> None:
        await self.queue.stop(timeout=timeout)

    async def put(self, item: T) -> bool:
        return await self.queue.put(item)

    async def process(
        self,
        worker_func: Callable[[T], Awaitable[Any]],
        num_workers: int | None = None,
        error_handler: Callable[[Exception, T], Awaitable[None]] | None = None,
    ) -> None:
        if num_workers is None:
            num_workers = self.concurrency_limit or 1
        await self.queue.start_workers(
            worker_func=worker_func,
            num_workers=num_workers,
            error_handler=error_handler,
        )

    async def join(self) -> None:
        await self.queue.join()

    async def batch_process(
        self,
        items: list[T],
        worker_func: Callable[[T], Awaitable[Any]],
        num_workers: int | None = None,
        error_handler: Callable[[Exception, T], Awaitable[None]] | None = None,
    ) -> None:
        await self.start()
        await self.process(
            worker_func=worker_func,
            num_workers=num_workers,
            error_handler=error_handler,
        )
        for item in items:
            while True:
                if await self.put(item):
                    break
                await asyncio.sleep(0.1)  # pragma: no cover
        await self.join()
        await self.stop()


class Lock:
    """A mutex lock for controlling access to a shared resource.
    This lock is reentrant, meaning the same task can acquire it multiple times
    without deadlocking.
    Wraps anyio.Lock.
    """

    def __init__(self):
        self._lock = anyio.Lock()

    async def __aenter__(self) -> None:
        await self.acquire()

    async def __aexit__(
        self,
        exc_type: Optional[type[BaseException]],
        exc_val: Optional[BaseException],
        exc_tb: Optional[TracebackType],
    ) -> None:
        self.release()

    async def acquire(self) -> bool:
        await self._lock.acquire()
        return True

    def release(self) -> None:
        self._lock.release()


class Semaphore:
    """A semaphore for limiting concurrent access to a resource.
    Wraps anyio.Semaphore.
    """

    def __init__(self, initial_value: int):
        if initial_value < 0:
            raise ValueError("The initial value must be >= 0")  # pragma: no cover
        self._semaphore = anyio.Semaphore(initial_value)

    async def __aenter__(self) -> None:
        await self.acquire()

    async def __aexit__(
        self,
        exc_type: Optional[type[BaseException]],
        exc_val: Optional[BaseException],
        exc_tb: Optional[TracebackType],
    ) -> None:
        self.release()

    async def acquire(self) -> None:
        await self._semaphore.acquire()

    def release(self) -> None:
        self._semaphore.release()


class CapacityLimiter:
    """A context manager for limiting the number of concurrent operations.
    Wraps anyio.CapacityLimiter.
    """

    def __init__(self, total_tokens: float):
        if total_tokens < 1:
            raise ValueError(
                "The total number of tokens must be >= 1"
            )  # pragma: no cover
        self._limiter = anyio.CapacityLimiter(total_tokens)

    async def __aenter__(self) -> None:
        await self.acquire()

    async def __aexit__(
        self,
        exc_type: Optional[type[BaseException]],
        exc_val: Optional[BaseException],
        exc_tb: Optional[TracebackType],
    ) -> None:
        self.release()

    async def acquire(self) -> None:
        await self._limiter.acquire()

    def release(self) -> None:
        self._limiter.release()

    @property
    def total_tokens(self) -> float:
        return self._limiter.total_tokens  # pragma: no cover

    @total_tokens.setter
    def total_tokens(self, value: float) -> None:
        if value < 1:
            raise ValueError(
                "The total number of tokens must be >= 1"
            )  # pragma: no cover
        self._limiter.total_tokens = value  # pragma: no cover

    @property
    def borrowed_tokens(self) -> int:
        return self._limiter.borrowed_tokens  # pragma: no cover

    @property
    def available_tokens(self) -> float:
        return self._limiter.available_tokens  # pragma: no cover


class Event:
    """An event object for task synchronization.
    Wraps anyio.Event.
    """

    def __init__(self):
        self._event = anyio.Event()

    def is_set(self) -> bool:
        return self._event.is_set()

    def set(self) -> None:
        self._event.set()

    async def wait(self) -> None:
        await self._event.wait()


class Condition:
    """A condition variable for task synchronization.
    Wraps anyio.Condition.
    """

    def __init__(self, lock: Optional[Lock] = None):
        self._lock = lock or Lock()  # Use the Lock wrapper defined above
        self._condition = anyio.Condition(
            self._lock._lock
        )  # Access the underlying anyio.Lock

    async def __aenter__(self) -> "Condition":
        await self._lock.acquire()
        return self

    async def __aexit__(
        self,
        exc_type: Optional[type[BaseException]],
        exc_val: Optional[BaseException],
        exc_tb: Optional[TracebackType],
    ) -> None:
        self._lock.release()

    async def wait(self) -> None:
        await self._condition.wait()

    async def notify(self, n: int = 1) -> None:
        await self._condition.notify(n)  # pragma: no cover

    async def notify_all(self) -> None:
        await self._condition.notify_all()  # pragma: no cover
