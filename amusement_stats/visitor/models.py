from django.conf import settings
from django.db import models

from projects.models import Project


class VisitorFavorite(models.Model):
    """登录用户收藏的游乐项目（游园端）。"""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="visitor_favorites",
        verbose_name="用户",
    )
    project = models.ForeignKey(
        Project,
        on_delete=models.CASCADE,
        related_name="visitor_favorited_by",
        verbose_name="项目",
    )
    created_at = models.DateTimeField("收藏时间", auto_now_add=True)

    class Meta:
        verbose_name = "游园收藏"
        verbose_name_plural = "游园收藏"
        constraints = [
            models.UniqueConstraint(fields=["user", "project"], name="uniq_visitor_favorite_user_project"),
        ]
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.user_id} → {self.project_id}"


class VisitorFeedback(models.Model):
    """游园意见反馈（登录用户）。"""

    STATUS_PENDING = "pending"
    STATUS_RESOLVED = "resolved"
    STATUS_CHOICES = [
        (STATUS_PENDING, "待处理"),
        (STATUS_RESOLVED, "已处理"),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="visitor_feedbacks",
        verbose_name="用户",
    )
    title = models.CharField("标题", max_length=120, blank=True)
    content = models.TextField("内容")
    contact = models.CharField("联系方式（选填）", max_length=120, blank=True)
    created_at = models.DateTimeField("提交时间", auto_now_add=True)
    status = models.CharField(
        "处理状态",
        max_length=20,
        choices=STATUS_CHOICES,
        default=STATUS_PENDING,
        db_index=True,
    )
    resolved_at = models.DateTimeField("处理时间", null=True, blank=True)

    class Meta:
        verbose_name = "游园反馈"
        verbose_name_plural = "游园反馈"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.user_id} {self.created_at:%Y-%m-%d} {self.title or '（无标题）'}"


class VisitorFeedbackMessage(models.Model):
    SENDER_VISITOR = "visitor"
    SENDER_ADMIN = "admin"
    SENDER_CHOICES = [
        (SENDER_VISITOR, "游客"),
        (SENDER_ADMIN, "管理员"),
    ]

    feedback = models.ForeignKey(
        VisitorFeedback,
        on_delete=models.CASCADE,
        related_name="messages",
        verbose_name="反馈会话",
    )
    sender = models.CharField("发送方", max_length=20, choices=SENDER_CHOICES)
    content = models.TextField("消息内容")
    created_at = models.DateTimeField("发送时间", auto_now_add=True)
    read_by_visitor = models.BooleanField("游客已读", default=False)
    read_by_admin = models.BooleanField("管理员已读", default=False)

    class Meta:
        verbose_name = "反馈会话消息"
        verbose_name_plural = "反馈会话消息"
        ordering = ["created_at", "id"]

    def __str__(self):
        return f"{self.feedback_id} {self.sender} {self.created_at:%m-%d %H:%M}"


class ItineraryPlan(models.Model):
    AUDIENCE_FAMILY = "family"
    AUDIENCE_ADULT = "adult"
    AUDIENCE_TEEN = "teen"
    AUDIENCE_CHOICES = [
        (AUDIENCE_FAMILY, "亲子家庭"),
        (AUDIENCE_ADULT, "成人游客"),
        (AUDIENCE_TEEN, "青少年"),
    ]

    name = models.CharField("方案名称", max_length=120)
    audience = models.CharField("适用人群", max_length=20, choices=AUDIENCE_CHOICES, default=AUDIENCE_FAMILY)
    preference_tag = models.CharField("偏好标签", max_length=80, blank=True, default="")
    description = models.TextField("方案说明", blank=True, default="")
    is_active = models.BooleanField("启用", default=True)
    updated_at = models.DateTimeField("更新时间", auto_now=True)

    class Meta:
        verbose_name = "行程规划模板"
        verbose_name_plural = "行程规划模板"
        ordering = ["name"]

    def __str__(self):
        return self.name


class ItineraryPlanItem(models.Model):
    plan = models.ForeignKey(
        ItineraryPlan,
        on_delete=models.CASCADE,
        related_name="items",
        verbose_name="规划方案",
    )
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="+", verbose_name="项目")
    seq = models.PositiveIntegerField("顺序", default=1)
    tip = models.CharField("提示", max_length=200, blank=True, default="")

    class Meta:
        verbose_name = "行程规划项目"
        verbose_name_plural = "行程规划项目"
        ordering = ["seq", "id"]
        unique_together = ("plan", "seq")

    def __str__(self):
        return f"{self.plan_id}#{self.seq}:{self.project_id}"
