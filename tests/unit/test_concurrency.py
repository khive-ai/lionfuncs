import asyncio
import logging
from unittest.mock import MagicMock

import anyio  # <-- Add import
import pytest

from lionfuncs.concurrency import (
    BoundedQueue,
    CapacityLimiter,
    Condition,
    Event,
    Lock,
    QueueConfig,
    QueueStatus,
    Semaphore,
    WorkQueue,
)
from lionfuncs.errors import QueueStateError

# Configure logging for tests
logger = logging.getLogger(__name__)
# logging.basicConfig(level=logging.DEBUG) # Uncomment for verbose test logging


@pytest.fixture
def mock_logger():
    return MagicMock(spec=logging.Logger)


@pytest.fixture
# @pytest.mark.asyncio # <-- Remove marker
async def bq(mock_logger: MagicMock):
    queue = BoundedQueue[int](maxsize=3, logger=mock_logger)
    await queue.start()
    yield queue
    if queue.status != QueueStatus.STOPPED:
        await queue.stop()


@pytest.fixture
# @pytest.mark.asyncio # <-- Remove marker
async def wq(mock_logger: MagicMock):
    work_queue = WorkQueue[int](maxsize=3, concurrency_limit=2, logger=mock_logger)
    async with work_queue as wq_instance:
        yield wq_instance


