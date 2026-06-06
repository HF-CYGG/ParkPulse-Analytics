"""看板模块测试：用于验证经营看板首页在核心数据存在时可正常渲染。"""

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
    """为测试账号动态生成口令，避免把固定明文写进测试代码。"""

    return f"{label}-Dashboard-Secret-2026!"


class DashboardFlowTests(TestCase):
    """经营看板流程测试。"""

    def setUp(self):
        """创建管理员与基础运营数据，确保看板请求能走完整计算链路。"""

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
        """管理员访问经营看板首页时，应返回 200 并输出基础指标。"""

        response = self.client.get(reverse("index"))

        self.assertEqual(response.status_code, 200)
        # 页面主标题当前文案为“运营看板”，这里按真实用户可见文本断言。
        self.assertContains(response, "运营看板")
        self.assertContains(response, self.project.name)
        self.assertGreaterEqual(response.context["metrics"]["total_visits"], 1)


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
        self.assertTrue(0 <= rows[0]["score"] <= 100)

    def test_forecast_service_returns_seven_day_rows_and_peak_warning(self):
        from analytics.services.forecasting import build_forecast_rows

        result = build_forecast_rows(days=30, horizon=7)

        self.assertEqual(result["mode"], "baseline")
        self.assertGreaterEqual(len(result["items"]), 1)
        hot_row = next(item for item in result["items"] if item["project_id"] == self.project_hot.id)
        self.assertEqual(len(hot_row["forecast"]), 7)
        self.assertTrue(hot_row["alert"])
        self.assertIn("warning", hot_row)
