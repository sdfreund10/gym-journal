from unittest.mock import patch

from django.test import Client, TestCase
from django.urls import reverse


class HealthViewTests(TestCase):
    def setUp(self):
        self.client = Client()

    def test_health_returns_ok_when_database_is_available(self):
        response = self.client.get(reverse("health"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"status": "ok"})

    def test_health_does_not_require_authentication(self):
        response = self.client.get(reverse("health"))

        self.assertEqual(response.status_code, 200)

    @patch("gym_journal.health.connection.ensure_connection", side_effect=Exception("db down"))
    def test_health_returns_unavailable_when_database_is_down(self, _mock_ensure_connection):
        response = self.client.get(reverse("health"))

        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.json(), {"status": "unavailable"})
