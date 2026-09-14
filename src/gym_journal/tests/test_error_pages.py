from django.test import Client, RequestFactory, SimpleTestCase, override_settings
from django.urls import reverse
from django.views.defaults import server_error


@override_settings(DEBUG=False, ALLOWED_HOSTS=["testserver"])
class ErrorPageTests(SimpleTestCase):
    def setUp(self):
        self.client = Client()
        self.factory = RequestFactory()

    def test_404_page_renders_branded_content(self):
        response = self.client.get("/missing-page-for-error-test/")

        self.assertEqual(response.status_code, 404)
        self.assertTemplateUsed(response, "404.html")
        self.assertContains(response, "Gym Journal", status_code=404)
        self.assertContains(response, "Page not found", status_code=404)
        self.assertContains(response, reverse("index"), status_code=404)

    def test_500_page_renders_branded_content(self):
        request = self.factory.get("/")

        with self.assertTemplateUsed("500.html"):
            response = server_error(request)

        self.assertEqual(response.status_code, 500)
        self.assertContains(response, "Gym Journal", status_code=500)
        self.assertContains(response, "Something went wrong", status_code=500)
        self.assertContains(response, 'href="/"', status_code=500)