class TestBoundedQueue:
    @pytest.mark.asyncio  # <-- Add marker
    async def test_initialization(self, mock_logger: MagicMock):
        queue = BoundedQueue[int](maxsize=5, timeout=0.05, logger=mock_logger)
        assert queue.maxsize == 5
        assert queue.timeout == 0.05
        assert queue.status == QueueStatus.IDLE
        assert queue.size == 0
        assert not queue.is_full
        assert queue.is_empty
        mock_logger.debug.assert_called_with(
            "Initialized BoundedQueue with maxsize=5, timeout=0.05"
        )

        with pytest.raises(ValueError):
            BoundedQueue[int](maxsize=0)

    @pytest.mark.asyncio  # <-- Add marker
    async def test_start_stop(self, bq: BoundedQueue[int], mock_logger: MagicMock):
        assert bq.status == QueueStatus.PROCESSING
        mock_logger.info.assert_any_call("Queue started with maxsize 3")

        await bq.stop()
        assert bq.status == QueueStatus.STOPPED
        mock_logger.info.assert_any_call("Stopping queue and workers...")
        mock_logger.info.assert_any_call("Queue stopped")

        # Test idempotency of stop
        await bq.stop()
        assert bq.status == QueueStatus.STOPPED

        # Test idempotency of start (if already processing or stopping)
        bq._status = QueueStatus.PROCESSING  # manually set for test
        await bq.start()  # should return
        bq._status = QueueStatus.STOPPING  # manually set for test
        await bq.start()  # should return

    @pytest.mark.asyncio  # <-- Add marker
    async def test_put_get_task_done_join(self, bq: BoundedQueue[int]):
        assert await bq.put(1) is True
        assert bq.size == 1
        assert bq.metrics["enqueued"] == 1

        assert await bq.put(2) is True
        assert bq.size == 2

        item1 = await bq.get()
        assert item1 == 1
        assert bq.size == 1
        bq.task_done()
        assert bq.metrics["processed"] == 1

        item2 = await bq.get()
        assert item2 == 2
        bq.task_done()

        await bq.join()  # Should complete as tasks are done

    @pytest.mark.asyncio  # <-- Add marker
    async def test_put_full_queue_backpressure(self, bq: BoundedQueue[int]):
        await bq.put(1)
        await bq.put(2)
        await bq.put(3)
        assert bq.is_full

        # This should apply backpressure and return False due to timeout
        assert await bq.put(4, timeout=0.01) is False
        assert bq.metrics["backpressure_events"] == 1
        assert bq.size == 3  # Item 4 not added

        # Test put when queue is not processing
        await bq.stop()
        with pytest.raises(QueueStateError):
            await bq.put(5)

    @pytest.mark.asyncio  # <-- Add marker
    async def test_get_empty_queue(self, bq: BoundedQueue[int]):
        # Test get when queue is not processing
        current_status = bq.status
        bq._status = QueueStatus.IDLE  # Manually set for test
        with pytest.raises(QueueStateError):
            await bq.get()
        bq._status = current_status  # Reset status

        # Test get from empty queue (will hang if not handled by worker loop timeout)
        # This is typically handled by worker logic, direct get() will wait.
        # For this test, we'll ensure it doesn't raise QueueStateError if processing
        assert bq.status == QueueStatus.PROCESSING
        # We won't await bq.get() here as it would block indefinitely

    @pytest.mark.asyncio  # <-- Add marker
    async def test_worker_management(
        self, bq: BoundedQueue[int], mock_logger: MagicMock
    ):
        processed_items = []

        async def worker_func(item: int):
            await asyncio.sleep(0.01)  # Simulate work
            processed_items.append(item)

        with pytest.raises(ValueError):
            await bq.start_workers(worker_func, num_workers=0)

        await bq.start_workers(worker_func, num_workers=2)
        assert bq.worker_count == 2
        mock_logger.info.assert_any_call("Started 2 worker tasks")

        await bq.put(10)
        await bq.put(20)
        await bq.put(30)  # This one might wait if workers are busy

        await bq.join()  # Wait for all items to be processed
        assert sorted(processed_items) == [10, 20, 30]
        assert bq.metrics["processed"] == 3

        # Test starting new workers (should stop old ones)
        processed_items_new = []

        async def new_worker_func(item: int):
            processed_items_new.append(item * 2)

        await bq.start_workers(new_worker_func, num_workers=1)
        mock_logger.warning.assert_any_call(
            "Stopping existing workers before starting new ones"
        )
        assert bq.worker_count == 1

        await bq.put(5)
        await bq.join()
        assert processed_items_new == [10]

    @pytest.mark.asyncio  # <-- Add marker
    async def test_worker_error_handling(
        self, bq: BoundedQueue[int], mock_logger: MagicMock
    ):
        error_handled_event = asyncio.Event()
        problematic_item = -1

        async def failing_worker(item: int):
            if item == problematic_item:
                raise ValueError("Test worker error")
            await asyncio.sleep(0.01)

        async def custom_error_handler(exc: Exception, item: int):
            assert isinstance(exc, ValueError)
            assert item == problematic_item
            mock_logger.error(f"Custom handler caught: {exc} for item {item}")
            error_handled_event.set()

        await bq.start_workers(
            failing_worker, num_workers=1, error_handler=custom_error_handler
        )
        await bq.put(1)
        await bq.put(problematic_item)
        await bq.put(2)

        await bq.join()
        assert bq.metrics["errors"] == 1
        assert error_handled_event.is_set()
        mock_logger.error.assert_any_call(
            f"Custom handler caught: Test worker error for item {problematic_item}"
        )

        # Test default error logging if no handler
        bq._metrics["errors"] = 0  # Reset for next test by accessing internal attribute
        await bq.start_workers(failing_worker, num_workers=1, error_handler=None)
        await bq.put(problematic_item)
        await bq.join()
        assert bq.metrics["errors"] == 1
        mock_logger.exception.assert_any_call("Error processing item")

    @pytest.mark.asyncio  # <-- Add marker
    async def test_worker_loop_cancellation(self, bq: BoundedQueue[int]):
        async def long_worker(item: int):
            try:
                await asyncio.sleep(5)  # Long running task
            except asyncio.CancelledError:
                logger.info(f"Worker for item {item} cancelled as expected.")
                raise

        await bq.start_workers(long_worker, num_workers=1)
        await bq.put(100)
        await asyncio.sleep(0.05)  # Give worker time to start

        assert bq.worker_count == 1
        await bq.stop(timeout=0.1)  # Stop should cancel the worker
        assert bq.worker_count == 0
        # Check logs for cancellation message if logger was real and configured

    @pytest.mark.asyncio  # <-- Add marker
    async def test_context_manager(self, mock_logger: MagicMock):
        async with BoundedQueue[str](maxsize=2, logger=mock_logger) as q_ctx:
            assert q_ctx.status == QueueStatus.PROCESSING
            await q_ctx.put("hello")
        assert q_ctx.status == QueueStatus.STOPPED
        mock_logger.info.assert_any_call("Queue started with maxsize 2")
        mock_logger.info.assert_any_call("Stopping queue and workers...")
        mock_logger.info.assert_any_call("Queue stopped")


