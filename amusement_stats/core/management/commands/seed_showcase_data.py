import math
import os
import random
from datetime import datetime, time, timedelta

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.management.base import BaseCommand
from django.utils import timezone

from accounts.models import VisitorProfile
from analytics.models import (
    HolidayCalendar,
    MaintenanceWorkOrder,
    ProjectIncident,
    ProjectReview,
    PromotionEvent,
    ServiceFacility,
    WeatherObservation,
)
from core.auth_utils import ADMIN_GROUP, STAFF_GROUP
from projects.models import Project
from records.models import PlayRecord
from visitor.models import ItineraryPlan, ItineraryPlanItem, VisitorFavorite, VisitorFeedback, VisitorFeedbackMessage


DEMO_NOTE = "showcase-demo"


class Command(BaseCommand):
    help = "Seed a complete, idempotent showcase dataset without clearing existing data."

    def add_arguments(self, parser):
        parser.add_argument("--days", type=int, default=90)
        parser.add_argument("--records-per-day", type=int, default=120)

    def handle(self, *args, **options):
        days = max(1, min(int(options["days"]), 365))
        records_per_day = max(1, min(int(options["records_per_day"]), 500))
        random.seed(20260607)

        admin, staff, visitor = self._seed_users()
        projects = self._seed_projects()
        self._seed_visitor_profile(visitor)
        self._seed_service_facilities()
        self._seed_external_calendar()
        self._seed_weather(days)
        self._seed_demo_profiles()
        self._seed_reviews(visitor, projects)
        self._seed_incidents_and_work_orders(staff, projects)
        self._seed_visitor_engagement(visitor, projects)
        self._seed_itinerary_plans(projects)
        created_records = self._seed_play_records(staff, projects, days, records_per_day)

        self.stdout.write(
            self.style.SUCCESS(
                "Showcase demo data seeded. "
                f"projects={len(projects)}, play_records_created={created_records}, "
                "accounts=demo_admin/demo_staff/demo_visitor"
            )
        )

    def _seed_users(self):
        admin_group, _ = Group.objects.get_or_create(name=ADMIN_GROUP)
        staff_group, _ = Group.objects.get_or_create(name=STAFF_GROUP)
        User = get_user_model()

        admin = self._upsert_user(
            User,
            "demo_admin",
            os.environ.get("DEMO_ADMIN_PASSWORD", "ParkPulse@2026!"),
            is_staff=True,
            is_superuser=True,
            email="demo_admin@parkpulse.local",
        )
        staff = self._upsert_user(
            User,
            "demo_staff",
            os.environ.get("DEMO_STAFF_PASSWORD", "Staff@2026!"),
            is_staff=True,
            is_superuser=False,
            email="demo_staff@parkpulse.local",
        )
        visitor = self._upsert_user(
            User,
            "demo_visitor",
            os.environ.get("DEMO_VISITOR_PASSWORD", "Visitor@2026!"),
            is_staff=False,
            is_superuser=False,
            email="demo_visitor@parkpulse.local",
        )
        admin.groups.add(admin_group)
        staff.groups.add(staff_group)
        return admin, staff, visitor

    def _upsert_user(self, User, username, password, *, is_staff, is_superuser, email):
        user, _ = User.objects.get_or_create(username=username, defaults={"email": email})
        user.email = email
        user.is_staff = is_staff
        user.is_superuser = is_superuser
        user.is_active = True
        user.set_password(password)
        user.save(update_fields=["email", "is_staff", "is_superuser", "is_active", "password"])
        return user

    def _seed_projects(self):
        rows = [
            ("星际过山车", Project.TYPE_THRILL, Project.REGION_THRILL, 28, 18, 520, 31.237800, 121.478900, "高速翻转轨道，适合刺激型游客。"),
            ("云霄飞塔", Project.TYPE_THRILL, Project.REGION_THRILL, 32, 12, 480, 31.238400, 121.477800, "高空俯冲与观景结合的地标项目。"),
            ("激流勇进", Project.TYPE_THRILL, Project.REGION_VIEW, 22, 15, 430, 31.236900, 121.479800, "水上俯冲项目，午后热度较高。"),
            ("海盗船", Project.TYPE_THRILL, Project.REGION_THRILL, 36, 8, 420, 31.237300, 121.477200, "经典摆动项目，吞吐稳定。"),
            ("旋转木马", Project.TYPE_FAMILY, Project.REGION_FAMILY, 40, 5, 360, 31.235900, 121.476700, "亲子游客首选，低龄友好。"),
            ("童话小火车", Project.TYPE_FAMILY, Project.REGION_FAMILY, 48, 10, 380, 31.235500, 121.477500, "环园慢速观光路线。"),
            ("魔法剧场", Project.TYPE_FAMILY, Project.REGION_FAMILY, 120, 25, 520, 31.235200, 121.478500, "室内剧场，可承接高峰分流。"),
            ("泡泡水世界", Project.TYPE_FAMILY, Project.REGION_FAMILY, 55, 20, 440, 31.234800, 121.479400, "亲子戏水区，天气敏感度高。"),
            ("摩天轮", Project.TYPE_VIEW, Project.REGION_VIEW, 60, 18, 500, 31.238200, 121.480700, "园区观景核心项目。"),
            ("天空缆车", Project.TYPE_VIEW, Project.REGION_VIEW, 42, 16, 420, 31.237100, 121.481500, "连接观光区和休闲区。"),
            ("湖畔漂流", Project.TYPE_VIEW, Project.REGION_VIEW, 35, 22, 390, 31.236000, 121.481000, "低强度水上观光项目。"),
            ("梦幻花车巡游", Project.TYPE_VIEW, Project.REGION_ENTRANCE, 200, 30, 700, 31.234900, 121.475800, "入口主街巡游活动，适合全客群。"),
        ]
        projects = []
        for name, ptype, region, capacity, cycle, threshold, lat, lng, description in rows:
            project, _ = Project.objects.update_or_create(
                name=name,
                defaults={
                    "project_type": ptype,
                    "region": region,
                    "capacity": capacity,
                    "cycle_minutes": cycle,
                    "daily_warn_threshold": threshold,
                    "status": Project.STATUS_NORMAL,
                    "queue_count": self._queue_count_for(name, capacity),
                    "latitude": lat,
                    "longitude": lng,
                    "short_description": description,
                    "operating_hours_text": "10:00-21:00",
                },
            )
            projects.append(project)
        return projects

    def _queue_count_for(self, name: str, capacity: int) -> int:
        factor = 0.9 if name in {"星际过山车", "摩天轮", "魔法剧场"} else 0.55
        return max(3, int(capacity * factor))

    def _seed_visitor_profile(self, visitor):
        VisitorProfile.objects.update_or_create(
            user=visitor,
            defaults={
                "nickname": "演示游客",
                "phone": "18800000001",
                "preference_tags": "亲子,低排队,观光",
                "age_group": VisitorProfile.AGE_FAMILY,
                "consumption_level": VisitorProfile.CONSUMPTION_MEDIUM,
                "available_minutes": 240,
                "budget_amount": 360,
                "with_children": True,
                "with_elderly": False,
            },
        )

    def _seed_service_facilities(self):
        rows = [
            ("星际能量餐厅", ServiceFacility.TYPE_CATERING, Project.REGION_THRILL, 31.237600, 121.478200),
            ("亲子补给站", ServiceFacility.TYPE_CATERING, Project.REGION_FAMILY, 31.235700, 121.477200),
            ("湖畔咖啡", ServiceFacility.TYPE_CATERING, Project.REGION_VIEW, 31.236300, 121.480700),
            ("云端文创店", ServiceFacility.TYPE_RETAIL, Project.REGION_VIEW, 31.238000, 121.480200),
            ("童话礼品屋", ServiceFacility.TYPE_RETAIL, Project.REGION_FAMILY, 31.235300, 121.478200),
            ("家庭休息亭", ServiceFacility.TYPE_REST, Project.REGION_FAMILY, 31.235000, 121.477900),
            ("刺激区储物柜", ServiceFacility.TYPE_REST, Project.REGION_THRILL, 31.237900, 121.477300),
            ("入口游客中心", ServiceFacility.TYPE_REST, Project.REGION_ENTRANCE, 31.234700, 121.475500),
        ]
        for name, facility_type, region, lat, lng in rows:
            ServiceFacility.objects.update_or_create(
                name=name,
                defaults={
                    "facility_type": facility_type,
                    "region": region,
                    "latitude": lat,
                    "longitude": lng,
                    "is_active": True,
                },
            )

    def _seed_external_calendar(self):
        today = timezone.localdate()
        for offset in range(-3, 11):
            target = today + timedelta(days=offset)
            is_weekend = target.weekday() >= 5
            HolidayCalendar.objects.update_or_create(
                date=target,
                defaults={
                    "name": "周末客流日" if is_weekend else "工作日",
                    "day_type": HolidayCalendar.TYPE_WEEKEND if is_weekend else HolidayCalendar.TYPE_WORKDAY,
                    "heat_multiplier": 1.16 if is_weekend else 1.0,
                },
            )
        HolidayCalendar.objects.update_or_create(
            date=today + timedelta(days=1),
            defaults={"name": "演示节假日", "day_type": HolidayCalendar.TYPE_HOLIDAY, "heat_multiplier": 1.3},
        )
        PromotionEvent.objects.update_or_create(
            name="暑期亲子畅玩节",
            defaults={
                "start_date": today - timedelta(days=2),
                "end_date": today + timedelta(days=14),
                "description": "亲子套票、餐饮折扣与文创满减联动活动。",
                "heat_multiplier": 1.18,
                "is_active": True,
            },
        )
        PromotionEvent.objects.update_or_create(
            name="夜场观光优惠",
            defaults={
                "start_date": today,
                "end_date": today + timedelta(days=10),
                "description": "摩天轮、天空缆车和花车巡游夜场组合优惠。",
                "heat_multiplier": 1.12,
                "is_active": True,
            },
        )

    def _seed_weather(self, days):
        today = timezone.localdate()
        for offset in range(days - 1, -8, -1):
            target = today - timedelta(days=offset)
            mod = abs(offset) % 10
            if mod in {0, 1}:
                weather_type = WeatherObservation.TYPE_RAIN
                temp = 21
                rain = 6.5
                humidity = 86
                multiplier = 0.86
                desc = "小雨，室外刺激项目热度下降"
            elif mod == 5:
                weather_type = WeatherObservation.TYPE_HEAT
                temp = 34
                rain = 0
                humidity = 62
                multiplier = 0.94
                desc = "高温，亲水与室内项目热度提升"
            elif mod == 7:
                weather_type = WeatherObservation.TYPE_CLOUDY
                temp = 26
                rain = 0
                humidity = 58
                multiplier = 1.05
                desc = "多云舒适，整体游园意愿提升"
            else:
                weather_type = WeatherObservation.TYPE_CLEAR
                temp = 27
                rain = 0
                humidity = 52
                multiplier = 1.0
                desc = "晴朗，按常规热度处理"
            WeatherObservation.objects.update_or_create(
                date=target,
                defaults={
                    "weather_type": weather_type,
                    "temperature_c": temp,
                    "rain_mm": rain,
                    "humidity": humidity,
                    "heat_multiplier": multiplier,
                    "description": desc,
                },
            )

    def _seed_demo_profiles(self):
        User = get_user_model()
        rows = [
            ("demo_family_low_budget", "亲子低预算", "亲子,低排队", VisitorProfile.AGE_FAMILY, VisitorProfile.CONSUMPTION_LOW, 180, 120, True, False),
            ("demo_senior_view", "长者观光", "观光,休闲", VisitorProfile.AGE_SENIOR, VisitorProfile.CONSUMPTION_MEDIUM, 150, 180, False, True),
            ("demo_thrill_high", "刺激玩家", "刺激,热门", VisitorProfile.AGE_ADULT, VisitorProfile.CONSUMPTION_HIGH, 240, 420, False, False),
        ]
        for username, nickname, tags, age, consumption, minutes, budget, children, elderly in rows:
            user, _ = User.objects.get_or_create(username=username, defaults={"email": f"{username}@parkpulse.local"})
            user.set_password(os.environ.get("DEMO_VISITOR_PASSWORD", "Visitor@2026!"))
            user.save(update_fields=["password"])
            VisitorProfile.objects.update_or_create(
                user=user,
                defaults={
                    "nickname": nickname,
                    "preference_tags": tags,
                    "age_group": age,
                    "consumption_level": consumption,
                    "available_minutes": minutes,
                    "budget_amount": budget,
                    "with_children": children,
                    "with_elderly": elderly,
                },
            )

    def _seed_reviews(self, visitor, projects):
        comments = ["体验顺畅，适合推荐。", "排队可接受，现场引导清晰。", "项目热度高，建议错峰游玩。"]
        for idx, project in enumerate(projects):
            ProjectReview.objects.get_or_create(
                project=project,
                user=visitor,
                comment=f"{DEMO_NOTE}: {comments[idx % len(comments)]}",
                defaults={
                    "experience_score": 4 + (idx % 2),
                    "queue_reasonableness_score": 4 if idx % 3 else 3,
                    "safety_score": 5,
                },
            )

    def _seed_incidents_and_work_orders(self, staff, projects):
        now = timezone.now()
        for idx, project in enumerate(projects[:6]):
            if idx % 2 == 0:
                incident, _ = ProjectIncident.objects.get_or_create(
                    project=project,
                    description=f"{DEMO_NOTE}: 例行维护与安全检查",
                    started_at=now - timedelta(days=idx + 2, hours=2),
                    defaults={
                        "incident_type": ProjectIncident.TYPE_MAINTENANCE,
                        "severity": 1 + (idx % 3),
                        "ended_at": now - timedelta(days=idx + 2, hours=1),
                        "downtime_minutes": 45 + idx * 10,
                        "handled_by": staff,
                        "status": ProjectIncident.STATUS_RESOLVED,
                        "notes": "演示维护闭环数据",
                    },
                )
                MaintenanceWorkOrder.objects.get_or_create(
                    project=project,
                    incident=incident,
                    started_at=incident.started_at,
                    defaults={
                        "status": MaintenanceWorkOrder.STATUS_DONE,
                        "handled_by": staff,
                        "ended_at": incident.ended_at,
                        "notes": "完成传感器检查、轨道巡检与试运行。",
                    },
                )

    def _seed_visitor_engagement(self, visitor, projects):
        for project in projects[:5]:
            VisitorFavorite.objects.get_or_create(user=visitor, project=project)
        feedback, _ = VisitorFeedback.objects.get_or_create(
            user=visitor,
            title="希望增加亲子路线引导",
            defaults={"content": "希望在高峰期推荐低排队亲子路线。", "contact": "18800000001"},
        )
        VisitorFeedbackMessage.objects.get_or_create(
            feedback=feedback,
            sender=VisitorFeedbackMessage.SENDER_VISITOR,
            content="我们带儿童游玩，希望减少往返和排队时间。",
            defaults={"read_by_visitor": True, "read_by_admin": False},
        )
        VisitorFeedbackMessage.objects.get_or_create(
            feedback=feedback,
            sender=VisitorFeedbackMessage.SENDER_ADMIN,
            content="已为您推荐亲子低排队路线，可在智能推荐页面查看。",
            defaults={"read_by_visitor": False, "read_by_admin": True},
        )

    def _seed_itinerary_plans(self, projects):
        project_by_name = {project.name: project for project in projects}
        plans = [
            (
                "亲子低排队半日线",
                ItineraryPlan.AUDIENCE_FAMILY,
                "亲子,低排队",
                "优先选择等待时间较短、步行距离较少的亲子项目。",
                ["旋转木马", "童话小火车", "魔法剧场", "泡泡水世界"],
            ),
            (
                "刺激挑战高热线",
                ItineraryPlan.AUDIENCE_ADULT,
                "刺激,热门",
                "覆盖园区高热刺激项目，适合成人游客和年轻团队。",
                ["星际过山车", "云霄飞塔", "海盗船", "激流勇进"],
            ),
            (
                "观光休闲夜场线",
                ItineraryPlan.AUDIENCE_TEEN,
                "观光,低预算",
                "结合观光项目和夜场活动，减少体力消耗。",
                ["梦幻花车巡游", "摩天轮", "天空缆车", "湖畔漂流"],
            ),
            (
                "长者友好慢游线",
                ItineraryPlan.AUDIENCE_ADULT,
                "长者友好,休闲",
                "优先安排观光与低刺激项目，减少排队和快速移动压力。",
                ["梦幻花车巡游", "童话小火车", "摩天轮", "天空缆车"],
            ),
            (
                "低预算高性价比线",
                ItineraryPlan.AUDIENCE_FAMILY,
                "低预算,低排队",
                "选择等待压力较低、停留成本较低的项目，适合预算敏感游客。",
                ["童话小火车", "旋转木马", "湖畔漂流", "梦幻花车巡游"],
            ),
            (
                "夜场拍照打卡线",
                ItineraryPlan.AUDIENCE_TEEN,
                "夜场,拍照",
                "串联夜间观景与拍照点位，适合傍晚后入园游客。",
                ["梦幻花车巡游", "摩天轮", "天空缆车", "湖畔漂流"],
            ),
            (
                "热门项目精华线",
                ItineraryPlan.AUDIENCE_ADULT,
                "热门,刺激",
                "精选高热项目，建议配合高峰预警错峰体验。",
                ["星际过山车", "魔法剧场", "云霄飞塔", "摩天轮"],
            ),
            (
                "清凉亲水休闲线",
                ItineraryPlan.AUDIENCE_FAMILY,
                "休闲,亲子",
                "围绕水上和休闲项目安排，适合午后降温与家庭停留。",
                ["泡泡水世界", "湖畔漂流", "童话小火车", "旋转木马"],
            ),
        ]
        for name, audience, tag, description, project_names in plans:
            plan, _ = ItineraryPlan.objects.update_or_create(
                name=name,
                defaults={
                    "audience": audience,
                    "preference_tag": tag,
                    "description": description,
                    "is_active": True,
                },
            )
            for seq, project_name in enumerate(project_names, start=1):
                project = project_by_name.get(project_name)
                if not project:
                    continue
                ItineraryPlanItem.objects.update_or_create(
                    plan=plan,
                    seq=seq,
                    defaults={"project": project, "tip": self._route_tip(seq, project)},
                )

    def _route_tip(self, seq, project):
        if seq == 1:
            return "建议开园后优先游玩，降低排队压力。"
        if project.project_type == Project.TYPE_FAMILY:
            return "适合亲子停留，可与周边餐饮休息联动。"
        if project.project_type == Project.TYPE_THRILL:
            return "高峰前完成体验，避开午后排队。"
        return "适合作为路线收尾或夜场观光节点。"

    def _seed_play_records(self, staff, projects, days, records_per_day):
        now = timezone.localtime()
        created = 0
        for offset in range(days - 1, -1, -1):
            target_day = now.date() - timedelta(days=offset)
            existing = PlayRecord.objects.filter(play_time__date=target_day, note=DEMO_NOTE).count()
            missing = max(0, records_per_day - existing)
            for index in range(missing):
                project = self._weighted_project(projects, target_day, index)
                play_dt = self._play_datetime(target_day, index)
                queue_time = self._queue_time(project, play_dt, index)
                PlayRecord.objects.create(
                    project=project,
                    play_time=play_dt,
                    queue_time=queue_time,
                    repeat_count=1 if (project.project_type == Project.TYPE_THRILL and index % 5 == 0) else index % 2,
                    status_snapshot=Project.STATUS_MAINTENANCE if index % 37 == 0 else Project.STATUS_NORMAL,
                    note=DEMO_NOTE,
                    created_by=staff,
                )
                created += 1
        return created

    def _weighted_project(self, projects, target_day, index):
        weekend_boost = 2 if target_day.weekday() >= 5 else 1
        weighted = []
        for project in projects:
            weight = 3
            if project.name in {"星际过山车", "摩天轮", "魔法剧场"}:
                weight += 3 * weekend_boost
            if project.project_type == Project.TYPE_FAMILY and 10 <= index % 24 <= 16:
                weight += 2
            weighted.extend([project] * weight)
        return weighted[index % len(weighted)]

    def _play_datetime(self, target_day, index):
        peak_hours = [10, 11, 12, 15, 16, 17, 19]
        quiet_hours = [13, 14, 18, 20]
        hour_pool = peak_hours if index % 3 else quiet_hours
        hour = hour_pool[index % len(hour_pool)]
        minute = (index * 7) % 60
        naive = datetime.combine(target_day, time(hour=hour, minute=minute))
        return timezone.make_aware(naive, timezone.get_current_timezone())

    def _queue_time(self, project, play_dt, index):
        peak = 10 <= play_dt.hour <= 12 or 16 <= play_dt.hour <= 19
        base = project.cycle_minutes + math.ceil(project.queue_count / max(project.capacity, 1) * 10)
        type_boost = 12 if project.project_type == Project.TYPE_THRILL else 6
        weekend_boost = 8 if play_dt.date().weekday() >= 5 else 0
        peak_boost = 10 if peak else 0
        variation = (index * 3) % 9
        return max(3, min(90, base + type_boost + weekend_boost + peak_boost + variation))
