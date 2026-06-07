"""核心后台视图：负责系统设置、审计日志、游客反馈与行程模板管理等管理员页面逻辑。"""

from django.contrib import admin, messages
from django.contrib.admin.models import LogEntry
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from core.auth_utils import admin_required
from core.audit import log_action
from core.models import AuditLog, SiteConfig
from projects.models import Project
from visitor.models import ItineraryPlan, ItineraryPlanItem, VisitorFeedback, VisitorFeedbackMessage
from visitor.preferences import PREFERENCE_TAG_CHOICES, clean_preference_values


def _parse_feedback_or_redirect(request):
    """统一解析反馈主键，失败时直接返回提示和跳转响应。"""

    feedback_id = request.POST.get("feedback_id", "").strip()
    if not feedback_id:
        messages.error(request, "参数无效")
        return None, redirect("visitor_feedback_manage")
    try:
        feedback_id_int = int(feedback_id)
    except ValueError:
        messages.error(request, "参数无效")
        return None, redirect("visitor_feedback_manage")
    return get_object_or_404(VisitorFeedback, id=feedback_id_int), None


def _reply_visitor_feedback(request, feedback):
    """管理员回复游客反馈，并同步把会话标记为已处理。"""

    content = request.POST.get("reply_content", "").strip()
    if not content:
        messages.error(request, "回复内容不能为空")
        return redirect("visitor_feedback_manage")
    VisitorFeedbackMessage.objects.create(
        feedback=feedback,
        sender=VisitorFeedbackMessage.SENDER_ADMIN,
        content=content,
        read_by_admin=True,
        read_by_visitor=False,
    )
    feedback.status = VisitorFeedback.STATUS_RESOLVED
    feedback.resolved_at = timezone.now()
    feedback.save(update_fields=["status", "resolved_at"])
    log_action(
        request,
        "visitor_feedback_reply",
        target_type="VisitorFeedback",
        target_id=str(feedback.id),
        message=f"回复反馈 id={feedback.id}",
    )
    messages.success(request, "回复已发送")
    return redirect("visitor_feedback_manage")


def _resolve_visitor_feedback(request, feedback):
    """把反馈标记为已处理，重复操作时保持幂等。"""

    if feedback.status != VisitorFeedback.STATUS_RESOLVED:
        feedback.status = VisitorFeedback.STATUS_RESOLVED
        feedback.resolved_at = timezone.now()
        feedback.save(update_fields=["status", "resolved_at"])
        log_action(
            request,
            "visitor_feedback_resolve",
            target_type="VisitorFeedback",
            target_id=str(feedback.id),
            message=f"标记已处理 id={feedback.id} user={feedback.user.username}",
        )
        messages.success(request, "已标记为已处理")
    return redirect("visitor_feedback_manage")


def _reopen_visitor_feedback(request, feedback):
    """把反馈重新打开到待处理状态。"""

    feedback.status = VisitorFeedback.STATUS_PENDING
    feedback.resolved_at = None
    feedback.save(update_fields=["status", "resolved_at"])
    log_action(
        request,
        "visitor_feedback_reopen",
        target_type="VisitorFeedback",
        target_id=str(feedback.id),
        message=f"重新打开 id={feedback.id}",
    )
    messages.info(request, "已改回待处理")
    return redirect("visitor_feedback_manage")


def _delete_visitor_feedback(request, feedback):
    """删除反馈并写入审计日志，便于后台追溯。"""

    feedback_id = feedback.id
    username = feedback.user.username
    preview = (feedback.title or feedback.content or "")[:40]
    feedback.delete()
    log_action(
        request,
        "visitor_feedback_delete",
        target_type="VisitorFeedback",
        target_id=str(feedback_id),
        message=f"删除反馈 id={feedback_id} user={username} {preview}",
    )
    messages.warning(request, "该条反馈已删除")
    return redirect("visitor_feedback_manage")


def _handle_visitor_feedback_manage_post(request):
    """分发反馈管理页的 POST 操作，降低主视图分支复杂度。"""

    feedback, early_response = _parse_feedback_or_redirect(request)
    if early_response:
        return early_response

    operation = request.POST.get("op", "").strip()
    handlers = {
        "reply": _reply_visitor_feedback,
        "resolve": _resolve_visitor_feedback,
        "reopen": _reopen_visitor_feedback,
        "delete": _delete_visitor_feedback,
    }
    handler = handlers.get(operation)
    if not handler:
        messages.error(request, "未知操作")
        return redirect("visitor_feedback_manage")
    return handler(request, feedback)


