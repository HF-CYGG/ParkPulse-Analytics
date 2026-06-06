"""账号模块测试：用于验证登录分流等核心用户入口流程是否保持可用。"""

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.test import TestCase
from django.urls import reverse

from core.auth_utils import ADMIN_GROUP, STAFF_GROUP

User = get_user_model()


def _build_test_secret(label: str) -> str:
    """为测试账号动态生成口令，避免把固定明文写进测试代码。"""

    return f"{label}-Flow-Secret-2026!"


class StaffLoginFlowTests(TestCase):
    """登录分流测试。"""

    def setUp(self):
        """创建三类账号，验证登录成功后的首跳是否符合角色预期。"""

        self.password = _build_test_secret("login-flow")
        self.staff_group, _ = Group.objects.get_or_create(name=STAFF_GROUP)
        self.admin_group, _ = Group.objects.get_or_create(name=ADMIN_GROUP)

        self.visitor_user = User.objects.create_user(
            username="visitor_flow_user",
            password=self.password,
        )
        self.staff_user = User.objects.create_user(
            username="staff_flow_user",
            password=self.password,
        )
        self.staff_user.groups.add(self.staff_group)

        self.admin_user = User.objects.create_user(
            username="admin_flow_user",
            password=self.password,
        )
        self.admin_user.groups.add(self.admin_group)

    def test_login_redirects_visitor_to_visitor_index(self):
        """普通用户登录后应进入游客首页，而不是误入后台页面。"""

        response = self.client.post(
            reverse("login"),
            {"username": self.visitor_user.username, "password": self.password},
        )

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response["Location"], reverse("visitor_index"))

    def test_login_redirects_staff_to_staff_workbench(self):
        """工作人员登录后应进入工作台。"""

        response = self.client.post(
            reverse("login"),
            {"username": self.staff_user.username, "password": self.password},
        )

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response["Location"], reverse("staff_workbench"))

    def test_login_redirects_admin_to_dashboard(self):
        """管理员登录后应进入经营看板首页。"""

        response = self.client.post(
            reverse("login"),
            {"username": self.admin_user.username, "password": self.password},
        )

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response["Location"], reverse("index"))
