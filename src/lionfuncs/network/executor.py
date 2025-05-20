# Copyright (c) 2023 - 2025, HaiyangLi <quantocean.li at gmail dot com>
#
# SPDX-License-Identifier: Apache-2.0

"""
Network executor for managing and rate-limiting API calls.

This module provides the Executor class, which manages a queue of API call tasks,
enforces concurrency and rate limits, and tracks request lifecycles.
"""

import asyncio
import logging
import uuid
from collections.abc import Coroutine
from typing import Any, Callable, Optional

from lionfuncs.concurrency import CapacityLimiter, WorkQueue
from lionfuncs.network.events import NetworkRequestEvent, RequestStatus
from lionfuncs.network.primitives import TokenBucketRateLimiter

logger = logging.getLogger(__name__)


class Executor:
    """
    Executor for managing and rate-limiting API calls.

    The Executor manages a queue of API call tasks, enforces concurrency and
    rate limits, and tracks request lifecycles using NetworkRequestEvent objects.
    """

    def __init__(
        self,
        queue_capacity: int = 1000,
        concurrency_limit: int = 10,
        requests_rate: float = 10.0,  # e.g., 10 requests
        requests_period: float = 1.0,  # e.g., per 1 second
        requests_bucket_capacity: Optional[float] = None,  # Defaults to rate if None
        api_tokens_rate: Optional[float] = None,  # e.g., 10000 tokens
        api_tokens_period: float = 60.0,  # e.g., per 60 seconds
        api_tokens_bucket_capacity: Optional[float] = None,  # Defaults to rate if None
        num_workers: int = 5,  # Number of workers for the WorkQueue
    ):
        """
        Initialize the Executor.

        Args:
            queue_capacity: Max capacity of the internal task queue.
            concurrency_limit: Max number of concurrent API calls.
            requests_rate: Max requests for the requests_rate_limiter.
            requests_period: Period in seconds for requests_rate.
            requests_bucket_capacity: Max capacity of the request token bucket.
                                      Defaults to requests_rate if None.
            api_tokens_rate: Max API tokens for the api_tokens_rate_limiter.
                             If None, this limiter is disabled.
            api_tokens_period: Period in seconds for api_tokens_rate.
            api_tokens_bucket_capacity: Max capacity of the API token bucket.
                                        Defaults to api_tokens_rate if None.
            num_workers: Number of worker coroutines to process the queue.
        """
        self.work_queue = WorkQueue(maxsize=queue_capacity)
        self._num_workers = num_workers
        self.capacity_limiter = CapacityLimiter(total_tokens=concurrency_limit)

        self.requests_rate_limiter = TokenBucketRateLimiter(
            rate=requests_rate,
            period=requests_period,
            max_tokens=requests_bucket_capacity,
        )

        self.api_tokens_rate_limiter: Optional[TokenBucketRateLimiter] = None
        if api_tokens_rate is not None:
            self.api_tokens_rate_limiter = TokenBucketRateLimiter(
                rate=api_tokens_rate,
                period=api_tokens_period,
                max_tokens=api_tokens_bucket_capacity,
            )

        self._is_running = False
        logger.debug(
            f"Initialized Executor with queue_capacity={queue_capacity}, "
            f"concurrency_limit={concurrency_limit}, requests_rate={requests_rate}, "
            f"requests_period={requests_period}, api_tokens_rate={api_tokens_rate}, "
            f"api_tokens_period={api_tokens_period}, num_workers={num_workers}"
        )

    async def _worker(self, task_data: dict[str, Any]) -> None:
        """
        Internal worker coroutine that processes a single task from the queue.

        Args:
            task_data: Dictionary containing the API coroutine and event.
        """
        api_coro: Callable[[], Coroutine[Any, Any, Any]] = task_data["api_coro"]
        event: NetworkRequestEvent = task_data["event"]

        event.update_status(RequestStatus.PROCESSING)
        try:
            async with self.capacity_limiter:
                event.add_log("Acquired concurrency slot.")
                # Acquire request rate limit token
                wait_time_req = await self.requests_rate_limiter.acquire(tokens=1)
                if wait_time_req > 0:
                    event.add_log(
                        f"Waiting {wait_time_req:.2f}s for request rate limit."
                    )
                    await asyncio.sleep(wait_time_req)
                event.add_log("Acquired request rate limit token.")

                # Acquire API token rate limit tokens (if applicable)
                num_api_tokens_needed = event.num_api_tokens_needed
                if self.api_tokens_rate_limiter and num_api_tokens_needed > 0:
                    wait_time_api_tokens = await self.api_tokens_rate_limiter.acquire(
                        tokens=num_api_tokens_needed
                    )
                    if wait_time_api_tokens > 0:
                        event.add_log(
                            f"Waiting {wait_time_api_tokens:.2f}s for API token rate limit ({num_api_tokens_needed} tokens)."
                        )
                        await asyncio.sleep(wait_time_api_tokens)
                    event.add_log(
                        f"Acquired API token rate limit ({num_api_tokens_needed} tokens)."
                    )

                event.update_status(RequestStatus.CALLING)

                # api_coro() can return either just the body or a tuple of (status_code, headers, body)
                response = await api_coro()

                # Check if response is a tuple with at least 3 elements
                if isinstance(response, tuple) and len(response) >= 3:
                    status_code, headers, body = response
                else:
                    # If not a tuple, assume it's just the body with default status and headers
                    status_code = 200
                    headers = {"Content-Type": "application/json"}
                    body = response

                # Set the result with the extracted or default values
                event.set_result(
                    status_code=status_code,
                    headers=headers.copy()
                    if headers is not None
                    else None,  # Pass a copy
                    body=body,
                )
                # Status is set to COMPLETED by set_result
        except Exception as e:
            event.set_error(e)
            # Status is set to FAILED by set_error
            logger.exception(f"Error processing API call: {e}")

    async def submit_task(
        self,
        api_call_coroutine: Callable[
            [], Coroutine[Any, Any, Any]
        ],  # Should return (status_code, headers, body)
        endpoint_url: Optional[str] = None,
        method: Optional[str] = None,
        headers: Optional[dict[str, Any]] = None,
        payload: Optional[Any] = None,
        num_api_tokens_needed: int = 0,
        metadata: Optional[dict[str, Any]] = None,
    ) -> NetworkRequestEvent:
        """
        Submit a new API call task to the executor.

        Args:
            api_call_coroutine: A callable that returns a coroutine.
                                The coroutine should perform the API call and return a tuple
                                (status_code: int, headers: Dict, body: Any) or raise an exception.
            endpoint_url: URL of the API endpoint.
            method: HTTP method (e.g., "GET", "POST").
            headers: Request headers.
            payload: Request payload/body.
            num_api_tokens_needed: Number of API-specific tokens this call will consume.
            metadata: Optional dictionary for custom metadata on the event.

        Returns:
            A NetworkRequestEvent instance tracking this task.

        Raises:
            RuntimeError: If the executor is not running.
        """
        if not self._is_running:
            raise RuntimeError("Executor is not running. Call start() first.")

        event = NetworkRequestEvent(
            request_id=str(uuid.uuid4()),
            endpoint_url=endpoint_url,
            method=method,
            headers=headers,
            payload=payload,
            num_api_tokens_needed=num_api_tokens_needed,
            metadata=metadata or {},
        )
        event.update_status(RequestStatus.QUEUED)

        task_data = {
            "api_coro": api_call_coroutine,
            "event": event,
        }
        await self.work_queue.put(task_data)
        return event

    async def start(self) -> None:
        """
        Start the executor and its internal worker queue.

        Raises:
            RuntimeError: If the executor is already running.
        """
        if self._is_running:
            return

        self._is_running = True
        await self.work_queue.start()
        await self.work_queue.process(
            worker_func=self._worker, num_workers=self._num_workers
        )
        logger.info("Executor started")

    async def stop(self, graceful: bool = True) -> None:
        """
        Stop the executor.

        Args:
            graceful: If True, waits for the queue to empty and workers to finish.
                     If False, attempts a more immediate shutdown (cancels tasks).
        """
        if not self._is_running:
            return

        self._is_running = False
        await self.work_queue.stop(timeout=None if graceful else 0.1)
        logger.info(f"Executor stopped (graceful={graceful})")

    async def __aenter__(self) -> "Executor":
        """Enter async context manager."""
        await self.start()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Exit async context manager."""
        await self.stop()
