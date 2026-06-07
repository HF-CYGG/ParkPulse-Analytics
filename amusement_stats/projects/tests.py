"""项目模块测试：覆盖项目管理中的创建、编辑、状态切换与地图组件行为。"""

import base64

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
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
        """创建工作人员账号。"""

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

    def test_project_cover_storage_settings_are_configured_for_uploads(self):
        """项目封面上传需要默认文件存储和绝对媒体 URL。"""

        self.assertEqual(settings.STORAGES["default"]["BACKEND"], "django.core.files.storage.FileSystemStorage")
        self.assertEqual(settings.MEDIA_URL, "/media/")
        self.assertTrue(settings.SERVE_MEDIA_FILES)

    @override_settings(
        STORAGES={
            "default": {
                "BACKEND": "django.core.files.storage.InMemoryStorage",
            },
            "staticfiles": {
                "BACKEND": "whitenoise.storage.CompressedStaticFilesStorage",
            },
        }
    )
    def test_project_edit_uploads_cover_image_with_absolute_media_url(self):
        """项目编辑页应能保存封面图，并生成可在当前页面直接访问的媒体路径。"""

        tiny_png = base64.b64decode(
            "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="
        )
        upload = SimpleUploadedFile("cover.png", tiny_png, content_type="image/png")

        response = self.client.post(
            reverse("project_edit", args=[self.project.id]),
            {
                "name": self.project.name,
                "project_type": self.project.project_type,
                "region": self.project.region,
                "status": self.project.status,
                "capacity": self.project.capacity,
                "daily_warn_threshold": self.project.daily_warn_threshold,
                "queue_count": self.project.queue_count,
                "cycle_minutes": self.project.cycle_minutes,
                "operating_hours_text": self.project.operating_hours_text,
                "short_description": "Cover upload smoke",
                "latitude": "31.232000",
                "longitude": "121.502000",
                "cover_image": upload,
            },
        )

        self.assertEqual(response.status_code, 302)
        self.project.refresh_from_db()
        self.assertTrue(self.project.cover_image.name.startswith("project_covers/"))
        self.assertTrue(self.project.cover_image.url.startswith("/media/project_covers/"))

        edit_response = self.client.get(reverse("project_edit", args=[self.project.id]))
        self.assertContains(edit_response, 'src="/media/project_covers/')

    def test_project_edit_page_uses_shared_leaflet_tile_map(self):
        """项目编辑页地图应统一使用 Leaflet 在线瓦片和图层切换。"""

        response = self.client.get(reverse("project_edit", args=[self.project.id]))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "webrd0{s}.is.autonavi.com")
        self.assertContains(response, "OpenStreetMap")
        self.assertContains(response, "L.tileLayer")
        self.assertContains(response, "L.control.layers")
        self.assertNotContains(response, "project-map-offline-base")
        self.assertNotContains(response, "离线园区示意底图")
