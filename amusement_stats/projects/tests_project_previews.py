from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.test import TestCase
from django.urls import reverse

from core.auth_utils import STAFF_GROUP
from projects.models import Project

User = get_user_model()


class ProjectPreviewImageTests(TestCase):
    def setUp(self):
        staff_group, _ = Group.objects.get_or_create(name=STAFF_GROUP)
        self.staff_user = User.objects.create_user(
            username="project_preview_staff",
            password="Project-Preview-Secret-2026!",
        )
        self.staff_user.groups.add(staff_group)
        self.client.force_login(self.staff_user)

    def test_project_list_uses_type_specific_preview_image_for_missing_cover(self):
        Project.objects.create(name="Preview Admin Thrill", project_type=Project.TYPE_THRILL)

        response = self.client.get(reverse("project_list"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "img/project-previews/thrill.svg")
        self.assertNotContains(response, "img/project-placeholder.svg")
