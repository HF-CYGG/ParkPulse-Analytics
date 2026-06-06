from django import forms
from django.utils import timezone

from projects.models import Project

from .models import PlayRecord


class PlayRecordForm(forms.ModelForm):
    class Meta:
        model = PlayRecord
        fields = ["project", "play_time", "queue_time", "repeat_count", "status_snapshot", "note"]
        widgets = {
            "project": forms.Select(attrs={"class": "form-select"}),
            "play_time": forms.DateTimeInput(attrs={"class": "form-control", "type": "datetime-local"}),
            "queue_time": forms.NumberInput(attrs={"class": "form-control", "min": 0}),
            "repeat_count": forms.NumberInput(attrs={"class": "form-control", "min": 0}),
            "status_snapshot": forms.Select(attrs={"class": "form-select"}),
            "note": forms.Textarea(attrs={"class": "form-control", "rows": 3, "placeholder": "填写异常、天气或活动备注"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["project"].queryset = Project.objects.exclude(status=Project.STATUS_CLOSED).order_by("name")
        if not self.initial.get("play_time"):
            self.initial["play_time"] = timezone.localtime().replace(second=0, microsecond=0).strftime("%Y-%m-%dT%H:%M")
