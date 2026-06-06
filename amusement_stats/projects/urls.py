from django.urls import path

from . import views

urlpatterns = [
    path("", views.project_list, name="project_list"),
    path("<int:project_id>/edit/", views.project_edit, name="project_edit"),
    path("<int:project_id>/delete/", views.project_delete, name="project_delete"),
    path("<int:project_id>/toggle-status/", views.project_toggle_status, name="project_toggle_status"),
]

