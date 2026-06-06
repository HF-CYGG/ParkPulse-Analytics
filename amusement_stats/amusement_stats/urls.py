"""
URL configuration for amusement_stats project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/6.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""

from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.contrib.auth import views as auth_views
from django.urls import path, include

from accounts.views import StaffLoginView
from dashboard.views import spatial_heat
from projects.views import queue_update_count_api

urlpatterns = [
    path("admin/", admin.site.urls),
    path(
        "login/",
        StaffLoginView.as_view(template_name="registration/login.html"),
        name="login",
    ),
    path("logout/", auth_views.LogoutView.as_view(), name="logout"),
    path("", include("dashboard.urls")),
    path("dashboard/spatial-heat/", spatial_heat, name="dashboard_spatial_heat_prefixed"),
    path("", include("core.urls")),
    path("", include("accounts.urls")),
    path("records/", include("records.urls")),
    path("projects/", include("projects.urls")),
    path("visitor/", include("visitor.urls")),
    path("analytics/", include("analytics.urls")),
    path("api/queue/project/<int:project_id>/update-count/", queue_update_count_api, name="queue_update_count_api"),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
