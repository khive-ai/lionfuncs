# Copyright (c) 2023 - 2025, HaiyangLi <quantocean.li at gmail dot com>
#
# SPDX-License-Identifier: Apache-2.0

"""
Network event classes for tracking API request lifecycles.

This module provides classes for tracking the lifecycle of API requests,
including status, timing, and result information.
"""

import datetime
import traceback
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional


class RequestStatus(str, Enum):
    """Possible states of a network request."""

    PENDING = (
        "PENDING"  # Initial state before queueing (event created, not yet submitted)
    )
    QUEUED = "QUEUED"  # Task is in the WorkQueue
    PROCESSING = "PROCESSING"  # Task picked by worker, waiting for limits/capacity
    CALLING = "CALLING"  # API call is in flight
    COMPLETED = "COMPLETED"  # API call finished successfully
    FAILED = "FAILED"  # API call failed
    CANCELLED = "CANCELLED"  # Task was cancelled


@dataclass
class NetworkRequestEvent:
    """
    Event class for tracking the lifecycle of a network request.

    This class maintains the state, timing, and result information for
    an API request as it progresses through the execution pipeline.
    """

    request_id: str  # e.g., uuid, should be set by Executor on creation
    created_at: datetime.datetime = field(default_factory=datetime.datetime.utcnow)
    updated_at: datetime.datetime = field(default_factory=datetime.datetime.utcnow)
    status: RequestStatus = RequestStatus.PENDING

    # Request details
    endpoint_url: Optional[str] = None
    method: Optional[str] = None
    headers: Optional[dict[str, Any]] = None
    payload: Optional[Any] = None  # Or request_body

    # Execution details
    num_api_tokens_needed: int = 0  # For API token rate limiter

    # Response details
    response_status_code: Optional[int] = None
    response_headers: Optional[dict[str, Any]] = None
    response_body: Optional[Any] = None

    # Error details
    error_type: Optional[str] = None
    error_message: Optional[str] = None
    error_details: Optional[str] = None  # Store traceback string

    # Timing
    queued_at: Optional[datetime.datetime] = None
    processing_started_at: Optional[datetime.datetime] = None
    call_started_at: Optional[datetime.datetime] = None
    completed_at: Optional[datetime.datetime] = None  # or failed_at / cancelled_at

    # Logs/Metadata
    logs: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def _update_timestamp(self) -> None:
        """Update the updated_at timestamp to the current time."""
        self.updated_at = datetime.datetime.utcnow()

    def update_status(self, new_status: RequestStatus) -> None:
        """
        Update the status of the request and record the timestamp.

        Args:
            new_status: The new status to set.
        """
        old_status = self.status
        self.status = new_status
        now = datetime.datetime.utcnow()

        if old_status != new_status:  # Log status change
            self.add_log(
                f"Status changed from {old_status.value} to {new_status.value}"
            )

        if new_status == RequestStatus.QUEUED and not self.queued_at:
            self.queued_at = now
        elif new_status == RequestStatus.PROCESSING and not self.processing_started_at:
            self.processing_started_at = now
        elif new_status == RequestStatus.CALLING and not self.call_started_at:
            self.call_started_at = now
        elif (
            new_status
            in [RequestStatus.COMPLETED, RequestStatus.FAILED, RequestStatus.CANCELLED]
            and not self.completed_at
        ):
            self.completed_at = now

        self._update_timestamp()

    def set_result(
        self, status_code: int, headers: Optional[dict], body: Optional[Any]
    ) -> None:
        """
        Set the result of the request and update status to COMPLETED.

        Args:
            status_code: HTTP status code of the response.
            headers: Response headers.
            body: Response body.
        """
        self.response_status_code = status_code
        self.response_headers = headers
        self.response_body = body
        self.add_log(f"Call completed with status code: {status_code}")
        self.update_status(RequestStatus.COMPLETED)

    def set_error(self, exception: Exception) -> None:
        """
        Set error information for the request and update status to FAILED.

        Args:
            exception: The exception that occurred.
        """
        self.error_type = type(exception).__name__
        self.error_message = str(exception)
        self.error_details = traceback.format_exc()
        self.add_log(f"Call failed: {self.error_type} - {self.error_message}")
        self.update_status(RequestStatus.FAILED)

    def add_log(self, message: str) -> None:
        """
        Add a log message to the request's log.

        Args:
            message: The message to add.
        """
        self.logs.append(f"{datetime.datetime.utcnow().isoformat()} - {message}")
        self._update_timestamp()
