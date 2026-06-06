"""记录模块测试：用于验证游玩记录录入流程对工作人员是否保持可用。"""

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from core.auth_utils import STAFF_GROUP
from projects.models import Project
from .models import PlayRecord

User = get_user_model()


def _build_test_secret(label: str) -> str:
    """为测试账号动态生成口令，避免把固定明文写进测试代码。"""

    return f"{label}-Record-Secret-2026!"


class RecordEntryFlowTests(TestCase):
    """记录录入流程测试。"""

    def setUp(self):
        """准备工作人员账号和一个可录入项目，便于验证表单提交流程。"""

        self.staff_group, _ = Group.objects.get_or_create(name=STAFF_GROUP)
        self.staff_user = User.objects.create_user(
            username="record_staff_user",
            password=_build_test_secret("record-staff"),
        )
        self.staff_user.groups.add(self.staff_group)
        self.client.force_login(self.staff_user)

        self.project = Project.objects.create(
            name="飞越地平线",
            project_type=Project.TYPE_VIEW,
            region=Project.REGION_VIEW,
            status=Project.STATUS_NORMAL,
            capacity=100,
            daily_warn_threshold=500,
            queue_count=18,
            cycle_minutes=8,
        )

    def test_record_new_creates_play_record_for_staff(self):
        """工作人员录入有效记录后，应成功落库并回到录入页。"""

        play_time = timezone.localtime().replace(second=0, microsecond=0)
        response = self.client.post(
            reverse("record_new"),
            {
                "project": self.project.id,
                "play_time": play_time.strftime("%Y-%m-%dT%H:%M"),
                "queue_time": 15,
                "repeat_count": 1,
                "status_snapshot": Project.STATUS_NORMAL,
                "note": "巡检验证用记录",
            },
        )

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response["Location"], reverse("record_new"))

        record = PlayRecord.objects.get(project=self.project)
        self.assertEqual(record.created_by, self.staff_user)
        self.assertEqual(record.queue_time, 15)
        self.assertEqual(record.repeat_count, 1)
