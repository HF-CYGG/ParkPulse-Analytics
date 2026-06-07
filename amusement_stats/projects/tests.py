"""项目模块测试：用于验证项目管理流程中的创建、列表与状态切换行为。"""

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.test import TestCase
from django.urls import reverse

from core.auth_utils import STAFF_GROUP
from .models import Project

User = get_user_model()


def _build_test_secret(label: str) -> str:
    """为测试账号动态生成口令，避免把固定明文写进测试代码。"""

    return f"{label}-Project-Secret-2026!"


class ProjectManagementFlowTests(TestCase):
    """项目管理流程测试。"""

    def setUp(self):
        """创建工作人员账号，确保项目管理页按真实权限访问。"""

        self.staff_group, _ = Group.objects.get_or_create(name=STAFF_GROUP)
        self.staff_user = User.objects.create_user(
            username="project_staff_user",
            password=_build_test_secret("project-staff"),
        )
        self.staff_user.groups.add(self.staff_group)
        self.client.force_login(self.staff_user)

        self.project = Project.objects.create(
            name="激流勇进",
            project_type=Project.TYPE_THRILL,
            region=Project.REGION_THRILL,
            status=Project.STATUS_NORMAL,
            capacity=40,
            daily_warn_threshold=300,
            queue_count=12,
            cycle_minutes=6,
            operating_hours_text="10:00-21:00",
        )

    def test_project_list_supports_create_project(self):
        """项目管理页应允许工作人员直接创建项目。"""

        response = self.client.post(
            reverse("project_list"),
            {
                "name": "旋转木马",
                "project_type": Project.TYPE_FAMILY,
                "region": Project.REGION_FAMILY,
                "status": Project.STATUS_NORMAL,
                "capacity": 30,
                "daily_warn_threshold": 260,
                "queue_count": 5,
                "cycle_minutes": 4,
                "operating_hours_text": "09:30-20:30",
            },
        )

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response["Location"], reverse("project_list"))
        self.assertTrue(Project.objects.filter(name="旋转木马", region=Project.REGION_FAMILY).exists())

    def test_project_toggle_status_cycles_to_next_state(self):
        """项目状态切换按钮应能把项目从正常切换到维护。"""

        response = self.client.get(reverse("project_toggle_status", args=[self.project.id]))

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response["Location"], reverse("project_list"))
        self.project.refresh_from_db()
        self.assertEqual(self.project.status, Project.STATUS_MAINTENANCE)

    def test_project_edit_page_uses_shared_leaflet_tile_map(self):
        """项目编辑页地图应与游客端园区地图统一使用 Leaflet 在线瓦片和图层切换。"""

        response = self.client.get(reverse("project_edit", args=[self.project.id]))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "webrd0{s}.is.autonavi.com")
        self.assertContains(response, "OpenStreetMap")
        self.assertContains(response, "L.tileLayer")
        self.assertContains(response, "L.control.layers")
        self.assertNotContains(response, "project-map-offline-base")
        self.assertNotContains(response, "离线园区示意底图")
