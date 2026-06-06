from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from analytics.models import HolidayCalendar, ProjectIncident, ProjectReview, PromotionEvent
from projects.models import Project


class Command(BaseCommand):
    help = "Seed optional analytics demo data for reviews, incidents, holidays, and promotions."

    def handle(self, *args, **options):
        today = timezone.localdate()
        projects = list(Project.objects.all()[:8])
        for idx, project in enumerate(projects):
            ProjectReview.objects.get_or_create(project=project, rating=4 + (idx % 2), comment="演示评分数据")
            if idx % 3 == 0:
                ProjectIncident.objects.get_or_create(
                    project=project,
                    incident_type=ProjectIncident.TYPE_MAINTENANCE,
                    started_at=timezone.now() - timedelta(days=idx + 1),
                    defaults={"severity": 1, "description": "例行维护演示数据", "downtime_minutes": 30 + idx * 5},
                )
        HolidayCalendar.objects.get_or_create(
            date=today + timedelta(days=1),
            defaults={"name": "演示节假日", "day_type": HolidayCalendar.TYPE_HOLIDAY, "heat_multiplier": 1.25},
        )
        PromotionEvent.objects.get_or_create(
            name="演示亲子优惠",
            defaults={
                "start_date": today,
                "end_date": today + timedelta(days=7),
                "description": "用于验证促销活动对热度评分的外部维度影响。",
                "heat_multiplier": 1.15,
                "is_active": True,
            },
        )
        self.stdout.write(self.style.SUCCESS("Analytics demo data seeded."))
