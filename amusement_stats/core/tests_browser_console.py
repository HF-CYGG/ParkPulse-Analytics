from django.conf import settings
from django.test import SimpleTestCase
from django.urls import reverse


class BrowserConsoleCompatibilityTests(SimpleTestCase):
    def test_favicon_route_redirects_to_static_asset(self):
        response = self.client.get("/favicon.ico")

        self.assertEqual(response.status_code, 301)
        self.assertEqual(response["Location"], "/static/img/favicon.svg")

    def test_cross_origin_opener_policy_is_disabled_by_default(self):
        self.assertIsNone(settings.SECURE_CROSS_ORIGIN_OPENER_POLICY)

        response = self.client.get(reverse("healthz"))

        self.assertNotIn("Cross-Origin-Opener-Policy", response)
