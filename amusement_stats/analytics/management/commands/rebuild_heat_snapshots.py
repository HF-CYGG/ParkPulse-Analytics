from datetime import datetime, time, timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from analytics.models import ProjectHeatSnapshot
from analytics.services.heat import compute_project_heat_scores


class Command(BaseCommand):
    help = "Rebuild project heat snapshots from existing play records."

    def add_arguments(self, parser):
        parser.add_argument("--days", type=int, default=30)

    def handle(self, *args, **options):
        days = max(1, min(int(options["days"]), 365))
        today = timezone.localdate()
        count = 0
        for offset in range(days - 1, -1, -1):
            target_day = today - timedelta(days=offset)
            snapshot_time = timezone.make_aware(datetime.combine(target_day, time(hour=12)))
            rows = compute_project_heat_scores(start_date=target_day, end_date=target_day)
            for row in rows:
                ProjectHeatSnapshot.objects.update_or_create(
                    project_id=row["project_id"],
                    snapshot_time=snapshot_time,
                    defaults={
                        "score": row["score"],
                        "base_score": row["dimensions"]["base"],
                        "time_score": row["dimensions"]["time"],
                        "user_score": row["dimensions"]["user"],
                        "operations_score": row["dimensions"]["operations"],
                        "external_score": row["dimensions"]["external"],
                        "subjective_score": row["dimensions"]["subjective"],
                        "metrics": row["metrics"],
                    },
                )
                count += 1
        self.stdout.write(self.style.SUCCESS(f"Rebuilt {count} heat snapshots for {days} day(s)."))
