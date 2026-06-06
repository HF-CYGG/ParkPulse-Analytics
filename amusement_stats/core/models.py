from django.db import models
from django.contrib.auth import get_user_model


User = get_user_model()

class AuditLog(models.Model):
    action = models.CharField("动作", max_length=50)
    actor = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="操作者")
    target_type = models.CharField("目标类型", max_length=50, blank=True)
    target_id = models.CharField("目标ID", max_length=64, blank=True)
    message = models.CharField("说明", max_length=255, blank=True)
    ip = models.GenericIPAddressField("IP", null=True, blank=True)
    path = models.CharField("路径", max_length=255, blank=True)
    created_at = models.DateTimeField("时间", auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "操作审计"
        verbose_name_plural = "操作审计"

    def __str__(self):
        return f"{self.created_at:%Y-%m-%d %H:%M:%S} {self.action}"


class SiteConfig(models.Model):
    operating_hours_text = models.CharField("园区营业时间", max_length=100, blank=True, default="10:00-21:00")
    updated_at = models.DateTimeField("更新时间", auto_now=True)

    class Meta:
        verbose_name = "站点配置"
        verbose_name_plural = "站点配置"

    @classmethod
    def get_solo(cls):
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj
