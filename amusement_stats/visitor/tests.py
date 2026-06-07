"""游客端测试：用于验证游客端行程规划、账户中心等面对最终用户的关键页面行为。"""

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from accounts.models import VisitorProfile
from projects.models import Project
from visitor.models import ItineraryPlan, ItineraryPlanItem

User = get_user_model()


def _build_test_secret(label: str) -> str:
    """为测试账号动态生成口令，避免把固定明文写进测试代码。"""

    return f"{label}-Visitor-Secret-2026!"


class VisitorItineraryViewTests(TestCase):
    """游客端行程规划页面测试。"""

    def setUp(self):
        """构造两个模板，便于验证游客端仅展示推荐信息与节点顺序。"""

        # 第一个模板放两个项目，用于验证列表页和详情页都能展示节点顺序。
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

    def test_itinerary_list_only_shows_plan_summary_without_map_preview(self):
        """列表页应只展示模板摘要与节点预览，不再输出地图预览数据和提示。"""

        response = self.client.get(reverse("visitor_itinerary"))

        self.assertEqual(response.status_code, 200)
        plan_cards = response.context["plan_cards"]
        self.assertEqual(len(plan_cards), 2)

        primary_card = next(card for card in plan_cards if card["plan"].id == self.primary_plan.id)
        secondary_card = next(card for card in plan_cards if card["plan"].id == self.secondary_plan.id)

        self.assertEqual(len(primary_card["items"]), 2)
        self.assertEqual(len(primary_card["preview_items"]), 2)
        self.assertEqual(len(secondary_card["items"]), 1)
        self.assertEqual([item.project.name for item in primary_card["preview_items"]], ["极速穿梭", "梦幻木马"])
        self.assertNotIn("map_rows", primary_card)
        self.assertNotIn("map_rows_json", primary_card)
        self.assertNotIn("fallback_count", primary_card)
        self.assertNotIn("map_id", primary_card)

        self.assertContains(response, self.primary_plan.name)
        self.assertContains(response, self.secondary_plan.name)
        self.assertContains(response, "前 3 个项目预览")
        self.assertNotContains(response, "地图预览")
        self.assertNotContains(response, "当前模板独立预览")
        self.assertNotContains(response, "区域默认参考点")
        self.assertNotContains(response, "data-itinerary-preview-map")
        self.assertNotContains(response, "data-itinerary-preview-rows")
        self.assertNotContains(response, "leaflet")
        self.assertNotIn("map_default_lat", response.context)
        self.assertNotIn("map_default_lng", response.context)

    def test_itinerary_detail_only_shows_steps_without_map_preview(self):
        """详情页应只展示模板说明与游玩顺序，不再渲染地图容器和地图脚本。"""

        response = self.client.get(reverse("visitor_itinerary_detail", args=[self.primary_plan.id]))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.primary_plan.name)
        self.assertContains(response, self.primary_plan.description)
        self.assertContains(response, "设施游玩顺序")
        self.assertContains(response, "极速穿梭")
        self.assertContains(response, "梦幻木马")
        self.assertContains(response, "开园后先冲热门刺激项目")
        self.assertContains(response, "午前转场到亲子区")
        self.assertNotContains(response, "行程地图预览")
        self.assertNotContains(response, "节点 + 顺序连线 + 方向箭头")
        self.assertNotContains(response, "区域默认参考点")
        self.assertNotContains(response, "visitor-itinerary-map")
        self.assertNotContains(response, "leaflet")
        self.assertNotIn("map_rows_json", response.context)
        self.assertNotIn("map_default_lat", response.context)
        self.assertNotIn("map_default_lng", response.context)
        self.assertNotIn("fallback_count", response.context)


