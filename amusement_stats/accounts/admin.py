from django.contrib import admin

from .models import VisitorProfile


@admin.register(VisitorProfile)
class VisitorProfileAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "nickname", "phone", "preference_tags", "updated_at")
    search_fields = ("user__username", "nickname", "phone", "preference_tags")
