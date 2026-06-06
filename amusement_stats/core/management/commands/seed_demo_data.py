import random
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.utils import timezone

from projects.models import Project
from records.models import PlayRecord


class Command(BaseCommand):
    help = "生成演示数据（项目+游玩记录）"

    def add_arguments(self, parser):
        parser.add_argument("--days", type=int, default=14, help="生成最近 N 天数据")
        parser.add_argument("--records-per-day", type=int, default=40, help="每天生成记录数")

    def handle(self, *args, **options):
        days = options["days"]
        records_per_day = options["records_per_day"]

        demo_projects = [
            ("过山车", Project.TYPE_THRILL, 24),
            ("海盗船", Project.TYPE_THRILL, 28),
            ("旋转木马", Project.TYPE_FAMILY, 30),
            ("摩天轮", Project.TYPE_VIEW, 40),
            ("激流勇进", Project.TYPE_VIEW, 18),
        ]

        projects = []
        for name, ptype, capacity in demo_projects:
            region_map = {
                Project.TYPE_FAMILY: Project.REGION_FAMILY,
                Project.TYPE_THRILL: Project.REGION_THRILL,
                Project.TYPE_VIEW: Project.REGION_VIEW,
            }
            region = region_map.get(ptype, Project.REGION_REST)
            p, _ = Project.objects.get_or_create(
                name=name,
                defaults={
                    "project_type": ptype,
                    "capacity": capacity,
                    "daily_warn_threshold": capacity * 12,
                    "status": Project.STATUS_NORMAL,
                    "region": region,
                },
            )
            if not p.region:
                p.region = region
                p.save(update_fields=["region"])
            projects.append(p)

        user = get_user_model().objects.filter(is_superuser=True).first()
        now = timezone.localtime()
        created = 0
        for i in range(days):
            day = now.date() - timedelta(days=i)
            for _ in range(records_per_day):
                hour = random.randint(10, 18)
                minute = random.randint(0, 59)
                dt = timezone.make_aware(
                    timezone.datetime.combine(day, timezone.datetime.min.time()) + timedelta(hours=hour, minutes=minute)
                )
                project = random.choice(projects)
                PlayRecord.objects.create(
                    project=project,
                    play_time=dt,
                    queue_time=random.randint(3, 35),
                    repeat_count=random.randint(0, 3),
                    status_snapshot=random.choice(
                        [Project.STATUS_NORMAL, Project.STATUS_NORMAL, Project.STATUS_MAINTENANCE]
                    ),
                    note="演示数据自动生成",
                    created_by=user,
                )
                created += 1

        self.stdout.write(self.style.SUCCESS(f"演示数据生成完成：新增 {created} 条记录，项目 {len(projects)} 个。"))

