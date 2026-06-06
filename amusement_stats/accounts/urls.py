from django.urls import path

from . import views

urlpatterns = [
    path("accounts/post-login/", views.login_redirect, name="login_redirect"),
    path("staff/", views.staff_workbench, name="staff_workbench"),
    path("staff/api/project-queues/", views.staff_project_queues_api, name="staff_project_queues_api"),
    path("accounts/users/", views.user_role_manage, name="user_role_manage"),
]

