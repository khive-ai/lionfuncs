# Copyright (c) 2023 - 2025, HaiyangLi <quantocean.li at gmail dot com>
#
# SPDX-License-Identifier: Apache-2.0

"""
Unit tests for the network events module.
"""

import datetime
import unittest
from unittest.mock import patch

from lionfuncs.network.events import NetworkRequestEvent, RequestStatus


class TestNetworkRequestEvent(unittest.TestCase):
    """Test cases for the NetworkRequestEvent class."""

    def test_init_default_values(self):
        """Test initialization with default values."""
        event = NetworkRequestEvent(request_id="test-id")
        
        self.assertEqual(event.request_id, "test-id")
        self.assertEqual(event.status, RequestStatus.PENDING)
        self.assertEqual(event.num_api_tokens_needed, 0)
        self.assertIsNone(event.endpoint_url)
        self.assertIsNone(event.method)
        self.assertIsNone(event.headers)
        self.assertIsNone(event.payload)
        self.assertIsNone(event.response_status_code)
        self.assertIsNone(event.response_headers)
        self.assertIsNone(event.response_body)
        self.assertIsNone(event.error_type)
        self.assertIsNone(event.error_message)
        self.assertIsNone(event.error_details)
        self.assertIsNone(event.queued_at)
        self.assertIsNone(event.processing_started_at)
        self.assertIsNone(event.call_started_at)
        self.assertIsNone(event.completed_at)
        self.assertEqual(event.logs, [])
        self.assertEqual(event.metadata, {})

    def test_init_custom_values(self):
        """Test initialization with custom values."""
        event = NetworkRequestEvent(
            request_id="test-id",
            endpoint_url="https://api.example.com/v1/completions",
            method="POST",
            headers={"Content-Type": "application/json"},
            payload={"prompt": "Hello"},
            num_api_tokens_needed=100,
            metadata={"model": "gpt-4"}
        )
        
        self.assertEqual(event.request_id, "test-id")
        self.assertEqual(event.endpoint_url, "https://api.example.com/v1/completions")
        self.assertEqual(event.method, "POST")
        self.assertEqual(event.headers, {"Content-Type": "application/json"})
        self.assertEqual(event.payload, {"prompt": "Hello"})
        self.assertEqual(event.num_api_tokens_needed, 100)
        self.assertEqual(event.metadata, {"model": "gpt-4"})

    def test_update_status(self):
        """Test status updates and timestamp tracking."""
        event = NetworkRequestEvent(request_id="test-id")
        
        # Initial state
        self.assertEqual(event.status, RequestStatus.PENDING)
        self.assertIsNone(event.queued_at)
        
        # Update to QUEUED
        with patch("datetime.datetime") as mock_datetime:
            mock_now = datetime.datetime(2025, 5, 20, 12, 0, 0)
            mock_datetime.utcnow.return_value = mock_now
            
            event.update_status(RequestStatus.QUEUED)
            
            self.assertEqual(event.status, RequestStatus.QUEUED)
            self.assertEqual(event.queued_at, mock_now)
            self.assertIsNone(event.processing_started_at)
            self.assertEqual(len(event.logs), 1)
            self.assertIn("Status changed from PENDING to QUEUED", event.logs[0])
        
        # Update to PROCESSING
        with patch("datetime.datetime") as mock_datetime:
            mock_now = datetime.datetime(2025, 5, 20, 12, 0, 1)
            mock_datetime.utcnow.return_value = mock_now
            
            event.update_status(RequestStatus.PROCESSING)
            
            self.assertEqual(event.status, RequestStatus.PROCESSING)
            self.assertEqual(event.processing_started_at, mock_now)
            self.assertIsNone(event.call_started_at)
            self.assertEqual(len(event.logs), 2)
            self.assertIn("Status changed from QUEUED to PROCESSING", event.logs[1])
        
        # Update to CALLING
        with patch("datetime.datetime") as mock_datetime:
            mock_now = datetime.datetime(2025, 5, 20, 12, 0, 2)
            mock_datetime.utcnow.return_value = mock_now
            
            event.update_status(RequestStatus.CALLING)
            
            self.assertEqual(event.status, RequestStatus.CALLING)
            self.assertEqual(event.call_started_at, mock_now)
            self.assertIsNone(event.completed_at)
            self.assertEqual(len(event.logs), 3)
            self.assertIn("Status changed from PROCESSING to CALLING", event.logs[2])
        
        # Update to COMPLETED
        with patch("datetime.datetime") as mock_datetime:
            mock_now = datetime.datetime(2025, 5, 20, 12, 0, 3)
            mock_datetime.utcnow.return_value = mock_now
            
            event.update_status(RequestStatus.COMPLETED)
            
            self.assertEqual(event.status, RequestStatus.COMPLETED)
            self.assertEqual(event.completed_at, mock_now)
            self.assertEqual(len(event.logs), 4)
            self.assertIn("Status changed from CALLING to COMPLETED", event.logs[3])

    def test_set_result(self):
        """Test setting result and status transition to COMPLETED."""
        event = NetworkRequestEvent(request_id="test-id")
        
        with patch("datetime.datetime") as mock_datetime:
            mock_now = datetime.datetime(2025, 5, 20, 12, 0, 0)
            mock_datetime.utcnow.return_value = mock_now
            mock_datetime.isoformat = datetime.datetime.isoformat
            
            event.set_result(
                status_code=200,
                headers={"Content-Type": "application/json"},
                body={"result": "Success"}
            )
            
            self.assertEqual(event.status, RequestStatus.COMPLETED)
            self.assertEqual(event.response_status_code, 200)
            self.assertEqual(event.response_headers, {"Content-Type": "application/json"})
            self.assertEqual(event.response_body, {"result": "Success"})
            self.assertEqual(event.completed_at, mock_now)
            self.assertEqual(len(event.logs), 2)  # Status change log + completion log
            self.assertIn("Call completed with status code: 200", event.logs[0])

    def test_set_error(self):
        """Test error setting and status transition to FAILED."""
        event = NetworkRequestEvent(request_id="test-id")
        
        with patch("datetime.datetime") as mock_datetime:
            mock_now = datetime.datetime(2025, 5, 20, 12, 0, 0)
            mock_datetime.utcnow.return_value = mock_now
            mock_datetime.isoformat = datetime.datetime.isoformat
            
            exception = ValueError("Test error")
            event.set_error(exception)
            
            self.assertEqual(event.status, RequestStatus.FAILED)
            self.assertEqual(event.error_type, "ValueError")
            self.assertEqual(event.error_message, "Test error")
            self.assertIsNotNone(event.error_details)
            self.assertEqual(event.completed_at, mock_now)
            self.assertEqual(len(event.logs), 2)  # Status change log + error log
            self.assertIn("Call failed: ValueError - Test error", event.logs[0])

    def test_add_log(self):
        """Test log addition."""
        event = NetworkRequestEvent(request_id="test-id")
        
        # Use a simpler approach without mocking datetime.isoformat
        event.add_log("Test log message")
        
        self.assertEqual(len(event.logs), 1)
        self.assertIn("Test log message", event.logs[0])
        # Just verify the log entry contains a timestamp format
        self.assertRegex(event.logs[0], r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}")


if __name__ == "__main__":
    unittest.main()