class TestWorkQueue:
    @pytest.mark.asyncio  # <-- Add marker
    async def test_initialization(self, mock_logger: MagicMock):
        wq_instance = WorkQueue[int](
            maxsize=10, timeout=0.2, concurrency_limit=5, logger=mock_logger
        )
        assert wq_instance.queue.maxsize == 10
        assert wq_instance.queue.timeout == 0.2
        assert wq_instance.concurrency_limit == 5
        mock_logger.debug.assert_any_call(
            "Initialized WorkQueue with maxsize=10, timeout=0.2, concurrency_limit=5"
        )

    @pytest.mark.asyncio  # <-- Add marker
    async def test_properties_delegation(self, wq: WorkQueue[int]):
        assert wq.is_full == wq.queue.is_full
        assert wq.is_empty == wq.queue.is_empty
        assert wq.metrics == wq.queue.metrics
        assert wq.size == wq.queue.size

    @pytest.mark.asyncio  # <-- Add marker
    async def test_start_stop_put_join_delegation(self, wq: WorkQueue[int]):
        # Start is called by fixture's __aenter__
        assert wq.queue.status == QueueStatus.PROCESSING

        assert await wq.put(100) is True
        assert wq.size == 1

        # Mock worker function for process
        processed_items_wq = []

        async def wq_worker(item: int):
            await asyncio.sleep(0.01)
            processed_items_wq.append(item)

        await wq.process(wq_worker, num_workers=1)  # Starts workers in underlying BQ
        await wq.join()  # Waits for item 100 to be processed
        assert processed_items_wq == [100]

        # Stop is called by fixture's __aexit__
        # We can test it explicitly if needed by creating a WQ outside fixture

    @pytest.mark.asyncio  # <-- Add marker
    async def test_batch_process(self, mock_logger: MagicMock):
        # Create a new WQ for this test to control its lifecycle fully
        wq_batch = WorkQueue[int](maxsize=5, concurrency_limit=2, logger=mock_logger)
        items_to_process = [1, 2, 3, 4, 5]
        processed_batch_items = []
        worker_calls = 0

        async def batch_worker(item: int):
            nonlocal worker_calls
            await asyncio.sleep(0.01)  # Simulate work
            processed_batch_items.append(item * 10)
            worker_calls += 1

        error_event = asyncio.Event()

        async def batch_error_handler(exc, item):
            logger.error(f"Batch error handler: {exc} for {item}")
            error_event.set()

        await wq_batch.batch_process(
            items_to_process,
            batch_worker,
            num_workers=2,
            error_handler=batch_error_handler,
        )

        assert sorted(processed_batch_items) == [10, 20, 30, 40, 50]
        assert worker_calls == 5
        assert (
            wq_batch.queue.status == QueueStatus.STOPPED
        )  # batch_process stops the queue
        assert not error_event.is_set()  # No errors expected

        # Test batch_process with errors
        processed_batch_items.clear()
        worker_calls = 0
        items_with_error = [1, -1, 3]  # -1 will cause error

        async def batch_worker_with_error(item: int):
            nonlocal worker_calls
            if item == -1:
                raise ValueError("Batch item error")
            await asyncio.sleep(0.01)
            processed_batch_items.append(item * 10)
            worker_calls += 1

        await wq_batch.batch_process(
            items_with_error,
            batch_worker_with_error,
            num_workers=1,
            error_handler=batch_error_handler,
        )
        assert sorted(processed_batch_items) == [10, 30]  # Item -1 skipped due to error
        assert worker_calls == 2
        assert error_event.is_set()  # Error handler should have been called
        assert wq_batch.queue.metrics["errors"] == 1


