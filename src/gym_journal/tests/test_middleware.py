from django.test import Client, TestCase
from django.urls import reverse

from gym_journal.middleware import SKIP_PATH_PREFIXES


class RequestLoggingMiddlewareTests(TestCase):
    def setUp(self):
        self.client = Client()

    def test_health_response_includes_request_id_header(self):
        response = self.client.get(reverse("health"))

        self.assertEqual(response.status_code, 200)
        self.assertIn("X-Request-ID", response)
        self.assertTrue(response["X-Request-ID"])

    def test_authenticated_request_includes_request_id_header(self):
        with self.assertLogs("gym_journal", level="INFO") as logs:
            response = self.client.get(reverse("login"))

        self.assertEqual(response.status_code, 200)
        self.assertIn("X-Request-ID", response)
        self.assertTrue(
            any(record.msg == "request completed" for record in logs.records)
        )

    def test_health_requests_are_not_logged(self):
        with self.assertNoLogs("gym_journal", level="INFO"):
            self.client.get(reverse("health"))

    def test_skip_path_prefixes(self):
        self.assertIn("/health/", SKIP_PATH_PREFIXES)
        self.assertIn("/static/", SKIP_PATH_PREFIXES)