class VisitorAccountViewTests(TestCase):
    """游客端个人中心测试。"""

    def setUp(self):
        """创建已登录游客账号，便于验证账户页两个表单彼此隔离。"""

        self.old_password = _build_test_secret("visitor-old")
        self.user = User.objects.create_user(
            username="visitor_demo",
            email="visitor@example.com",
            password=self.old_password,
        )
        self.other_user = User.objects.create_user(
            username="existing_account",
            email="other@example.com",
            password=_build_test_secret("visitor-other"),
        )
        self.client.force_login(self.user)

    def test_change_password_failure_only_binds_password_form_and_shows_field_error(self):
        """密码修改失败时，只应校验密码表单，并把字段级错误回显给用户。"""

        invalid_old_secret = _build_test_secret("visitor-invalid-old")
        new_secret = _build_test_secret("visitor-new-fail")

        response = self.client.post(
            reverse("visitor_account"),
            {
                "op": "change_password",
                "old_password": invalid_old_secret,
                "new_password1": new_secret,
                "new_password2": new_secret,
            },
        )

        self.assertEqual(response.status_code, 200)

        # 修改密码提交失败时，个人资料表单不应被同一份 POST 误绑并产生无关错误。
        profile_form = response.context["profile_form"]
        pwd_form = response.context["pwd_form"]
        self.assertFalse(profile_form.is_bound)
        self.assertEqual(profile_form.errors, {})
        self.assertTrue(pwd_form.is_bound)
        self.assertIn("old_password", pwd_form.errors)

        # 页面除了通用失败消息，还必须把密码字段的具体错误直接渲染出来。
        self.assertContains(response, "密码修改失败，请检查输入")
        self.assertContains(response, pwd_form.errors["old_password"][0])
        self.assertNotContains(response, "该账号已被使用。")

    def test_update_profile_failure_only_binds_profile_form_and_shows_field_error(self):
        """资料更新失败时，只应校验资料表单，并展示对应字段错误。"""

        response = self.client.post(
            reverse("visitor_account"),
            {
                "op": "update_profile",
                "account": self.other_user.username,
                "nickname": "测试昵称",
                "preference_tags": "夜场",
                "phone": "",
                "email": "new-visitor@example.com",
            },
        )

        self.assertEqual(response.status_code, 200)

        # 更新资料失败时，密码表单不应被错误绑定为“必填项全部缺失”的状态。
        profile_form = response.context["profile_form"]
        pwd_form = response.context["pwd_form"]
        self.assertTrue(profile_form.is_bound)
        self.assertIn("account", profile_form.errors)
        self.assertFalse(pwd_form.is_bound)
        self.assertEqual(pwd_form.errors, {})

        # 页面需要展示资料字段的具体错误，便于用户知道是账号重复而非系统异常。
        self.assertContains(response, "个人资料更新失败，请检查输入")
        self.assertContains(response, profile_form.errors["account"][0])

    def test_account_page_limits_preference_tags_to_fixed_choices(self):
        """个人资料页的偏好标签应只能从固定选项中多选，不能自由输入。"""

        response = self.client.get(reverse("visitor_account"))

        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, 'type="text" name="preference_tags"')
        self.assertContains(response, 'name="preference_tags"', count=10)
        self.assertContains(response, 'value="亲子"')
        self.assertContains(response, 'value="夜场"')
        self.assertContains(response, 'value="长者友好"')

    def test_update_profile_filters_custom_preference_tags(self):
        """恶意提交自定义偏好标签时，只保存系统允许的标签。"""

        response = self.client.post(
            reverse("visitor_account"),
            {
                "op": "update_profile",
                "account": self.user.username,
                "nickname": "推荐标签测试",
                "preference_tags": ["亲子", "非法自定义标签", "夜场"],
                "age_group": "family",
                "consumption_level": "medium",
                "available_minutes": "180",
                "budget_amount": "0",
                "email": "profile-tags@example.com",
            },
        )

        self.assertEqual(response.status_code, 302)
        profile = self.user.visitor_profile
        profile.refresh_from_db()
        self.assertEqual(profile.preference_tags, "亲子,夜场")

    def test_change_password_success_keeps_login_state_and_allows_new_password_login(self):
        """密码修改成功后，应保持当前登录态，并且只允许新密码继续登录。"""

        updated_secret = _build_test_secret("visitor-updated")

        response = self.client.post(
            reverse("visitor_account"),
            {
                "op": "change_password",
                "old_password": self.old_password,
                "new_password1": updated_secret,
                "new_password2": updated_secret,
            },
            follow=True,
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "密码已更新")

        # 成功改密后，请求链最终仍应能访问需要登录的个人中心页面，证明会话未丢失。
        self.assertEqual(int(self.client.session.get("_auth_user_id")), self.user.id)

        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password(updated_secret))
        self.assertFalse(self.user.check_password(self.old_password))

        # 退出后旧密码应无法重新登录，而新密码可以正常登录，证明密码确实完成切换。
        self.client.logout()
        self.assertFalse(self.client.login(username=self.user.username, password=self.old_password))
        self.assertTrue(self.client.login(username=self.user.username, password=updated_secret))


