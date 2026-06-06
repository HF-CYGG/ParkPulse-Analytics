from django import forms
from django.contrib.auth import get_user_model

from accounts.models import VisitorProfile
from .models import VisitorFeedback, VisitorFeedbackMessage


User = get_user_model()


class FeedbackForm(forms.ModelForm):
    class Meta:
        model = VisitorFeedback
        fields = ["title", "content", "contact"]
        widgets = {
            "title": forms.TextInput(attrs={"class": "form-control", "placeholder": "简要说明（选填）"}),
            "content": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 4,
                    "placeholder": "请描述你的建议或遇到的问题",
                }
            ),
            "contact": forms.TextInput(attrs={"class": "form-control", "placeholder": "手机号 / 邮箱（选填，便于回访）"}),
        }
        labels = {
            "title": "标题",
            "content": "反馈内容",
            "contact": "联系方式",
        }


class FeedbackReplyForm(forms.ModelForm):
    class Meta:
        model = VisitorFeedbackMessage
        fields = ["content"]
        widgets = {
            "content": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 3,
                    "placeholder": "请输入回复内容",
                }
            ),
        }
        labels = {"content": "消息"}


class VisitorProfileForm(forms.ModelForm):
    account = forms.CharField(
        required=True,
        label="账号",
        widget=forms.TextInput(attrs={"class": "form-control", "placeholder": "登录账号"}),
    )
    email = forms.EmailField(
        required=False,
        label="邮箱",
        widget=forms.EmailInput(attrs={"class": "form-control", "placeholder": "name@example.com"}),
    )
    phone = forms.CharField(
        required=False,
        label="手机号",
        widget=forms.TextInput(attrs={"class": "form-control", "placeholder": "手机号"}),
    )

    class Meta:
        model = VisitorProfile
        fields = [
            "nickname",
            "phone",
            "preference_tags",
            "age_group",
            "consumption_level",
            "available_minutes",
            "budget_amount",
            "with_children",
            "with_elderly",
        ]
        widgets = {
            "nickname": forms.TextInput(attrs={"class": "form-control", "placeholder": "显示昵称"}),
            "phone": forms.TextInput(attrs={"class": "form-control", "placeholder": "手机号"}),
            "preference_tags": forms.TextInput(
                attrs={"class": "form-control", "placeholder": "例如：亲子，低刺激，夜场"}
            ),
            "age_group": forms.Select(attrs={"class": "form-select"}),
            "consumption_level": forms.Select(attrs={"class": "form-select"}),
            "available_minutes": forms.NumberInput(attrs={"class": "form-control", "min": 30, "step": 15}),
            "budget_amount": forms.NumberInput(attrs={"class": "form-control", "min": 0, "step": 10}),
            "with_children": forms.CheckboxInput(attrs={"class": "form-check-input"}),
            "with_elderly": forms.CheckboxInput(attrs={"class": "form-check-input"}),
        }
        labels = {
            "nickname": "昵称",
            "phone": "手机号",
            "preference_tags": "偏好标签",
            "age_group": "年龄段",
            "consumption_level": "消费层级",
            "available_minutes": "可游玩时长(分钟)",
            "budget_amount": "预算(元)",
            "with_children": "带儿童",
            "with_elderly": "带老人",
        }

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop("user", None)
        super().__init__(*args, **kwargs)
        for name in [
            "age_group",
            "consumption_level",
            "available_minutes",
            "budget_amount",
            "with_children",
            "with_elderly",
        ]:
            self.fields[name].required = False

    def clean_account(self):
        value = self.cleaned_data["account"].strip()
        if not value:
            raise forms.ValidationError("账号不能为空。")
        qs = User.objects.filter(username__iexact=value)
        if self.user:
            qs = qs.exclude(id=self.user.id)
        if qs.exists():
            raise forms.ValidationError("该账号已被使用。")
        return value

    def clean_email(self):
        value = (self.cleaned_data.get("email") or "").strip()
        if not value:
            return ""
        qs = User.objects.filter(email__iexact=value)
        if self.user:
            qs = qs.exclude(id=self.user.id)
        if qs.exists():
            raise forms.ValidationError("该邮箱已被使用。")
        return value

    def clean_nickname(self):
        value = (self.cleaned_data.get("nickname") or "").strip()
        if not value:
            return None
        qs = VisitorProfile.objects.filter(nickname__iexact=value)
        if self.instance and self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise forms.ValidationError("该昵称已被使用。")
        return value

    def clean_phone(self):
        value = (self.cleaned_data.get("phone") or "").strip()
        if not value:
            return None
        if not value.replace("+", "").isdigit():
            raise forms.ValidationError("手机号格式不正确。")
        qs = VisitorProfile.objects.filter(phone=value)
        if self.instance and self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise forms.ValidationError("该手机号已被使用。")
        return value

    def clean_age_group(self):
        return self.cleaned_data.get("age_group") or VisitorProfile.AGE_ADULT

    def clean_consumption_level(self):
        return self.cleaned_data.get("consumption_level") or VisitorProfile.CONSUMPTION_MEDIUM

    def clean_available_minutes(self):
        return self.cleaned_data.get("available_minutes") or 180

    def clean_budget_amount(self):
        return self.cleaned_data.get("budget_amount") or 0