def _create_itinerary_plan(request):
    """创建行程模板并对人群字段做基础兜底。"""

    name = request.POST.get("name", "").strip()
    audience = request.POST.get("audience", ItineraryPlan.AUDIENCE_FAMILY).strip()
    preference_tag = clean_preference_values([request.POST.get("preference_tag", "").strip()])
    description = request.POST.get("description", "").strip()
    if not name:
        messages.error(request, "方案名称不能为空")
        return redirect("itinerary_plan_manage")
    valid_audiences = {value for value, _ in ItineraryPlan.AUDIENCE_CHOICES}
    if audience not in valid_audiences:
        audience = ItineraryPlan.AUDIENCE_FAMILY
    plan = ItineraryPlan.objects.create(
        name=name,
        audience=audience,
        preference_tag=preference_tag,
        description=description,
    )
    log_action(request, "itinerary_plan_create", target_type="ItineraryPlan", target_id=str(plan.id), message=plan.name)
    messages.success(request, "行程模板已创建")
    return redirect("itinerary_plan_manage")


def _add_itinerary_plan_item(request):
    """为指定模板新增或更新一个顺序节点。"""

    plan_id = request.POST.get("plan_id", "").strip()
    project_id = request.POST.get("project_id", "").strip()
    seq = request.POST.get("seq", "1").strip()
    tip = request.POST.get("tip", "").strip()
    if not plan_id:
        messages.error(request, "请选择模板后再保存节点")
        return redirect("itinerary_plan_manage")
    if not project_id:
        messages.error(request, "请选择项目后再保存节点")
        return redirect("itinerary_plan_manage")
    try:
        plan_id_int = int(plan_id)
        project_id_int = int(project_id)
    except ValueError:
        messages.error(request, "模板或项目参数无效")
        return redirect("itinerary_plan_manage")

    plan = get_object_or_404(ItineraryPlan, id=plan_id_int)
    try:
        seq_int = max(1, int(seq))
    except ValueError:
        messages.error(request, "顺序必须为正整数")
        return redirect("itinerary_plan_manage")
    project = get_object_or_404(Project, id=project_id_int)

    ItineraryPlanItem.objects.update_or_create(
        plan=plan,
        seq=seq_int,
        defaults={"project": project, "tip": tip},
    )
    log_action(request, "itinerary_plan_item_add", target_type="ItineraryPlan", target_id=str(plan.id), message=f"seq={seq_int}")
    messages.success(request, "已保存行程节点")
    return redirect("itinerary_plan_manage")


def _toggle_itinerary_plan(request):
    """切换模板启用状态。"""

    plan_id = request.POST.get("plan_id", "").strip()
    if not plan_id:
        messages.error(request, "模板参数不能为空")
        return redirect("itinerary_plan_manage")
    try:
        plan_id_int = int(plan_id)
    except ValueError:
        messages.error(request, "模板参数无效")
        return redirect("itinerary_plan_manage")

    plan = get_object_or_404(ItineraryPlan, id=plan_id_int)
    plan.is_active = not plan.is_active
    plan.save(update_fields=["is_active", "updated_at"])
    log_action(request, "itinerary_plan_toggle", target_type="ItineraryPlan", target_id=str(plan.id), message=str(plan.is_active))
    messages.info(request, "模板状态已更新")
    return redirect("itinerary_plan_manage")


def _handle_itinerary_plan_manage_post(request):
    """分发行程模板管理页 POST 操作，减少主视图认知复杂度。"""

    operation = request.POST.get("op", "").strip()
    handlers = {
        "create_plan": _create_itinerary_plan,
        "add_item": _add_itinerary_plan_item,
        "toggle_plan": _toggle_itinerary_plan,
    }
    handler = handlers.get(operation)
    if not handler:
        messages.error(request, "未知操作")
        return redirect("itinerary_plan_manage")
    return handler(request)


@admin_required
def system_management_home(request):
    available_apps = admin.site.get_app_list(request)
    for app_info in available_apps:
        app_info["models"] = [
            model for model in app_info.get("models", []) if model.get("add_url") or model.get("admin_url")
        ]
    available_apps = [app for app in available_apps if app.get("models")]

    recent_actions = LogEntry.objects.select_related("user", "content_type").order_by("-action_time")[:12]
    my_actions = (
        LogEntry.objects.select_related("user", "content_type").filter(user=request.user).order_by("-action_time")[:12]
    )

    return render(
        request,
        "core/system_management_home.html",
        {
            "available_apps": available_apps,
            "recent_actions": recent_actions,
            "my_actions": my_actions,
        },
    )