class VisitorFavoritesAndFeedbackFlowTests(TestCase):
    """游客收藏与反馈流程测试。"""

    def setUp(self):
        """创建登录游客、项目与初始反馈数据，便于验证收藏和反馈闭环。"""

        self.password = _build_test_secret("visitor-flow")
        self.user = User.objects.create_user(
            username="visitor_flow_demo",
            email="visitor-flow@example.com",
            password=self.password,
        )
        self.client.force_login(self.user)

        self.project = Project.objects.create(
            name="梦境巡游",
            project_type=Project.TYPE_FAMILY,
            region=Project.REGION_FAMILY,
            status=Project.STATUS_NORMAL,
            capacity=35,
            daily_warn_threshold=180,
            queue_count=9,
            cycle_minutes=5,
        )

    def test_toggle_favorite_adds_item_and_redirects_back(self):
        """游客收藏项目后，应成功落库并按 next 参数返回原页面。"""

        response = self.client.post(
            reverse("visitor_favorite_toggle"),
            {
                "project_id": self.project.id,
                "next": reverse("visitor_favorites"),
            },
        )

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response["Location"], reverse("visitor_favorites"))
        self.assertTrue(self.user.visitor_favorites.filter(project=self.project).exists())

        favorites_response = self.client.get(reverse("visitor_favorites"))
        self.assertEqual(favorites_response.status_code, 200)
        self.assertContains(favorites_response, self.project.name)

    def test_feedback_flow_creates_session_and_follow_up_message(self):
        """游客提交反馈并继续追问时，应形成一条反馈会话和两条消息。"""

        create_response = self.client.post(
            reverse("visitor_feedback"),
            {
                "op": "new_feedback",
                "title": "排队提示建议",
                "content": "希望项目列表中展示更醒目的等待时间提示。",
                "contact": "visitor-flow@example.com",
            },
        )

        self.assertEqual(create_response.status_code, 302)
        self.assertEqual(create_response["Location"], reverse("visitor_feedback"))

        feedback = self.user.visitor_feedbacks.get()
        self.assertEqual(feedback.messages.count(), 1)
        self.assertEqual(feedback.messages.first().sender, "visitor")

        reply_response = self.client.post(
            reverse("visitor_feedback"),
            {
                "op": "reply",
                "feedback_id": feedback.id,
                "content": "补充一下，最好在首页热门榜也能看到排队趋势。",
            },
        )

        self.assertEqual(reply_response.status_code, 302)
        self.assertEqual(reply_response["Location"], reverse("visitor_feedback"))
        feedback.refresh_from_db()
        self.assertEqual(feedback.messages.count(), 2)
        self.assertEqual(feedback.status, feedback.STATUS_PENDING)


class VisitorRecommendationServiceTests(TestCase):
    def setUp(self):
        self.family_project = Project.objects.create(
            name="Recommendation Family Ride",
            project_type=Project.TYPE_FAMILY,
            region=Project.REGION_FAMILY,
            status=Project.STATUS_NORMAL,
            capacity=40,
            queue_count=3,
            latitude=31.230000,
            longitude=121.500000,
        )
        self.thrill_project = Project.objects.create(
            name="Recommendation Thrill Ride",
            project_type=Project.TYPE_THRILL,
            region=Project.REGION_THRILL,
            status=Project.STATUS_NORMAL,
            capacity=40,
            queue_count=18,
            latitude=31.231000,
            longitude=121.501000,
        )
        self.closed_project = Project.objects.create(
            name="Recommendation Closed Ride",
            project_type=Project.TYPE_FAMILY,
            region=Project.REGION_FAMILY,
            status=Project.STATUS_CLOSED,
            capacity=40,
            queue_count=1,
        )

    def test_recommendations_filter_closed_projects_and_prioritize_family_low_queue(self):
        from analytics.services.recommendations import build_recommendations

        result = build_recommendations(
            {
                "age_group": "family",
                "preference_tags": "family,low_queue",
                "budget_level": "medium",
                "available_minutes": 120,
                "with_children": True,
                "with_elderly": False,
            }
        )

        route_ids = [item["project_id"] for item in result["route"]["items"]]
        self.assertIn(self.family_project.id, route_ids)
        self.assertNotIn(self.closed_project.id, route_ids)
        self.assertEqual(result["avoid_peak"][0]["project_id"], self.family_project.id)
        self.assertGreaterEqual(len(result["combos"]), 1)
        self.assertIn("profile_score", result["route"]["items"][0])
        self.assertTrue(any(combo["name"] == "亲子轻松组合" for combo in result["combos"]))

    def test_recommendations_use_age_budget_and_elderly_profile(self):
        from analytics.services.recommendations import build_recommendations

        result = build_recommendations(
            {
                "age_group": "senior",
                "preference_tags": "view,low_queue",
                "budget_level": "low",
                "budget_amount": 80,
                "available_minutes": 70,
                "with_children": False,
                "with_elderly": True,
            }
        )

        self.assertLessEqual(len(result["route"]["items"]), 2)
        self.assertTrue(result["combos"])
        self.assertTrue(any("长者" in combo["name"] or "休闲" in combo["name"] for combo in result["combos"]))
        self.assertIn("budget_score", result["avoid_peak"][0])


