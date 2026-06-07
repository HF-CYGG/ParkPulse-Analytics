from datetime import timedelta

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from analytics.models import (
    ForecastEvaluation,
    ProjectForecast,
    ProjectIncident,
    ProjectReview,
    ServiceFacility,
    WeatherObservation,
)
from core.auth_utils import STAFF_GROUP
from projects.models import Project
from records.models import PlayRecord


User = get_user_model()


def _secret(label: str) -> str:
    return f"{label}-Secret-2026!"


class AnalyticsEnterpriseRequirementTests(TestCase):
    def setUp(self):
        self.staff_group, _ = Group.objects.get_or_create(name=STAFF_GROUP)
        self.staff_user = User.objects.create_user(username="analytics_staff", password=_secret("staff"))
        self.staff_user.groups.add(self.staff_group)
        self.visitor_user = User.objects.create_user(username="analytics_visitor", password=_secret("visitor"))
        self.project = Project.objects.create(
            name="Enterprise Coaster",
            project_type=Project.TYPE_THRILL,
            capacity=20,
            queue_count=18,
            daily_warn_threshold=20,
            latitude=31.230400,
            longitude=121.473700,
        )
        now = timezone.now()
        for day in range(12):
            for idx in range(5 + day):
                PlayRecord.objects.create(
                    project=self.project,
                    play_time=now - timedelta(days=day, hours=idx % 4),
                    queue_time=20 + day,
                    repeat_count=idx % 2,
                )

    def test_required_enterprise_models_and_fields_exist(self):
        review_fields = {field.name for field in ProjectReview._meta.fields}
        self.assertTrue({"experience_score", "queue_reasonableness_score", "safety_score", "image"}.issubset(review_fields))

        incident_fields = {field.name for field in ProjectIncident._meta.fields}
        self.assertTrue({"handled_by", "status", "image", "notes"}.issubset(incident_fields))

        evaluation_fields = {field.name for field in ForecastEvaluation._meta.fields}
        self.assertTrue({"validation_start", "validation_end", "parameters"}.issubset(evaluation_fields))

        from analytics.models import MaintenanceWorkOrder

        work_order_fields = {field.name for field in MaintenanceWorkOrder._meta.fields}
        self.assertTrue({"project", "incident", "status", "handled_by", "started_at", "ended_at", "notes"}.issubset(work_order_fields))

        weather_fields = {field.name for field in WeatherObservation._meta.fields}
        self.assertTrue({"date", "weather_type", "temperature_c", "rain_mm", "humidity", "heat_multiplier", "description"}.issubset(weather_fields))

    def test_forecasting_pipeline_fallback_persists_forecasts_and_evaluations(self):
        from analytics.forecasting.pipeline import run_forecast_pipeline

        result = run_forecast_pipeline(model="all", days=30, horizon=7, persist=True)

        self.assertIn(result["mode"], {"moving_average", "linear_regression", "prophet", "lstm", "mixed"})
        self.assertIn("candidate_models", result)
        self.assertEqual(ProjectForecast.objects.filter(project=self.project).count(), 7)
        model_names = set(ForecastEvaluation.objects.filter(project=self.project).values_list("model_name", flat=True))
        self.assertIn("moving_average", model_names)
        self.assertIn("linear_regression", model_names)
        forecast = ProjectForecast.objects.filter(project=self.project).order_by("target_time").first()
        self.assertIn("confidence", forecast.factors)
        self.assertIn("model", forecast.factors)
        self.assertIn("candidate_models", forecast.factors)
        self.assertIn("external_factors", forecast.factors)

    def test_standard_analytics_apis_and_permissions(self):
        self.client.force_login(self.visitor_user)
        response = self.client.get("/analytics/api/forecast/heat/")
        self.assertEqual(response.status_code, 302)

        self.client.force_login(self.staff_user)
        for path in [
            "/analytics/api/forecast/heat/",
            "/analytics/api/forecast/alerts/",
            "/analytics/api/heat/timeline/",
            f"/analytics/api/heat/project/{self.project.id}/detail/",
            f"/analytics/api/heat/project/{self.project.id}/forecast/",
            "/analytics/api/heat/spatial/",
        ]:
            response = self.client.get(path)
            self.assertEqual(response.status_code, 200, path)
            self.assertEqual(response.json()["code"], 0, path)

    def test_spatial_heat_uses_service_facility_linked_heat(self):
        ServiceFacility.objects.create(
            name="Coaster Cafe",
            facility_type=ServiceFacility.TYPE_CATERING,
            region=Project.REGION_THRILL,
            latitude=31.230500,
            longitude=121.473800,
        )

        self.client.force_login(self.staff_user)
        response = self.client.get("/analytics/api/heat/spatial/")

        item = response.json()["data"]["items"][0]
        self.assertEqual(item["facilities"][0]["name"], "Coaster Cafe")
        self.assertGreater(item["facilities"][0]["linked_heat"], 0)
        self.assertIn("dimension_reasons", item)
        self.assertIn("base", item["dimensions"])
        self.assertIn("weather", item["metrics"]["external"])

    def test_heat_score_uses_weather_and_profile_breakdown(self):
        from analytics.services.heat import compute_project_heat_scores

        today = timezone.localdate()
        WeatherObservation.objects.create(
            date=today,
            weather_type=WeatherObservation.TYPE_RAIN,
            temperature_c=18,
            rain_mm=8,
            humidity=88,
            heat_multiplier=0.82,
            description="测试降雨天气",
        )

        rows = compute_project_heat_scores(start_date=today, end_date=today)
        row = next(item for item in rows if item["project_id"] == self.project.id)

        self.assertIn("reasons", row)
        self.assertIn("dimension_reasons", row)
        self.assertIn("external", row["dimension_reasons"])
        self.assertIn("weather", row["metrics"]["external"])
        self.assertIn("user_profile_breakdown", row["metrics"])


class VisitorRecommendationEnterpriseTests(TestCase):
    def setUp(self):
        self.family = Project.objects.create(
            name="Family Star",
            project_type=Project.TYPE_FAMILY,
            capacity=30,
            queue_count=3,
            latitude=31.230100,
            longitude=121.473100,
        )
        self.family_low_rating = Project.objects.create(
            name="Family Low Rating",
            project_type=Project.TYPE_FAMILY,
            capacity=30,
            queue_count=2,
            latitude=31.230200,
            longitude=121.473200,
        )
        self.closed = Project.objects.create(
            name="Closed Family",
            project_type=Project.TYPE_FAMILY,
            status=Project.STATUS_CLOSED,
            capacity=30,
            queue_count=0,
        )
        user = User.objects.create_user(username="rating_user", password=_secret("rating"))
        ProjectReview.objects.create(project=self.family, user=user, experience_score=5, queue_reasonableness_score=5, safety_score=5)
        ProjectReview.objects.create(project=self.family_low_rating, user=user, experience_score=2, queue_reasonableness_score=2, safety_score=2)

    def test_recommendation_formula_uses_rating_and_excludes_closed_projects(self):
        from analytics.services.recommendations import build_recommendations

        result = build_recommendations({"with_children": True, "preference_tags": "亲子,低排队", "available_minutes": 90})
        route_names = [item["project_name"] for item in result["route"]["items"]]

        self.assertEqual(route_names[0], "Family Star")
        self.assertNotIn("Closed Family", route_names)
