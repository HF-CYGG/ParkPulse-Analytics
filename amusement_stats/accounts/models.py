from django.db import models
from django.db.models import Q
from django.conf import settings


class VisitorProfile(models.Model):
    AGE_CHILD = "child"
    AGE_TEEN = "teen"
    AGE_ADULT = "adult"
    AGE_SENIOR = "senior"
    AGE_FAMILY = "family"
    AGE_CHOICES = [
        (AGE_CHILD, "儿童"),
        (AGE_TEEN, "青少年"),
        (AGE_ADULT, "成人"),
        (AGE_SENIOR, "长者"),
        (AGE_FAMILY, "亲子家庭"),
    ]

    CONSUMPTION_LOW = "low"
    CONSUMPTION_MEDIUM = "medium"
    CONSUMPTION_HIGH = "high"
    CONSUMPTION_CHOICES = [
        (CONSUMPTION_LOW, "经济"),
        (CONSUMPTION_MEDIUM, "标准"),
        (CONSUMPTION_HIGH, "高预算"),
    ]

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="visitor_profile",
        verbose_name="用户",
    )
    nickname = models.CharField("昵称", max_length=50, blank=True, null=True)
    phone = models.CharField("手机号", max_length=20, blank=True, null=True)
    preference_tags = models.CharField("偏好标签", max_length=255, blank=True, default="")
    age_group = models.CharField("年龄段", max_length=20, choices=AGE_CHOICES, blank=True, default=AGE_ADULT)
    consumption_level = models.CharField("消费层级", max_length=20, choices=CONSUMPTION_CHOICES, blank=True, default=CONSUMPTION_MEDIUM)
    available_minutes = models.PositiveIntegerField("可游玩时长(分钟)", default=180)
    budget_amount = models.PositiveIntegerField("预算(元)", default=0)
    with_children = models.BooleanField("带儿童", default=False)
    with_elderly = models.BooleanField("带老人", default=False)
    updated_at = models.DateTimeField("更新时间", auto_now=True)

    class Meta:
        verbose_name = "游客资料"
        verbose_name_plural = "游客资料"
        constraints = [
            models.UniqueConstraint(
                fields=["nickname"],
                condition=Q(nickname__isnull=False) & ~Q(nickname=""),
                name="uniq_profile_nickname_not_blank",
            ),
            models.UniqueConstraint(
                fields=["phone"],
                condition=Q(phone__isnull=False) & ~Q(phone=""),
                name="uniq_profile_phone_not_blank",
            ),
        ]

    def __str__(self):
        return f"{self.user_id}:{self.nickname or self.user.username}"