@admin_required
def system_settings(request):
    config = SiteConfig.get_solo()
    if request.method == "POST":
        default_days = request.POST.get("default_days", "7").strip()
        page_size = request.POST.get("page_size", "10").strip()
        ui_theme = request.POST.get("ui_theme", "light").strip()
        operating_hours_text = request.POST.get("operating_hours_text", "").strip()

        try:
            default_days_int = min(max(int(default_days), 1), 30)
        except ValueError:
            default_days_int = 7
        try:
            page_size_int = min(max(int(page_size), 5), 100)
        except ValueError:
            page_size_int = 10
        if ui_theme not in {"light", "dark"}:
            ui_theme = "light"

        request.session["default_days"] = default_days_int
        request.session["page_size"] = page_size_int
        request.session["ui_theme"] = ui_theme
        config.operating_hours_text = operating_hours_text or "10:00-21:00"
        config.save(update_fields=["operating_hours_text", "updated_at"])
        log_action(request, "settings_update", target_type="system", target_id="settings", message="更新系统设置")
        messages.success(request, "系统设置已保存")
        return redirect("system_settings_ui")

    return render(
        request,
        "core/system_settings.html",
        {
            "default_days": request.session.get("default_days", 7),
            "page_size": request.session.get("page_size", 10),
            "ui_theme": request.session.get("ui_theme", "light"),
            "operating_hours_text": config.operating_hours_text,
        },
    )


@admin_required
def audit_logs(request):
    logs = AuditLog.objects.select_related("actor")[:200]
    return render(request, "core/audit_logs.html", {"logs": logs})


@admin_required
def visitor_feedback_manage(request):
    """管理员：游客反馈会话列表、回复、状态标记、删除。"""
    if request.method == "POST":
        return _handle_visitor_feedback_manage_post(request)

    status_filter = request.GET.get("status", "").strip()
    qs = VisitorFeedback.objects.select_related("user").order_by("-created_at")
    if status_filter in {VisitorFeedback.STATUS_PENDING, VisitorFeedback.STATUS_RESOLVED}:
        qs = qs.filter(status=status_filter)
    qs = qs.prefetch_related("messages")

    rows = []
    for fb in qs[:500]:
        last_msg = fb.messages.last()
        unread_cnt = fb.messages.filter(sender=VisitorFeedbackMessage.SENDER_VISITOR, read_by_admin=False).count()
        rows.append({"fb": fb, "last_msg": last_msg, "unread_cnt": unread_cnt})

    return render(
        request,
        "core/visitor_feedback_manage.html",
        {
            "feedback_rows": rows,
            "status_filter": status_filter,
            "status_choices": VisitorFeedback.STATUS_CHOICES,
        },
    )


@admin_required
def visitor_feedback_detail(request, feedback_id: int):
    fb = get_object_or_404(VisitorFeedback.objects.select_related("user"), id=feedback_id)

    if request.method == "POST":
        op = request.POST.get("op", "").strip()
        if op == "reply":
            content = request.POST.get("reply_content", "").strip()
            if not content:
                messages.error(request, "回复内容不能为空")
                return redirect("visitor_feedback_detail", feedback_id=fb.id)
            VisitorFeedbackMessage.objects.create(
                feedback=fb,
                sender=VisitorFeedbackMessage.SENDER_ADMIN,
                content=content,
                read_by_admin=True,
                read_by_visitor=False,
            )
            fb.status = VisitorFeedback.STATUS_RESOLVED
            fb.resolved_at = timezone.now()
            fb.save(update_fields=["status", "resolved_at"])
            log_action(request, "visitor_feedback_reply", target_type="VisitorFeedback", target_id=str(fb.id), message="详情页回复")
            messages.success(request, "回复已发送")
            return redirect("visitor_feedback_detail", feedback_id=fb.id)
        if op == "resolve":
            fb.status = VisitorFeedback.STATUS_RESOLVED
            fb.resolved_at = timezone.now()
            fb.save(update_fields=["status", "resolved_at"])
            log_action(request, "visitor_feedback_resolve", target_type="VisitorFeedback", target_id=str(fb.id), message="详情页标记已处理")
            messages.success(request, "已标记为已处理")
            return redirect("visitor_feedback_detail", feedback_id=fb.id)
        if op == "reopen":
            fb.status = VisitorFeedback.STATUS_PENDING
            fb.resolved_at = None
            fb.save(update_fields=["status", "resolved_at"])
            log_action(request, "visitor_feedback_reopen", target_type="VisitorFeedback", target_id=str(fb.id), message="详情页改回待处理")
            messages.info(request, "已改回待处理")
            return redirect("visitor_feedback_detail", feedback_id=fb.id)

    messages_qs = fb.messages.all()
    messages_qs.filter(sender=VisitorFeedbackMessage.SENDER_VISITOR, read_by_admin=False).update(read_by_admin=True)
    return render(request, "core/visitor_feedback_detail.html", {"feedback": fb, "messages": messages_qs})


@admin_required
def itinerary_plan_manage(request):
    if request.method == "POST":
        return _handle_itinerary_plan_manage_post(request)

    plans = ItineraryPlan.objects.prefetch_related("items__project").order_by("name")
    projects = Project.objects.order_by("name")

    return render(
        request,
        "core/itinerary_plan_manage.html",
        {
            "plans": plans,
            "projects": projects,
            "audience_choices": ItineraryPlan.AUDIENCE_CHOICES,
            "preference_tag_choices": PREFERENCE_TAG_CHOICES,
        },
    )
