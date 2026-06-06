from datetime import timedelta

from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import Group
from django.contrib.auth.views import LoginView
from django.core.paginator import Paginator
from django.db.models import Count, Sum
from django.http import HttpResponseRedirect, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone

from core.audit import log_action
from core.auth_utils import ADMIN_GROUP, STAFF_GROUP, admin_required, staff_or_admin_required, user_is_admin
from projects.models import Project

from .forms import StyledAuthenticationForm


@admin_required
def user_role_manage(request):
    """用户与角色管理：基于 Django Group 维护 none/staff/admin。"""
    User = get_user_model()
    role_choices = [
        ("none", "普通用户"),
        ("staff", "工作人员"),
        ("admin", "管理员"),
    ]
    role_map = dict(role_choices)

    admin_group, _ = Group.objects.get_or_create(name=ADMIN_GROUP)
    staff_group, _ = Group.objects.get_or_create(name=STAFF_GROUP)

    if request.method == "POST":
        op = request.POST.get("op", "assign_role").strip()

        if op == "create_user":
            username = request.POST.get("username", "").strip()
            password = request.POST.get("password", "").strip()
            role = request.POST.get("role", "none").strip()
            if not username or not password:
                messages.error(request, "用户名和密码不能为空。")
                return redirect("user_role_manage")
            if User.objects.filter(username=username).exists():
                messages.error(request, "该用户名已存在。")
                return redirect("user_role_manage")
            if role not in {"none", "staff", "admin"}:
                messages.error(request, "角色参数无效。")
                return redirect("user_role_manage")

            new_user = User.objects.create_user(username=username, password=password)
            if role == "admin":
                new_user.groups.add(admin_group)
            elif role == "staff":
                new_user.groups.add(staff_group)

            log_action(
                request,
                "user_create",
                target_type="User",
                target_id=str(new_user.id),
                message=f"{new_user.username} -> {role_map.get(role, role)}",
            )
            messages.success(request, f"用户 {new_user.username} 创建成功。")
            return redirect("user_role_manage")

        if op == "reset_password":
            user_id = request.POST.get("user_id", "").strip()
            new_password = request.POST.get("new_password", "").strip()
            if not user_id or not new_password:
                messages.error(request, "用户和新密码不能为空。")
                return redirect("user_role_manage")

            target_user = get_object_or_404(User, id=user_id)
            if target_user.is_superuser:
                messages.error(request, "超级管理员账号不允许重置密码。")
                return redirect("user_role_manage")

            target_user.set_password(new_password)
            target_user.save(update_fields=["password"])
            log_action(
                request,
                "user_password_reset",
                target_type="User",
                target_id=str(target_user.id),
                message=f"{target_user.username} 密码重置",
            )
            messages.success(request, f"用户 {target_user.username} 密码已重置。")
            return redirect("user_role_manage")

        if op == "delete_user":
            user_id = request.POST.get("user_id", "").strip()
            if not user_id:
                messages.error(request, "未指定用户。")
                return redirect("user_role_manage")
            target_user = get_object_or_404(User, id=user_id)
            if target_user.is_superuser:
                messages.error(request, "不能删除超级管理员账号。")
                return redirect("user_role_manage")
            if target_user.id == request.user.id:
                messages.error(request, "不能删除当前登录账号。")
                return redirect("user_role_manage")

            uname = target_user.username
            uid = target_user.id
            target_user.delete()
            log_action(
                request,
                "user_delete",
                target_type="User",
                target_id=str(uid),
                message=f"删除用户 {uname}",
            )
            messages.warning(request, f"已删除用户“{uname}”。")
            return redirect("user_role_manage")

        # 默认：assign_role
        user_id = request.POST.get("user_id", "").strip()
        role = request.POST.get("role", "none").strip()
        target_user = get_object_or_404(User, id=user_id)
        if target_user.is_superuser:
            messages.error(request, "超级管理员账号不允许修改角色。")
            return redirect("user_role_manage")

        target_user.groups.remove(admin_group)
        target_user.groups.remove(staff_group)
        if role == "admin":
            target_user.groups.add(admin_group)
        elif role == "staff":
            target_user.groups.add(staff_group)
        elif role != "none":
            messages.error(request, "角色参数无效。")
            return redirect("user_role_manage")

        role_label = role_map.get(role, role)
        log_action(
            request,
            "user_role_update",
            target_type="User",
            target_id=str(target_user.id),
            message=f"{target_user.username} -> {role_label}",
        )
        messages.success(request, f"用户 {target_user.username} 角色已更新为：{role_label}")
        return redirect("user_role_manage")

    keyword = request.GET.get("keyword", "").strip()
    users_qs = User.objects.all().order_by("username").prefetch_related("groups")
    if keyword:
        users_qs = users_qs.filter(username__icontains=keyword)

    try:
        page_size = max(5, min(100, int(request.session.get("page_size", 10))))
    except (TypeError, ValueError):
        page_size = 10
    page_obj = Paginator(users_qs, page_size).get_page(request.GET.get("page"))

    user_rows = []
    for user_obj in page_obj:
        if user_obj.is_superuser or user_obj.groups.filter(name=ADMIN_GROUP).exists():
            role = "admin"
        elif user_obj.groups.filter(name=STAFF_GROUP).exists():
            role = "staff"
        else:
            role = "none"
        user_rows.append({"user": user_obj, "role": role, "role_label": role_map.get(role, role)})

    return render(
        request,
        "accounts/user_role_manage.html",
        {
            "user_rows": user_rows,
            "role_choices": role_choices,
            "keyword": keyword,
            "page_obj": page_obj,
        },
    )


