from django.db import models


class Project(models.Model):
    STATUS_NORMAL = "normal"
    STATUS_MAINTENANCE = "maintenance"
    STATUS_CLOSED = "closed"
    STATUS_CHOICES = [
        (STATUS_NORMAL, "正常"),
        (STATUS_MAINTENANCE, "维护"),
        (STATUS_CLOSED, "关闭"),
    ]

    TYPE_THRILL = "thrill"
    TYPE_FAMILY = "family"
    TYPE_VIEW = "view"
    TYPE_CHOICES = [
        (TYPE_THRILL, "刺激类"),
        (TYPE_FAMILY, "亲子类"),
        (TYPE_VIEW, "观光类"),
    ]

    REGION_ENTRANCE = "entrance"
    REGION_FAMILY = "family"
    REGION_THRILL = "thrill"
    REGION_VIEW = "view"
    REGION_REST = "rest"
    REGION_CATERING = "catering"
    REGION_CHOICES = [
        (REGION_ENTRANCE, "入口区"),
        (REGION_FAMILY, "亲子区"),
        (REGION_THRILL, "刺激区"),
        (REGION_VIEW, "观光区"),
        (REGION_REST, "休闲区"),
        (REGION_CATERING, "餐饮配套区"),
    ]

    name = models.CharField("项目名称", max_length=100, unique=True)
    project_type = models.CharField("项目类型", max_length=20, choices=TYPE_CHOICES, default=TYPE_FAMILY)
    status = models.CharField("运行状态", max_length=20, choices=STATUS_CHOICES, default=STATUS_NORMAL)
    capacity = models.PositiveIntegerField("最大承载量", default=20)
    daily_warn_threshold = models.PositiveIntegerField("日客流预警阈值", default=300)
    queue_count = models.PositiveIntegerField("当前排队人数", default=0)
    cycle_minutes = models.PositiveIntegerField("单轮游玩时长(分钟)", default=5)
    operating_hours_text = models.CharField("运营时间说明", max_length=100, blank=True, default="")

    region = models.CharField("所属园区区域", max_length=20, choices=REGION_CHOICES, blank=True, null=True)
    short_description = models.TextField("项目简介（游客端展示）", blank=True)
    cover_image = models.ImageField("封面图", upload_to="project_covers/", blank=True, null=True)
    latitude = models.DecimalField("地图纬度", max_digits=9, decimal_places=6, blank=True, null=True)
    longitude = models.DecimalField("地图经度", max_digits=9, decimal_places=6, blank=True, null=True)
    created_at = models.DateTimeField("创建时间", auto_now_add=True)
    updated_at = models.DateTimeField("更新时间", auto_now=True)

    class Meta:
        ordering = ["name"]
        verbose_name = "游乐项目"
        verbose_name_plural = "游乐项目"

    def __str__(self):
        return self.name

    def effective_region(self) -> str:
        """历史数据缺少 region 时，用项目类型推断区域。"""
        if self.region:
            return self.region
        if self.project_type == Project.TYPE_FAMILY:
            return Project.REGION_FAMILY
        if self.project_type == Project.TYPE_THRILL:
            return Project.REGION_THRILL
        if self.project_type == Project.TYPE_VIEW:
            return Project.REGION_VIEW
        return Project.REGION_REST
