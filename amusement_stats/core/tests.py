"""核心模块测试：用于验证管理员端系统设置、行程模板管理等关键后台页面行为。"""

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from projects.models import Project
from visitor.models import ItineraryPlan, ItineraryPlanItem
from visitor.preferences import PREFERENCE_TAG_CHOICES

User = get_user_model()


def _build_test_secret(label: str) -> str:
    """为测试账号动态生成口令，避免把固定明文写进测试代码。"""

    return f"{label}-Core-Secret-2026!"


class ItineraryPlanManageViewTests(TestCase):
    """管理员端行程模板管理页面测试。"""

    def setUp(self):
        """构造管理员账号与两个模板，便于验证模板管理页只保留表单与节点列表。"""

        # 管理页受 admin_required 保护，因此测试需要显式登录管理员账号。
        self.admin_user = User.objects.create_superuser(
            username="admin_demo",
            email="admin@example.com",
            password=_build_test_secret("core-admin"),
        )
        self.client.force_login(self.admin_user)

        # 第一个模板放两个节点，用于验证模板列表仍能完整展示节点顺序和提示。
        self.project_with_coordinates = Project.objects.create(
            name="极速穿梭",
            project_type=Project.TYPE_THRILL,
            region=Project.REGION_THRILL,
            latitude=31.230111,
            longitude=121.500222,
        )
        self.project_without_coordinates = Project.objects.create(
            name="梦幻木马",
            project_type=Project.TYPE_FAMILY,
            region=Project.REGION_FAMILY,
        )

        # 第二个模板放独立节点，用于验证页面同时展示多个模板时仍保持清晰。
        self.project_for_other_plan = Project.objects.create(
            name="天空之眼",
            project_type=Project.TYPE_VIEW,
            region=Project.REGION_VIEW,
            latitude=31.238888,
            longitude=121.505666,
        )

        self.primary_plan = ItineraryPlan.objects.create(
            name="亲子轻松玩",
            audience=ItineraryPlan.AUDIENCE_FAMILY,
            preference_tag="亲子",
            description="上午优先体验亲子设施，减少高峰等待。",
            is_active=True,
        )
        ItineraryPlanItem.objects.create(
            plan=self.primary_plan,
            project=self.project_with_coordinates,
            seq=1,
            tip="开园后先冲热门刺激项目",
        )
        ItineraryPlanItem.objects.create(
            plan=self.primary_plan,
            project=self.project_without_coordinates,
            seq=2,
            tip="午前转场到亲子区",
        )

        self.secondary_plan = ItineraryPlan.objects.create(
            name="观光慢游线",
            audience=ItineraryPlan.AUDIENCE_ADULT,
            preference_tag="观光",
            description="适合拍照和轻松打卡。",
            is_active=True,
        )
        ItineraryPlanItem.objects.create(
            plan=self.secondary_plan,
            project=self.project_for_other_plan,
            seq=1,
            tip="先到高点拍照",
        )

    def test_manage_page_lists_plan_items_without_map_preview(self):
        """管理页应只展示模板与节点信息，不再提供地图预览数据或提示。"""

        response = self.client.get(reverse("itinerary_plan_manage"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.primary_plan.name)
        self.assertContains(response, self.secondary_plan.name)
        self.assertContains(response, "极速穿梭")
        self.assertContains(response, "梦幻木马")
        self.assertContains(response, "天空之眼")
        self.assertContains(response, "开园后先冲热门刺激项目")
        self.assertContains(response, "午前转场到亲子区")
        self.assertContains(response, "先到高点拍照")
        self.assertNotContains(response, "地图预览")
        self.assertNotContains(response, "当前模板独立预览")
        self.assertNotContains(response, "区域默认参考点")
        self.assertNotContains(response, "data-itinerary-preview-map")
        self.assertNotContains(response, "data-itinerary-preview-rows")
        self.assertNotIn("plan_cards", response.context)
        self.assertNotIn("map_default_lat", response.context)
        self.assertNotIn("map_default_lng", response.context)

    def test_manage_page_limits_plan_preference_to_fixed_choices(self):
        """管理端新增行程模板时，偏好标签只能从系统标签中选择。"""

        response = self.client.get(reverse("itinerary_plan_manage"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'id="createPlanPreference"')
        self.assertContains(response, 'name="preference_tag"')
        self.assertNotContains(response, 'type="text" name="preference_tag"')
        self.assertContains(response, 'name="preference_tag"', count=1)
        self.assertGreaterEqual(len(response.context["preference_tag_choices"]), 16)
        self.assertEqual(tuple(response.context["preference_tag_choices"]), PREFERENCE_TAG_CHOICES)

    def test_create_plan_filters_custom_preference_tag(self):
        """管理端恶意提交自定义偏好标签时，不应保存非法标签。"""

        response = self.client.post(
            reverse("itinerary_plan_manage"),
            {
                "op": "create_plan",
                "name": "非法标签测试路线",
                "audience": ItineraryPlan.AUDIENCE_FAMILY,
                "preference_tag": "自定义非法标签",
                "description": "应过滤非法偏好标签",
            },
        )

        self.assertEqual(response.status_code, 302)
        plan = ItineraryPlan.objects.get(name="非法标签测试路线")
        self.assertEqual(plan.preference_tag, "")