class StaffLoginView(LoginView):
    """登录成功后按角色跳转。"""

    authentication_form = StyledAuthenticationForm
    redirect_authenticated_user = True

    def get_success_url(self):
        nxt = self.get_redirect_url()
        if nxt:
            return nxt
        user = self.request.user
        if user_is_admin(user):
            return "/"
        if user.groups.filter(name=STAFF_GROUP).exists():
            return reverse("staff_workbench")
        return reverse("visitor_index")


@login_required
def login_redirect(request):
    """兼容 LOGIN_REDIRECT_URL 指向命名路由的场景。"""
    if user_is_admin(request.user):
        return HttpResponseRedirect("/")
    if request.user.groups.filter(name=STAFF_GROUP).exists():
        return HttpResponseRedirect(reverse("staff_workbench"))
    return HttpResponseRedirect(reverse("visitor_index"))


@staff_or_admin_required
def staff_workbench(request):
    from records.models import PlayRecord

    today = timezone.localdate()
    week_start = today - timedelta(days=6)

    base_qs = PlayRecord.objects.all()
    mine_qs = base_qs.filter(created_by=request.user)
    if user_is_admin(request.user):
        scope_qs = base_qs
        scope_label = "全平台"
    else:
        scope_qs = mine_qs
        scope_label = "本人录入"

    today_records = scope_qs.filter(play_time__date=today)
    week_records = scope_qs.filter(play_time__date__gte=week_start, play_time__date__lte=today)

    agg_today = today_records.aggregate(
        visits=Count("id"),
        repeats=Sum("repeat_count"),
        queue_sum=Sum("queue_time"),
    )

    top_projects_week = week_records.values("project__name").annotate(visits=Count("id")).order_by("-visits")[:5]
    recent_records = mine_qs.select_related("project").order_by("-created_at")[:10]

    queue_alert_rows = []
    for project in Project.objects.all().order_by("name"):
        reasons = []
        if project.capacity > 0 and project.queue_count >= project.capacity:
            reasons.append(f"排队人数 {project.queue_count} 达到/超过承载量 {project.capacity}")
        if project.daily_warn_threshold > 0 and project.queue_count >= project.daily_warn_threshold:
            reasons.append(f"排队人数 {project.queue_count} 达到/超过日预警阈值 {project.daily_warn_threshold}")
        day_visits = PlayRecord.objects.filter(project=project, play_time__date=today).count()
        if project.daily_warn_threshold > 0 and day_visits >= project.daily_warn_threshold:
            reasons.append(f"当日记录 {day_visits} 达到/超过日预警阈值 {project.daily_warn_threshold}")
        if reasons:
            queue_alert_rows.append({"name": project.name, "reasons": reasons})

    status_map = dict(Project.STATUS_CHOICES)
    project_queue_rows = [
        {
            "id": project.id,
            "name": project.name,
            "queue_count": project.queue_count,
            "cycle_minutes": project.cycle_minutes,
            "status": project.status,
            "status_display": status_map.get(project.status, project.status),
            "updated_at": timezone.localtime(project.updated_at),
        }
        for project in Project.objects.all().order_by("name")
    ]

    return render(
        request,
        "staff/workbench.html",
        {
            "scope_label": scope_label,
            "today": today,
            "week_start": week_start,
            "today_visits": agg_today.get("visits") or 0,
            "today_repeats": agg_today.get("repeats") or 0,
            "today_queue_sum": agg_today.get("queue_sum") or 0,
            "top_projects_week": list(top_projects_week),
            "recent_records": recent_records,
            "queue_alert_rows": queue_alert_rows,
            "project_queue_rows": project_queue_rows,
        },
    )


@staff_or_admin_required
def staff_project_queues_api(request):
    if request.method != "GET":
        return JsonResponse({"code": 405, "message": "method not allowed"}, status=405)

    status_map = dict(Project.STATUS_CHOICES)
    rows = []
    for project in Project.objects.all().order_by("name"):
        rows.append(
            {
                "id": project.id,
                "name": project.name,
                "queue_count": project.queue_count,
                "cycle_minutes": project.cycle_minutes,
                "status": project.status,
                "status_display": status_map.get(project.status, project.status),
                "updated_at": timezone.localtime(project.updated_at).strftime("%Y-%m-%d %H:%M:%S"),
            }
        )
    return JsonResponse({"code": 0, "message": "ok", "data": {"rows": rows}})
