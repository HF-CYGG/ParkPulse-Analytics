from django.contrib import admin
from django.urls import reverse
from django.utils.html import format_html

from .models import (
    ItineraryPlan,
    ItineraryPlanItem,
    VisitorFavorite,
    VisitorFeedback,
    VisitorFeedbackMessage,
)


@admin.register(VisitorFavorite)
class VisitorFavoriteAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "project", "created_at")
    list_filter = ("created_at",)
    search_fields = ("user__username", "project__name")


@admin.register(VisitorFeedback)
class VisitorFeedbackAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "title", "status", "created_at", "content_preview", "reply_entry")
    list_filter = ("status", "created_at")
    search_fields = ("user__username", "title", "content", "contact")
    readonly_fields = ("user", "created_at", "reply_entry")

    @admin.display(description="内容摘要")
    def content_preview(self, obj):
        text = (obj.content or "")[:80]
        return text + ("..." if len(obj.content or "") > 80 else "")

    @admin.display(description="会话回复")
    def reply_entry(self, obj):
        url = reverse("visitor_feedback_detail", args=[obj.id])
        return format_html('<a class="button" href="{}">进入会话详情回复</a>', url)


@admin.register(VisitorFeedbackMessage)
class VisitorFeedbackMessageAdmin(admin.ModelAdmin):
    list_display = ("id", "feedback", "sender", "created_at", "read_by_visitor", "read_by_admin")
    list_filter = ("sender", "created_at", "read_by_visitor", "read_by_admin")
    search_fields = ("feedback__id", "content")


class ItineraryPlanItemInline(admin.TabularInline):
    model = ItineraryPlanItem
    extra = 1


@admin.register(ItineraryPlan)
class ItineraryPlanAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "audience", "preference_tag", "is_active", "updated_at")
    list_filter = ("audience", "is_active")
    search_fields = ("name", "preference_tag", "description")
    inlines = [ItineraryPlanItemInline]