class VisitorRecommendationViewTests(TestCase):
    def setUp(self):
        self.password = _build_test_secret("visitor-recommend")
        self.user = User.objects.create_user(username="visitor_recommend_user", password=self.password)
        self.client.force_login(self.user)

    def test_recommendation_page_limits_preference_tags_to_fixed_choices(self):
        response = self.client.get(reverse("visitor_recommendations"))

        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, 'id="preference_tags" name="preference_tags"')
        self.assertContains(response, 'name="preference_tags"', count=10)
        self.assertContains(response, 'value="亲子"')
        self.assertContains(response, 'value="刺激"')
        self.assertContains(response, 'value="观光"')
        self.assertContains(response, 'value="低排队"')
        self.assertContains(response, 'value="夜场"')
        self.assertContains(response, 'value="长者友好"')

    def test_recommendation_post_filters_custom_preference_tags(self):
        response = self.client.post(
            reverse("visitor_recommendations"),
            {
                "age_group": VisitorProfile.AGE_FAMILY,
                "preference_tags": ["亲子", "非法自定义标签", "低排队"],
                "budget_level": VisitorProfile.CONSUMPTION_MEDIUM,
                "available_minutes": "180",
                "budget_amount": "0",
                "with_children": "on",
            },
        )

        self.assertEqual(response.status_code, 200)
        profile = VisitorProfile.objects.get(user=self.user)
        self.assertEqual(profile.preference_tags, "亲子,低排队")
        self.assertEqual(response.context["profile_data"]["preference_tags"], "亲子,低排队")
        self.assertEqual(response.context["selected_preference_tags"], ["亲子", "低排队"])


class VisitorProjectDetailRecommendationTests(TestCase):
    def test_project_detail_shows_similar_low_queue_projects(self):
        current = Project.objects.create(
            name="Busy Family Ride",
            project_type=Project.TYPE_FAMILY,
            queue_count=28,
            capacity=30,
        )
        alternative = Project.objects.create(
            name="Quiet Family Ride",
            project_type=Project.TYPE_FAMILY,
            queue_count=2,
            capacity=30,
        )
        Project.objects.create(
            name="Closed Alternative",
            project_type=Project.TYPE_FAMILY,
            queue_count=0,
            capacity=30,
            status=Project.STATUS_CLOSED,
        )

        response = self.client.get(reverse("visitor_project_detail", args=[current.id]))

        self.assertContains(response, "相似低排队项目")
        self.assertContains(response, alternative.name)
        self.assertNotContains(response, "Closed Alternative")


class VisitorMapHeatPayloadTests(TestCase):
    def test_visitor_map_contains_heat_radiation_payload(self):
        Project.objects.create(
            name="Map Heat Ride",
            project_type=Project.TYPE_VIEW,
            queue_count=6,
            capacity=30,
            latitude=31.230000,
            longitude=121.470000,
        )

        response = self.client.get(reverse("visitor_map"))

        self.assertContains(response, "visitorMapHeatData")
        self.assertContains(response, "mapHeatDetail")


class VisitorProjectPreviewImageTests(TestCase):
    def test_project_list_uses_type_specific_preview_images_when_cover_is_missing(self):
        Project.objects.create(name="Preview Thrill Ride", project_type=Project.TYPE_THRILL)
        Project.objects.create(name="Preview Family Ride", project_type=Project.TYPE_FAMILY)
        Project.objects.create(name="Preview View Ride", project_type=Project.TYPE_VIEW)

        response = self.client.get(reverse("visitor_project_list"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "img/project-previews/thrill.svg")
        self.assertContains(response, "img/project-previews/family.svg")
        self.assertContains(response, "img/project-previews/view.svg")
        self.assertNotContains(response, "img/project-placeholder.svg")

    def test_project_detail_uses_type_specific_preview_image_with_project_alt_text(self):
        project = Project.objects.create(name="Preview Detail Wheel", project_type=Project.TYPE_VIEW)

        response = self.client.get(reverse("visitor_project_detail", args=[project.id]))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "img/project-previews/view.svg")
        self.assertContains(response, 'alt="Preview Detail Wheel"')
        self.assertNotContains(response, "img/project-placeholder.svg")
