# Generated manually for the analytics upgrade.

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("projects", "0006_alter_project_status"),
    ]

    operations = [
        migrations.CreateModel(
            name="HolidayCalendar",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("date", models.DateField(unique=True, verbose_name="日期")),
                ("name", models.CharField(max_length=80, verbose_name="名称")),
                (
                    "day_type",
                    models.CharField(
                        choices=[("workday", "工作日"), ("weekend", "周末"), ("holiday", "节假日")],
                        max_length=20,
                        verbose_name="日期类型",
                    ),
                ),
                ("heat_multiplier", models.FloatField(default=1.0, verbose_name="热度系数")),
            ],
            options={"verbose_name": "节假日配置", "verbose_name_plural": "节假日配置", "ordering": ["date"]},
        ),
        migrations.CreateModel(
            name="PromotionEvent",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(max_length=120, verbose_name="活动名称")),
                ("start_date", models.DateField(verbose_name="开始日期")),
                ("end_date", models.DateField(verbose_name="结束日期")),
                ("description", models.TextField(blank=True, default="", verbose_name="说明")),
                ("heat_multiplier", models.FloatField(default=1.0, verbose_name="热度系数")),
                ("is_active", models.BooleanField(default=True, verbose_name="启用")),
            ],
            options={"verbose_name": "促销活动", "verbose_name_plural": "促销活动", "ordering": ["-start_date"]},
        ),
        migrations.CreateModel(
            name="ForecastEvaluation",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("model_name", models.CharField(max_length=40, verbose_name="模型")),
                ("train_start", models.DateField(verbose_name="训练开始")),
                ("train_end", models.DateField(verbose_name="训练结束")),
                ("horizon_days", models.PositiveIntegerField(default=7, verbose_name="预测天数")),
                ("mae", models.FloatField(verbose_name="MAE")),
                ("mse", models.FloatField(verbose_name="MSE")),
                ("r2", models.FloatField(verbose_name="R2")),
                ("sample_size", models.PositiveIntegerField(default=0, verbose_name="样本量")),
                ("evaluated_at", models.DateTimeField(auto_now_add=True, verbose_name="评估时间")),
                (
                    "project",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="forecast_evaluations",
                        to="projects.project",
                        verbose_name="项目",
                    ),
                ),
            ],
            options={"verbose_name": "预测误差评估", "verbose_name_plural": "预测误差评估", "ordering": ["-evaluated_at", "model_name"]},
        ),
        migrations.CreateModel(
            name="ProjectForecast",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("model_name", models.CharField(default="baseline", max_length=40, verbose_name="模型")),
                ("target_time", models.DateTimeField(db_index=True, verbose_name="预测时段")),
                ("predicted_score", models.FloatField(verbose_name="预测热度")),
                ("predicted_visits", models.FloatField(default=0, verbose_name="预测人次")),
                ("predicted_queue", models.FloatField(default=0, verbose_name="预测排队时长")),
                (
                    "alert_level",
                    models.CharField(
                        choices=[("none", "无"), ("watch", "关注"), ("high", "高峰预警")],
                        default="none",
                        max_length=20,
                        verbose_name="告警级别",
                    ),
                ),
                ("warning", models.CharField(blank=True, default="", max_length=255, verbose_name="告警文案")),
                ("factors", models.JSONField(blank=True, default=dict, verbose_name="影响因素")),
                ("created_at", models.DateTimeField(auto_now_add=True, verbose_name="生成时间")),
                (
                    "project",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="forecasts",
                        to="projects.project",
                        verbose_name="项目",
                    ),
                ),
            ],
            options={"verbose_name": "项目热度预测", "verbose_name_plural": "项目热度预测", "ordering": ["target_time", "-predicted_score"]},
        ),
        migrations.CreateModel(
            name="ProjectHeatSnapshot",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("snapshot_time", models.DateTimeField(db_index=True, verbose_name="快照时间")),
                ("score", models.FloatField(verbose_name="综合热度")),
                ("base_score", models.FloatField(verbose_name="基础指标")),
                ("time_score", models.FloatField(verbose_name="时间指标")),
                ("user_score", models.FloatField(verbose_name="用户指标")),
                ("operations_score", models.FloatField(verbose_name="运营指标")),
                ("external_score", models.FloatField(verbose_name="外部指标")),
                ("subjective_score", models.FloatField(verbose_name="主观指标")),
                ("metrics", models.JSONField(blank=True, default=dict, verbose_name="指标明细")),
                ("updated_at", models.DateTimeField(auto_now=True, verbose_name="更新时间")),
                (
                    "project",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="heat_snapshots",
                        to="projects.project",
                        verbose_name="项目",
                    ),
                ),
            ],
            options={"verbose_name": "项目热度快照", "verbose_name_plural": "项目热度快照", "ordering": ["-snapshot_time", "-score"]},
        ),
        migrations.CreateModel(
            name="ProjectIncident",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                (
                    "incident_type",
                    models.CharField(
                        choices=[("fault", "故障"), ("maintenance", "维护")],
                        default="fault",
                        max_length=20,
                        verbose_name="事件类型",
                    ),
                ),
                ("severity", models.PositiveSmallIntegerField(default=1, verbose_name="严重度")),
                ("description", models.CharField(blank=True, default="", max_length=255, verbose_name="说明")),
                ("started_at", models.DateTimeField(verbose_name="开始时间")),
                ("ended_at", models.DateTimeField(blank=True, null=True, verbose_name="结束时间")),
                ("downtime_minutes", models.PositiveIntegerField(default=0, verbose_name="维护/停机分钟")),
                ("created_at", models.DateTimeField(auto_now_add=True, verbose_name="创建时间")),
                (
                    "project",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="incidents",
                        to="projects.project",
                        verbose_name="项目",
                    ),
                ),
            ],
            options={"verbose_name": "设备事件", "verbose_name_plural": "设备事件", "ordering": ["-started_at"]},
        ),
        migrations.CreateModel(
            name="ProjectReview",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("rating", models.PositiveSmallIntegerField(verbose_name="评分")),
                ("comment", models.TextField(blank=True, default="", verbose_name="评论")),
                ("created_at", models.DateTimeField(auto_now_add=True, verbose_name="创建时间")),
                (
                    "project",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="reviews",
                        to="projects.project",
                        verbose_name="项目",
                    ),
                ),
                (
                    "user",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        to=settings.AUTH_USER_MODEL,
                        verbose_name="用户",
                    ),
                ),
            ],
            options={"verbose_name": "项目评分", "verbose_name_plural": "项目评分", "ordering": ["-created_at"]},
        ),
        migrations.AddConstraint(
            model_name="projectheatsnapshot",
            constraint=models.UniqueConstraint(fields=("project", "snapshot_time"), name="uniq_project_heat_snapshot_time"),
        ),
        migrations.AddConstraint(
            model_name="projectforecast",
            constraint=models.UniqueConstraint(fields=("project", "model_name", "target_time"), name="uniq_project_model_target"),
        ),
    ]
