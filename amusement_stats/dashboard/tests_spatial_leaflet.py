from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.test import TestCase
from django.urls import reverse

from core.auth_utils import ADMIN_GROUP
from projects.models import Project

User = get_user_model()


class SpatialHeatLeafletMapTests(TestCase):
    def setUp(self):
        admin_group, _ = Group.objects.get_or_create(name=ADMIN_GROUP)
        self.admin_user = User.objects.create_user(
            username="spatial_leaflet_admin",
            password="Spatial-Leaflet-Secret-2026!",
        )
        self.admin_user.groups.add(admin_group)
        self.client.force_login(self.admin_user)
        Project.objects.create(
            name="Spatial Leaflet Ride",
            project_type=Project.TYPE_VIEW,
            region=Project.REGION_VIEW,
            latitude=31.2384,
            longitude=121.4778,
        )

    def test_spatial_heat_page_uses_shared_leaflet_tile_map(self):
        response = self.client.get(reverse("dashboard_spatial_heat"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "spatialHeatData")
        self.assertContains(response, "spatialHeatCanvas")
        self.assertContains(response, "vendor/leaflet/leaflet.css")
        self.assertContains(response, "vendor/leaflet/leaflet.js")
        self.assertContains(response, "webrd0{s}.is.autonavi.com")
        self.assertContains(response, "OpenStreetMap")
        self.assertContains(response, "L.control.layers")
        self.assertContains(response, "L.circle")
        self.assertContains(response, "L.marker")
        self.assertNotContains(response, "spatial-map-viewport")
        self.assertNotContains(response, "data-map-x")
        self.assertNotContains(response, "data-map-y")
