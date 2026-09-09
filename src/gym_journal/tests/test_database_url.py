from django.core.exceptions import ImproperlyConfigured
from django.test import SimpleTestCase

from config.database_url import database_from_url


class DatabaseFromUrlTests(SimpleTestCase):
    def test_parses_postgres_url(self):
        config = database_from_url(
            "postgres://gym:s3cret@db.example.com:5433/gym_journal?sslmode=require"
        )

        self.assertEqual(config["ENGINE"], "django.db.backends.postgresql")
        self.assertEqual(config["NAME"], "gym_journal")
        self.assertEqual(config["USER"], "gym")
        self.assertEqual(config["PASSWORD"], "s3cret")
        self.assertEqual(config["HOST"], "db.example.com")
        self.assertEqual(config["PORT"], "5433")
        self.assertEqual(config["OPTIONS"], {"sslmode": "require"})
        self.assertTrue(config["CONN_HEALTH_CHECKS"])

    def test_defaults_port_when_missing(self):
        config = database_from_url("postgresql://gym@localhost/gym_journal")

        self.assertEqual(config["PORT"], "5432")
        self.assertEqual(config["OPTIONS"], {})

    def test_rejects_non_postgres_scheme(self):
        with self.assertRaises(ImproperlyConfigured):
            database_from_url("mysql://user:pass@localhost:3306/gym_journal")
