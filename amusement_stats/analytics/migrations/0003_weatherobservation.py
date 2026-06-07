# Generated manually for weather-aware heat analytics.

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("analytics", "0002_servicefacility_forecastevaluation_parameters_and_more"),
    ]

    operations = [
        migrations.CreateModel(
            name="WeatherObservation",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("date", models.DateField(unique=True, verbose_name="日期")),
                (
                    "weather_type",
                    models.CharField(
                        choices=[
                            ("clear", "晴朗"),
                            ("cloudy", "多云"),
                            ("rain", "降雨"),
                            ("heat", "高温"),
                            ("wind", "大风"),
                        ],
                        default="clear",
                        max_length=20,
                        verbose_name="天气类型",
                    ),
                ),
                ("temperature_c", models.FloatField(default=24, verbose_name="温度(℃)")),
                ("rain_mm", models.FloatField(default=0, verbose_name="降雨量(mm)")),
                ("humidity", models.FloatField(default=55, verbose_name="湿度(%)")),
                ("heat_multiplier", models.FloatField(default=1.0, verbose_name="热度系数")),
                ("description", models.CharField(blank=True, default="", max_length=160, verbose_name="说明")),
            ],
            options={
                "verbose_name": "天气观测",
                "verbose_name_plural": "天气观测",
                "ordering": ["date"],
            },
        ),
    ]
