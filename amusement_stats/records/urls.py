from django.urls import path

from . import views

urlpatterns = [
    path("new/", views.record_new, name="record_new"),
    path("import/", views.record_import, name="record_import"),
    path("import/template.csv", views.record_import_template_csv, name="record_import_template_csv"),
    path("<int:record_id>/edit/", views.record_edit, name="record_edit"),
    path("<int:record_id>/delete/", views.record_delete, name="record_delete"),
]

