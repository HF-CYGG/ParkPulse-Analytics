from django import forms

from .models import Project


class ProjectCreateForm(forms.ModelForm):
    """列表页快速新建（不含封面与坐标，避免 multipart 复杂度）。"""

    class Meta:
        model = Project
        fields = [
            "name",
            "project_type",
            "region",
            "status",
            "capacity",
            "daily_warn_threshold",
            "queue_count",
            "cycle_minutes",
            "operating_hours_text",
        ]
        widgets = {
            "name": forms.TextInput(attrs={"class": "form-control", "placeholder": "例如：过山车"}),
            "project_type": forms.Select(attrs={"class": "form-select"}),
            "region": forms.Select(attrs={"class": "form-select"}),
            "status": forms.Select(attrs={"class": "form-select"}),
            "capacity": forms.NumberInput(attrs={"class": "form-control", "min": 1}),
            "daily_warn_threshold": forms.NumberInput(attrs={"class": "form-control", "min": 1}),
            "queue_count": forms.NumberInput(attrs={"class": "form-control", "min": 0}),
            "cycle_minutes": forms.NumberInput(attrs={"class": "form-control", "min": 1}),
            "operating_hours_text": forms.TextInput(
                attrs={"class": "form-control", "placeholder": "例如：10:00-21:00"}
            ),
        }


class ProjectForm(forms.ModelForm):
    """编辑页：含简介、封面、地图坐标。"""

    class Meta:
        model = Project
        fields = [
            "name",
            "project_type",
            "region",
            "status",
            "capacity",
            "daily_warn_threshold",
            "queue_count",
            "cycle_minutes",
            "operating_hours_text",
            "short_description",
            "cover_image",
            "latitude",
            "longitude",
        ]
        widgets = {
            "name": forms.TextInput(attrs={"class": "form-control"}),
            "project_type": forms.Select(attrs={"class": "form-select"}),
            "region": forms.Select(attrs={"class": "form-select"}),
            "status": forms.Select(attrs={"class": "form-select"}),
            "capacity": forms.NumberInput(attrs={"class": "form-control", "min": 1}),
            "daily_warn_threshold": forms.NumberInput(attrs={"class": "form-control", "min": 1}),
            "queue_count": forms.NumberInput(attrs={"class": "form-control", "min": 0}),
            "cycle_minutes": forms.NumberInput(attrs={"class": "form-control", "min": 1}),
            "operating_hours_text": forms.TextInput(
                attrs={"class": "form-control", "placeholder": "例如：10:00-21:00"}
            ),
            "short_description": forms.Textarea(attrs={"rows": 3, "class": "form-control"}),
            "cover_image": forms.ClearableFileInput(attrs={"class": "form-control"}),
            "latitude": forms.NumberInput(
                attrs={"class": "form-control", "step": "any", "placeholder": "例如 31.240000"}
            ),
            "longitude": forms.NumberInput(
                attrs={"class": "form-control", "step": "any", "placeholder": "例如 121.470000"}
            ),
        }