def test_queue_config_validation():
    # Valid
    config = QueueConfig(
        queue_capacity=10, capacity_refresh_time=0.5, concurrency_limit=5
    )
    assert config.queue_capacity == 10

    with pytest.raises(ValueError, match="Queue capacity must be at least 1"):
        QueueConfig(queue_capacity=0)
    with pytest.raises(ValueError, match="Capacity refresh time must be positive"):
        QueueConfig(capacity_refresh_time=0)
    with pytest.raises(ValueError, match="Concurrency limit must be at least 1"):
        QueueConfig(concurrency_limit=0)

    # Test defaults
    config_default = QueueConfig()
    assert config_default.queue_capacity == 100
    assert config_default.concurrency_limit is None


# Minimal tests for anyio wrappers to ensure they are importable and construct
# Detailed testing of anyio itself is out of scope.
def test_anyio_wrappers_instantiation():
    lock = Lock()
    assert isinstance(lock._lock, anyio.Lock)

    sema = Semaphore(initial_value=5)
    assert isinstance(sema._semaphore, anyio.Semaphore)
    assert sema._semaphore.value == 5  # anyio.Semaphore has 'value'

    cap_limiter = CapacityLimiter(total_tokens=10)
    assert isinstance(cap_limiter._limiter, anyio.CapacityLimiter)
    assert cap_limiter.total_tokens == 10

    event = Event()
    assert isinstance(event._event, anyio.Event)

    # Condition requires an anyio.Lock for its internal _condition
    # Our Lock wrapper wraps an anyio.Lock, so we pass its internal _lock
    cond_lock = Lock()
    condition = WorkQueue[int]().queue._lock  # BoundedQueue uses asyncio.Lock
    # The Condition class in concurrency.py expects our Lock wrapper or None
    # If None, it creates its own Lock wrapper.
    # cond = Condition(lock=cond_lock)
    # assert isinstance(cond._condition, anyio.Condition)
    # assert cond._lock == cond_lock

    cond_no_lock = Condition()
    assert isinstance(cond_no_lock._lock, Lock)  # It should create its own Lock wrapper
    assert isinstance(cond_no_lock._condition, anyio.Condition)


@pytest.mark.asyncio
async def test_lock_context_manager():
    lock = Lock()
    shared_resource = 0

    async def task():
        nonlocal shared_resource
        async with lock:
            current_val = shared_resource
            await asyncio.sleep(0.01)  # Simulate work
            shared_resource = current_val + 1

    tasks = [asyncio.create_task(task()) for _ in range(5)]
    await asyncio.gather(*tasks)
    assert shared_resource == 5


@pytest.mark.asyncio
async def test_semaphore_context_manager():
    sema = Semaphore(2)  # Allow 2 concurrent tasks
    counter = 0
    active_tasks = 0
    max_active_tasks = 0

    async def task():
        nonlocal counter, active_tasks, max_active_tasks
        async with sema:
            active_tasks += 1
            max_active_tasks = max(max_active_tasks, active_tasks)
            await asyncio.sleep(0.05)  # Simulate work
            counter += 1
            active_tasks -= 1
        return True

    tasks = [asyncio.create_task(task()) for _ in range(5)]
    results = await asyncio.gather(*tasks)
    assert counter == 5
    assert all(results)
    assert max_active_tasks == 2


@pytest.mark.asyncio
async def test_event_wait_set():
    event = Event()
    waiter_done = False

    async def waiter():
        nonlocal waiter_done
        await event.wait()
        waiter_done = True

    async def setter():
        await asyncio.sleep(0.01)
        event.set()

    assert not event.is_set()
    await asyncio.gather(waiter(), setter())
    assert event.is_set()
    assert waiter_done
