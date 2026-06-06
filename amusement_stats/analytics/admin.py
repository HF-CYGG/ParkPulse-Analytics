from django.contrib import admin

from .models import (
    ForecastEvaluation,
    HolidayCalendar,
    MaintenanceWorkOrder,
    ProjectForecast,
    ProjectHeatSnapshot,
    ProjectIncident,
    ProjectReview,
    PromotionEvent,
    ServiceFacility,
)


@admin.register(ProjectHeatSnapshot)
class ProjectHeatSnapshotAdmin(admin.ModelAdmin):
    list_display = ("project", "snapshot_time", "score", "base_score", "time_score", "updated_at")
    list_filter = ("project", "snapshot_time")
    search_fields = ("project__name",)


@admin.register(ProjectForecast)
class ProjectForecastAdmin(admin.ModelAdmin):
    list_display = ("project", "target_time", "model_name", "predicted_score", "predicted_visits", "alert_level")
    list_filter = ("model_name", "alert_level", "target_time")
    search_fields = ("project__name", "warning")


@admin.register(ForecastEvaluation)
class ForecastEvaluationAdmin(admin.ModelAdmin):
    list_display = ("project", "model_name", "mae", "mse", "r2", "evaluated_at")
    list_filter = ("model_name", "evaluated_at")
    search_fields = ("project__name",)


@admin.register(ProjectReview)
class ProjectReviewAdmin(admin.ModelAdmin):
    list_display = ("project", "user", "rating", "created_at")
    list_filter = ("rating", "created_at")
    search_fields = ("project__name", "comment", "user__username")


@admin.register(ProjectIncident)
class ProjectIncidentAdmin(admin.ModelAdmin):
    list_display = ("project", "incident_type", "severity", "status", "handled_by", "started_at", "ended_at", "downtime_minutes")
    list_filter = ("incident_type", "severity", "status", "started_at")
    search_fields = ("project__name", "description")


@admin.register(MaintenanceWorkOrder)
class MaintenanceWorkOrderAdmin(admin.ModelAdmin):
    list_display = ("project", "incident", "status", "handled_by", "started_at", "ended_at")
    list_filter = ("status", "started_at")
    search_fields = ("project__name", "notes")


@admin.register(ServiceFacility)
class ServiceFacilityAdmin(admin.ModelAdmin):
    list_display = ("name", "facility_type", "region", "is_active")
    list_filter = ("facility_type", "region", "is_active")
    search_fields = ("name",)


@admin.register(HolidayCalendar)
class HolidayCalendarAdmin(admin.ModelAdmin):
    list_display = ("date", "name", "day_type", "heat_multiplier")
    list_filter = ("day_type",)
    search_fields = ("name",)


@admin.register(PromotionEvent)
class PromotionEventAdmin(admin.ModelAdmin):
    list_display = ("name", "start_date", "end_date", "heat_multiplier", "is_active")
    list_filter = ("is_active", "start_date", "end_date")
    search_fields = ("name", "description")
