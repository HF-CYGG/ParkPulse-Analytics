from datetime import timedelta

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from core.auth_utils import ADMIN_GROUP
from projects.models import Project
from records.models import PlayRecord

User = get_user_model()


def _build_test_secret(label: str) -> str:
    return f"{label}-Dashboard-Secret-2026!"


class DashboardFlowTests(TestCase):
    def setUp(self):
        self.admin_group, _ = Group.objects.get_or_create(name=ADMIN_GROUP)
        self.admin_user = User.objects.create_user(
            username="dashboard_admin_user",
            password=_build_test_secret("dashboard-admin"),
        )
        self.admin_user.groups.add(self.admin_group)
        self.client.force_login(self.admin_user)

        self.project = Project.objects.create(
            name="海盗船",
            project_type=Project.TYPE_THRILL,
            region=Project.REGION_THRILL,
            status=Project.STATUS_NORMAL,
            capacity=60,
            daily_warn_threshold=240,
            queue_count=20,
            cycle_minutes=6,
        )
        now = timezone.now()
        PlayRecord.objects.create(
            project=self.project,
            play_time=now - timedelta(hours=1),
            queue_time=18,
            repeat_count=1,
            status_snapshot=Project.STATUS_NORMAL,
            created_by=self.admin_user,
        )

    def test_dashboard_index_renders_for_admin(self):
        response = self.client.get(reverse("index"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.project.name)
        self.assertContains(response, "projectComparePanel")
        self.assertNotContains(response, "forecastDaySlider")
        self.assertNotContains(response, "forecastTimelineBody")
        self.assertNotContains(response, "predictTableBody")
        self.assertGreaterEqual(response.context["metrics"]["total_visits"], 1)

    def test_forecast_dashboard_renders_for_admin(self):
        response = self.client.get(reverse("dashboard_forecast"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "forecastDaySlider")
        self.assertContains(response, "forecastTimelineBody")
        self.assertContains(response, "predictTableBody")
        self.assertContains(response, 'id="refreshEvaluationButton"')
        self.assertContains(response, 'id="evaluationTableBody"')
        self.assertNotContains(response, 'href="/analytics/api/forecast-evaluation/?refresh=1"')
        self.assertContains(response, self.project.name)

    def test_spatial_heat_page_renders_for_admin(self):
        response = self.client.get(reverse("dashboard_spatial_heat"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "spatialHeatData")
        self.assertContains(response, "spatialHeatCanvas")
        self.assertContains(response, "vendor/leaflet/leaflet.css")
        self.assertContains(response, "vendor/leaflet/leaflet.js")
        self.assertContains(response, "webrd0{s}.is.autonavi.com")
        self.assertContains(response, "OpenStreetMap")
        self.assertContains(response, "L.control.layers")
        self.assertContains(response, "L.circle")
        self.assertContains(response, "L.marker")
        self.assertNotContains(response, "spatial-map-viewport")
        self.assertNotContains(response, "data-map-x")
        self.assertNotContains(response, "data-map-y")
        self.assertContains(response, "spatialTimeSlider")
        self.assertContains(response, "spatialHeatApiUrl")
        self.assertContains(response, "六维指标")

    def test_predict_api_returns_dashboard_display_fields(self):
        response = self.client.get(reverse("api_predict"), {"days": 7})

        self.assertEqual(response.status_code, 200)
        payload = response.json()["data"]
        self.assertGreaterEqual(len(payload["prediction_rows"]), 1)
        row = payload["prediction_rows"][0]
        self.assertEqual(row["name"], self.project.name)
        self.assertIn("predicted_next_day", row)
        self.assertIn("predicted_lr", row)
        self.assertEqual(row["threshold"], self.project.daily_warn_threshold)
        self.assertIn("capacity_risk_threshold", row)
        self.assertIn("is_alert", row)
        if payload["alert_rows"]:
            self.assertNotEqual(payload["alert_rows"][0]["name"], "")


class AnalyticsServiceContractTests(TestCase):
    def setUp(self):
        self.project_hot = Project.objects.create(
            name="Analytics Hot Ride",
            project_type=Project.TYPE_THRILL,
            region=Project.REGION_THRILL,
            status=Project.STATUS_NORMAL,
            capacity=50,
            daily_warn_threshold=3,
            queue_count=12,
        )
        self.project_calm = Project.objects.create(
            name="Analytics Calm Ride",
            project_type=Project.TYPE_FAMILY,
            region=Project.REGION_FAMILY,
            status=Project.STATUS_NORMAL,
            capacity=50,
            daily_warn_threshold=20,
            queue_count=2,
        )
        now = timezone.now()
        for i in range(6):
            PlayRecord.objects.create(
                project=self.project_hot,
                play_time=now - timedelta(hours=i),
                queue_time=8 + i,
                repeat_count=1,
                status_snapshot=Project.STATUS_NORMAL,
            )
        PlayRecord.objects.create(
            project=self.project_calm,
            play_time=now - timedelta(hours=2),
            queue_time=3,
            repeat_count=0,
            status_snapshot=Project.STATUS_NORMAL,
        )

    def test_heat_score_exposes_weighted_breakdown_and_orders_hotter_projects(self):
        from analytics.services.heat import compute_project_heat_scores

        rows = compute_project_heat_scores(days=7)

        self.assertGreaterEqual(len(rows), 2)
        self.assertEqual(rows[0]["project_id"], self.project_hot.id)
        self.assertIn("dimensions", rows[0])
        self.assertIn("base", rows[0]["dimensions"])
        self.assertIn("time", rows[0]["dimensions"])
        self.assertIn("operations", rows[0]["dimensions"])
        self.assertIn("reasons", rows[0])
        self.assertIn("dimension_reasons", rows[0])
        self.assertIn("user_profile_breakdown", rows[0]["metrics"])
        self.assertTrue(0 <= rows[0]["score"] <= 100)

    def test_forecast_service_returns_seven_day_rows_and_peak_warning(self):
        from analytics.services.forecasting import build_forecast_rows

        result = build_forecast_rows(days=30, horizon=7)

        self.assertIn(result["mode"], {"moving_average", "linear_regression", "prophet", "lstm", "mixed"})
        self.assertGreaterEqual(len(result["items"]), 1)
        hot_row = next(item for item in result["items"] if item["project_id"] == self.project_hot.id)
        self.assertEqual(len(hot_row["forecast"]), 7)
        self.assertTrue(hot_row["alert"])
        self.assertIn("warning", hot_row)
        self.assertIn("candidate_models", hot_row)
        self.assertIn("selected_model", hot_row)
