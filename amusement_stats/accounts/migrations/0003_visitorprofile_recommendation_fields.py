# Generated manually for visitor recommendation profiles.

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("accounts", "0002_visitorprofile_phone_alter_visitorprofile_nickname_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="visitorprofile",
            name="age_group",
            field=models.CharField(
                blank=True,
                choices=[
                    ("child", "儿童"),
                    ("teen", "青少年"),
                    ("adult", "成人"),
                    ("senior", "长者"),
                    ("family", "亲子家庭"),
                ],
                default="adult",
                max_length=20,
                verbose_name="年龄段",
            ),
        ),
        migrations.AddField(
            model_name="visitorprofile",
            name="consumption_level",
            field=models.CharField(
                blank=True,
                choices=[("low", "经济"), ("medium", "标准"), ("high", "高预算")],
                default="medium",
                max_length=20,
                verbose_name="消费层级",
            ),
        ),
        migrations.AddField(
            model_name="visitorprofile",
            name="available_minutes",
            field=models.PositiveIntegerField(default=180, verbose_name="可游玩时长(分钟)"),
        ),
        migrations.AddField(
            model_name="visitorprofile",
            name="budget_amount",
            field=models.PositiveIntegerField(default=0, verbose_name="预算(元)"),
        ),
        migrations.AddField(
            model_name="visitorprofile",
            name="with_children",
            field=models.BooleanField(default=False, verbose_name="带儿童"),
        ),
        migrations.AddField(
            model_name="visitorprofile",
            name="with_elderly",
            field=models.BooleanField(default=False, verbose_name="带老人"),
        ),
    ]
