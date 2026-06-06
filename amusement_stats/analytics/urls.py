from django.urls import path

from . import views

app_name = "analytics"

urlpatterns = [
    path("api/heat-score/", views.heat_score_api, name="heat_score_api"),
    path("api/forecast/", views.forecast_api, name="forecast_api"),
    path("api/forecast/heat/", views.forecast_api, name="forecast_heat_api"),
    path("api/forecast/alerts/", views.forecast_alerts_api, name="forecast_alerts_api"),
    path("api/forecast-evaluation/", views.forecast_evaluation_api, name="forecast_evaluation_api"),
    path("api/spatial-heat/", views.spatial_heat_api, name="spatial_heat_api"),
    path("api/heat/timeline/", views.heat_timeline_api, name="heat_timeline_api"),
    path("api/heat/spatial/", views.spatial_heat_api, name="heat_spatial_api"),
    path("api/heat/project/<int:project_id>/detail/", views.project_detail_api, name="heat_project_detail_api"),
    path("api/heat/project/<int:project_id>/forecast/", views.project_forecast_api, name="heat_project_forecast_api"),
    path("api/project-detail/<int:project_id>/", views.project_detail_api, name="project_detail_api"),
]
