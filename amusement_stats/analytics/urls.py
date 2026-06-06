from django.urls import path

from . import views

app_name = "analytics"

urlpatterns = [
    path("api/heat-score/", views.heat_score_api, name="heat_score_api"),
    path("api/forecast/", views.forecast_api, name="forecast_api"),
    path("api/forecast-evaluation/", views.forecast_evaluation_api, name="forecast_evaluation_api"),
    path("api/spatial-heat/", views.spatial_heat_api, name="spatial_heat_api"),
    path("api/project-detail/<int:project_id>/", views.project_detail_api, name="project_detail_api"),
]
