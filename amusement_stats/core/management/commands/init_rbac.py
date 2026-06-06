from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.management.base import BaseCommand

from core.auth_utils import ADMIN_GROUP, STAFF_GROUP


class Command(BaseCommand):
    help = "初始化 RBAC 角色组，并可将用户加入指定角色"

    def add_arguments(self, parser):
        parser.add_argument("--admin", type=str, help="加入管理员组的用户名")
        parser.add_argument("--staff", type=str, help="加入工作人员组的用户名")

    def handle(self, *args, **options):
        admin_group, _ = Group.objects.get_or_create(name=ADMIN_GROUP)
        staff_group, _ = Group.objects.get_or_create(name=STAFF_GROUP)
        self.stdout.write(self.style.SUCCESS("角色组已准备：admin/staff"))

        User = get_user_model()
        if options.get("admin"):
            user = User.objects.filter(username=options["admin"]).first()
            if user:
                user.groups.add(admin_group)
                self.stdout.write(self.style.SUCCESS(f"用户 {user.username} 已加入 admin 组"))
        if options.get("staff"):
            user = User.objects.filter(username=options["staff"]).first()
            if user:
                user.groups.add(staff_group)
                self.stdout.write(self.style.SUCCESS(f"用户 {user.username} 已加入 staff 组"))

