from django.db import models
from django.contrib.auth import get_user_model

from projects.models import Project


User = get_user_model()


class PlayRecord(models.Model):
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="records", verbose_name="游乐项目")
    play_time = models.DateTimeField("游玩时间")
    queue_time = models.PositiveIntegerField("排队时长(分钟)", default=0)
    repeat_count = models.PositiveIntegerField("重复游玩次数", default=0)
    status_snapshot = models.CharField("设备状态快照", max_length=20, choices=Project.STATUS_CHOICES, default=Project.STATUS_NORMAL)
    note = models.TextField("备注", blank=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="录入人")
    created_at = models.DateTimeField("录入时间", auto_now_add=True)

    class Meta:
        ordering = ["-play_time", "-created_at"]
        verbose_name = "游玩记录"
        verbose_name_plural = "游玩记录"

    def __str__(self):
        return f"{self.project.name} - {self.play_time:%Y-%m-%d %H:%M}"
