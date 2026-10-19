"""Tests for application error logging."""

import unittest
from types import SimpleNamespace

from app.main import create_app


class ApiErrorLoggingTests(unittest.IsolatedAsyncioTestCase):
    async def test_unhandled_request_exception_is_logged_and_sanitized(self) -> None:
        app = create_app()
        handler = app.exception_handlers[Exception]
        request = SimpleNamespace(
            method="GET",
            url=SimpleNamespace(path="/books"),
        )
        error = RuntimeError("internal failure detail")

        with self.assertLogs("app.main", level="ERROR") as captured:
            response = await handler(request, error)

        self.assertIn("Unhandled error while processing GET /books", captured.output[0])
        self.assertIn("RuntimeError: internal failure detail", captured.output[0])
        self.assertEqual(response.status_code, 500)
        self.assertEqual(
            response.body,
            b'{"detail":"Internal server error"}',
        )
