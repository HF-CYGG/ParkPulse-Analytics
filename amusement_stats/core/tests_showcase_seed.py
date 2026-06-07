from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.conf import settings
from django.core.management import call_command
from django.test import SimpleTestCase, TestCase, override_settings

from accounts.models import VisitorProfile
from analytics.models import (
    HolidayCalendar,
    MaintenanceWorkOrder,
    ProjectIncident,
    ProjectReview,
    ServiceFacility,
    WeatherObservation,
)
from core.auth_utils import ADMIN_GROUP, STAFF_GROUP
from projects.models import Project
from records.models import PlayRecord
from visitor.models import ItineraryPlan, VisitorFavorite, VisitorFeedback, VisitorFeedbackMessage


@override_settings(PASSWORD_HASHERS=["django.contrib.auth.hashers.MD5PasswordHasher"])
class ShowcaseSeedCommandTests(TestCase):
    def test_seed_showcase_data_creates_complete_demo_environment_idempotently(self):
        call_command("seed_showcase_data", days=8, records_per_day=6)

        User = get_user_model()
        admin = User.objects.get(username="demo_admin")
        staff = User.objects.get(username="demo_staff")
        visitor = User.objects.get(username="demo_visitor")

        self.assertTrue(admin.is_superuser)
        self.assertTrue(admin.groups.filter(name=ADMIN_GROUP).exists())
        self.assertTrue(staff.groups.filter(name=STAFF_GROUP).exists())
        self.assertTrue(visitor.check_password("Visitor@2026!"))
        self.assertTrue(Group.objects.filter(name=ADMIN_GROUP).exists())
        self.assertTrue(Group.objects.filter(name=STAFF_GROUP).exists())

        self.assertGreaterEqual(Project.objects.count(), 12)
        self.assertGreaterEqual(PlayRecord.objects.count(), 8 * 6)
        self.assertGreaterEqual(ServiceFacility.objects.count(), 6)
        self.assertGreaterEqual(ProjectReview.objects.count(), 12)
        self.assertGreaterEqual(ProjectIncident.objects.count(), 3)
        self.assertGreaterEqual(MaintenanceWorkOrder.objects.count(), 3)
        self.assertGreaterEqual(HolidayCalendar.objects.count(), 7)
        self.assertGreaterEqual(WeatherObservation.objects.count(), 8)
        self.assertGreaterEqual(ItineraryPlan.objects.filter(is_active=True).count(), 12)
        self.assertGreaterEqual(VisitorFavorite.objects.filter(user=visitor).count(), 3)
        self.assertTrue(VisitorProfile.objects.filter(user=visitor, with_children=True).exists())
        self.assertTrue(VisitorFeedback.objects.filter(user=visitor).exists())
        self.assertTrue(VisitorFeedbackMessage.objects.filter(feedback__user=visitor).exists())

        project_count = Project.objects.count()
        facility_count = ServiceFacility.objects.count()
        weather_count = WeatherObservation.objects.count()
        plan_count = ItineraryPlan.objects.count()
        call_command("seed_showcase_data", days=8, records_per_day=6)

        self.assertEqual(Project.objects.count(), project_count)
        self.assertEqual(ServiceFacility.objects.count(), facility_count)
        self.assertEqual(WeatherObservation.objects.count(), weather_count)
        self.assertEqual(ItineraryPlan.objects.count(), plan_count)


class ShowcaseEntrypointTests(SimpleTestCase):
    def test_entrypoint_runs_showcase_seed_before_derived_analytics_when_enabled(self):
        entrypoint = settings.BASE_DIR / "docker" / "entrypoint.sh"
        content = entrypoint.read_text(encoding="utf-8")

        self.assertIn('DJANGO_SEED_DEMO_DATA:-0', content)
        seed_pos = content.index("manage.py seed_showcase_data")
        snapshot_pos = content.index("manage.py rebuild_heat_snapshots")
        forecast_pos = content.index("manage.py train_heat_forecast")

        self.assertLess(seed_pos, snapshot_pos)
        self.assertLess(snapshot_pos, forecast_pos)
        self.assertIn("DJANGO_SHOWCASE_DAYS:-90", content)
        self.assertIn("DJANGO_SHOWCASE_RECORDS_PER_DAY:-120", content)
