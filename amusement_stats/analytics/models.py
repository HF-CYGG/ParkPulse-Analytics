from django.conf import settings
from django.db import models

from projects.models import Project


class ProjectHeatSnapshot(models.Model):
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="heat_snapshots", verbose_name="项目")
    snapshot_time = models.DateTimeField("快照时间", db_index=True)
    score = models.FloatField("综合热度")
    base_score = models.FloatField("基础指标")
    time_score = models.FloatField("时间指标")
    user_score = models.FloatField("用户指标")
    operations_score = models.FloatField("运营指标")
    external_score = models.FloatField("外部指标")
    subjective_score = models.FloatField("主观指标")
    metrics = models.JSONField("指标明细", default=dict, blank=True)
    updated_at = models.DateTimeField("更新时间", auto_now=True)

    class Meta:
        verbose_name = "项目热度快照"
        verbose_name_plural = "项目热度快照"
        ordering = ["-snapshot_time", "-score"]
        constraints = [
            models.UniqueConstraint(fields=["project", "snapshot_time"], name="uniq_project_heat_snapshot_time"),
        ]

    def __str__(self):
        return f"{self.project} {self.snapshot_time:%Y-%m-%d %H:%M} {self.score:.1f}"


class ProjectForecast(models.Model):
    ALERT_NONE = "none"
    ALERT_WATCH = "watch"
    ALERT_HIGH = "high"
    ALERT_CHOICES = [
        (ALERT_NONE, "无"),
        (ALERT_WATCH, "关注"),
        (ALERT_HIGH, "高峰预警"),
    ]

    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="forecasts", verbose_name="项目")
    model_name = models.CharField("模型", max_length=40, default="baseline")
    target_time = models.DateTimeField("预测时段", db_index=True)
    predicted_score = models.FloatField("预测热度")
    predicted_visits = models.FloatField("预测人次", default=0)
    predicted_queue = models.FloatField("预测排队时长", default=0)
    alert_level = models.CharField("告警级别", max_length=20, choices=ALERT_CHOICES, default=ALERT_NONE)
    warning = models.CharField("告警文案", max_length=255, blank=True, default="")
    factors = models.JSONField("影响因素", default=dict, blank=True)
    created_at = models.DateTimeField("生成时间", auto_now_add=True)

    class Meta:
        verbose_name = "项目热度预测"
        verbose_name_plural = "项目热度预测"
        ordering = ["target_time", "-predicted_score"]
        constraints = [
            models.UniqueConstraint(fields=["project", "model_name", "target_time"], name="uniq_project_model_target"),
        ]

    def __str__(self):
        return f"{self.project} {self.model_name} {self.target_time:%Y-%m-%d %H:%M}"


class ForecastEvaluation(models.Model):
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="forecast_evaluations", verbose_name="项目")
    model_name = models.CharField("模型", max_length=40)
    train_start = models.DateField("训练开始")
    train_end = models.DateField("训练结束")
    horizon_days = models.PositiveIntegerField("预测天数", default=7)
    mae = models.FloatField("MAE")
    mse = models.FloatField("MSE")
    r2 = models.FloatField("R2")
    sample_size = models.PositiveIntegerField("样本量", default=0)
    evaluated_at = models.DateTimeField("评估时间", auto_now_add=True)

    class Meta:
        verbose_name = "预测误差评估"
        verbose_name_plural = "预测误差评估"
        ordering = ["-evaluated_at", "model_name"]

    def __str__(self):
        return f"{self.project} {self.model_name} MAE={self.mae:.2f}"


class ProjectReview(models.Model):
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="reviews", verbose_name="项目")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="用户")
    rating = models.PositiveSmallIntegerField("评分")
    comment = models.TextField("评论", blank=True, default="")
    created_at = models.DateTimeField("创建时间", auto_now_add=True)

    class Meta:
        verbose_name = "项目评分"
        verbose_name_plural = "项目评分"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.project} {self.rating}"


class ProjectIncident(models.Model):
    TYPE_FAULT = "fault"
    TYPE_MAINTENANCE = "maintenance"
    TYPE_CHOICES = [
        (TYPE_FAULT, "故障"),
        (TYPE_MAINTENANCE, "维护"),
    ]

    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="incidents", verbose_name="项目")
    incident_type = models.CharField("事件类型", max_length=20, choices=TYPE_CHOICES, default=TYPE_FAULT)
    severity = models.PositiveSmallIntegerField("严重度", default=1)
    description = models.CharField("说明", max_length=255, blank=True, default="")
    started_at = models.DateTimeField("开始时间")
    ended_at = models.DateTimeField("结束时间", null=True, blank=True)
    downtime_minutes = models.PositiveIntegerField("维护/停机分钟", default=0)
    created_at = models.DateTimeField("创建时间", auto_now_add=True)

    class Meta:
        verbose_name = "设备事件"
        verbose_name_plural = "设备事件"
        ordering = ["-started_at"]

    def __str__(self):
        return f"{self.project} {self.incident_type}"


class HolidayCalendar(models.Model):
    TYPE_WORKDAY = "workday"
    TYPE_WEEKEND = "weekend"
    TYPE_HOLIDAY = "holiday"
    TYPE_CHOICES = [
        (TYPE_WORKDAY, "工作日"),
        (TYPE_WEEKEND, "周末"),
        (TYPE_HOLIDAY, "节假日"),
    ]

    date = models.DateField("日期", unique=True)
    name = models.CharField("名称", max_length=80)
    day_type = models.CharField("日期类型", max_length=20, choices=TYPE_CHOICES)
    heat_multiplier = models.FloatField("热度系数", default=1.0)

    class Meta:
        verbose_name = "节假日配置"
        verbose_name_plural = "节假日配置"
        ordering = ["date"]

    def __str__(self):
        return f"{self.date} {self.name}"


class PromotionEvent(models.Model):
    name = models.CharField("活动名称", max_length=120)
    start_date = models.DateField("开始日期")
    end_date = models.DateField("结束日期")
    description = models.TextField("说明", blank=True, default="")
    heat_multiplier = models.FloatField("热度系数", default=1.0)
    is_active = models.BooleanField("启用", default=True)

    class Meta:
        verbose_name = "促销活动"
        verbose_name_plural = "促销活动"
        ordering = ["-start_date"]

    def __str__(self):
        return self.name
