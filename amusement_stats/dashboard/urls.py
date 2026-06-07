from django.urls import path

from . import views

urlpatterns = [
    path("", views.index, name="index"),
    path("forecast/", views.forecast_dashboard, name="dashboard_forecast"),
    path("spatial-heat/", views.spatial_heat, name="dashboard_spatial_heat"),
    path("api/rank/", views.api_rank, name="api_rank"),
    path("api/hot_score/", views.api_hot_score, name="api_hot_score"),
    path("api/traffic/", views.api_traffic, name="api_traffic"),
    path("api/type_ratio/", views.api_type_ratio, name="api_type_ratio"),
    path("api/predict/", views.api_predict, name="api_predict"),
    path("api/region_heatmap/", views.api_region_heatmap, name="api_region_heatmap"),
    path("api/heat_decay/", views.api_heat_decay, name="api_heat_decay"),
    path("export/csv/", views.export_csv, name="dashboard_export_csv"),
    path("export/xlsx/", views.export_xlsx, name="dashboard_export_xlsx"),
    path("report/weekly/", views.weekly_report, name="dashboard_weekly_report"),
    path("report/weekly/xlsx/", views.export_weekly_xlsx, name="dashboard_weekly_xlsx"),
    path("report/weekly/html/", views.export_weekly_html, name="dashboard_weekly_brief_html"),
]

