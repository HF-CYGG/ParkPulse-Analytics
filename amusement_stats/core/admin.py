from django.contrib import admin

from .models import AuditLog, SiteConfig


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ("id", "action", "actor", "target_type", "target_id", "created_at")
    list_filter = ("action", "created_at")
    search_fields = ("action", "target_type", "target_id", "message", "path")


@admin.register(SiteConfig)
class SiteConfigAdmin(admin.ModelAdmin):
    list_display = ("id", "operating_hours_text", "updated_at")
