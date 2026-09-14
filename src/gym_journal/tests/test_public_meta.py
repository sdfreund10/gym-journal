from django.test import Client, SimpleTestCase, override_settings
from django.urls import reverse


class PublicMetaTests(SimpleTestCase):
    def setUp(self):
        self.client = Client()

    def test_robots_txt_disallows_all_crawlers(self):
        response = self.client.get("/robots.txt")

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response["Content-Type"].startswith("text/plain"))
        self.assertContains(response, "User-agent: *")
        self.assertContains(response, "Disallow: /")

    def test_security_txt_is_available(self):
        response = self.client.get("/.well-known/security.txt")

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response["Content-Type"].startswith("text/plain"))
        self.assertContains(response, "Contact:")
        self.assertContains(response, "Expires:")

    def test_privacy_page_is_public(self):
        response = self.client.get(reverse("privacy"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Privacy")
        self.assertContains(response, "Gym Journal")

    def test_terms_page_is_public(self):
        response = self.client.get(reverse("terms"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Terms")
        self.assertContains(response, "Gym Journal")

    def test_login_links_legal_pages_and_manifest(self):
        response = self.client.get(reverse("login"))

        self.assertContains(response, reverse("privacy"))
        self.assertContains(response, reverse("terms"))
        self.assertContains(response, "site.webmanifest")


@override_settings(
    MIDDLEWARE=[
        "django.middleware.security.SecurityMiddleware",
        "gym_journal.middleware.ContentSecurityPolicyMiddleware",
        "django.contrib.sessions.middleware.SessionMiddleware",
        "django.middleware.common.CommonMiddleware",
        "django.middleware.csrf.CsrfViewMiddleware",
        "django.contrib.auth.middleware.AuthenticationMiddleware",
        "django.contrib.messages.middleware.MessageMiddleware",
        "django.middleware.clickjacking.XFrameOptionsMiddleware",
    ]
)
class ContentSecurityPolicyMiddlewareTests(SimpleTestCase):
    def test_csp_header_is_set(self):
        response = Client().get(reverse("login"))

        self.assertEqual(response.status_code, 200)
        csp = response["Content-Security-Policy"]
        self.assertIn("default-src 'self'", csp)
        self.assertIn("cdn.tailwindcss.com", csp)
        self.assertIn("fonts.googleapis.com", csp)
        self.assertIn("frame-ancestors 'none'", csp)
