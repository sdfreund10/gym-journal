from zoneinfo import ZoneInfo

from django.http import HttpResponse
from django.test import Client, RequestFactory, SimpleTestCase, TestCase
from django.urls import reverse
from django.utils import timezone

from gym_journal.middleware import (
    SKIP_PATH_PREFIXES,
    TIMEZONE_COOKIE_NAME,
    TimeZoneMiddleware,
)


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


class TimeZoneMiddlewareTests(SimpleTestCase):
    def setUp(self):
        self.factory = RequestFactory()

    def tearDown(self):
        timezone.deactivate()

    def _run_with_cookie(self, cookie_value):
        activated = []

        def get_response(_request):
            activated.append(timezone.get_current_timezone_name())
            return HttpResponse("ok")

        middleware = TimeZoneMiddleware(get_response=get_response)
        request = self.factory.get("/")
        if cookie_value is not None:
            request.COOKIES[TIMEZONE_COOKIE_NAME] = cookie_value
        middleware(request)
        return activated[0] if activated else None

    def test_url_encoded_cookie_activates_timezone(self):
        active_tz = self._run_with_cookie("America%2FLos_Angeles")

        self.assertEqual(active_tz, "America/Los_Angeles")
        self.assertEqual(timezone.get_current_timezone_name(), "UTC")

    def test_plain_cookie_activates_timezone(self):
        active_tz = self._run_with_cookie("America/Los_Angeles")

        self.assertEqual(active_tz, "America/Los_Angeles")
        self.assertEqual(timezone.get_current_timezone_name(), "UTC")

    def test_invalid_cookie_deactivates_timezone(self):
        timezone.activate(ZoneInfo("Europe/London"))
        active_tz = self._run_with_cookie("Not%2FA%2FZone")

        self.assertEqual(active_tz, "UTC")
        self.assertEqual(timezone.get_current_timezone_name(), "UTC")

    def test_missing_cookie_deactivates_timezone(self):
        timezone.activate(ZoneInfo("Europe/London"))
        active_tz = self._run_with_cookie(None)

        self.assertEqual(active_tz, "UTC")
        self.assertEqual(timezone.get_current_timezone_name(), "UTC")

    def test_timezone_is_deactivated_after_response(self):
        active_tz = self._run_with_cookie("America%2FNew_York")

        self.assertEqual(active_tz, "America/New_York")
        self.assertEqual(timezone.get_current_timezone_name(), "UTC")
