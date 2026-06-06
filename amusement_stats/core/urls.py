from django.urls import path

from . import views

urlpatterns = [
    path("settings/", views.system_management_home, name="system_management_home"),
    path("settings/ui/", views.system_settings, name="system_settings_ui"),
    path("settings/itinerary/", views.itinerary_plan_manage, name="itinerary_plan_manage"),
    path("audit/", views.audit_logs, name="audit_logs"),
    path("visitor-feedback/", views.visitor_feedback_manage, name="visitor_feedback_manage"),
    path("visitor-feedback/<int:feedback_id>/", views.visitor_feedback_detail, name="visitor_feedback_detail"),
]

