import json

from django.contrib import messages
from django.db.models import Count
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from core.auth_utils import staff_or_admin_required
from core.audit import log_action
from .forms import ProjectCreateForm, ProjectForm
from .location_defaults import DEFAULT_CENTER, REGION_CENTER, initial_marker_latlng, safe_latlng
from .models import Project


def _map_display_latlng(form: ProjectForm, project: Project) -> tuple[float, float]:
    """地图初始标记：优先表单当前值（含校验失败时用户已填写内容），否则用项目已存或区域默认。"""
    raw_lat = form["latitude"].value()
    raw_lng = form["longitude"].value()
    if raw_lat not in (None, "") and raw_lng not in (None, ""):
        coords = safe_latlng(raw_lat, raw_lng)
        if coords is not None:
            return coords
    return initial_marker_latlng(project)

@staff_or_admin_required
def project_list(request):
    """项目列表与新增。"""
    if request.method == "POST":
        form = ProjectCreateForm(request.POST)
        if form.is_valid():
            project = form.save()
            if not project.region:
                project.region = project.effective_region()
                project.save(update_fields=["region"])
            log_action(request, "project_create", target_type="Project", target_id=project.id, message=project.name)
            messages.success(request, f"项目“{project.name}”已创建。")
            return redirect("project_list")
    else:
        form = ProjectCreateForm()

    keyword = request.GET.get("keyword", "").strip()
    status = request.GET.get("status", "").strip()
    project_type = request.GET.get("project_type", "").strip()

    projects = Project.objects.annotate(record_count=Count("records"))
    if keyword:
        projects = projects.filter(name__icontains=keyword)
    if status:
        projects = projects.filter(status=status)
    if project_type:
        projects = projects.filter(project_type=project_type)

    return render(
        request,
        "projects/project_list.html",
        {
            "form": form,
            "projects": projects,
            "keyword": keyword,
            "status": status,
            "project_type": project_type,
            "status_choices": Project.STATUS_CHOICES,
            "type_choices": Project.TYPE_CHOICES,
        },
    )


@staff_or_admin_required
def project_edit(request, project_id):
    project = get_object_or_404(Project, id=project_id)
    if request.method == "POST":
        form = ProjectForm(request.POST, request.FILES, instance=project)
        if form.is_valid():
            form.save()
            if not project.region:
                project.region = project.effective_region()
                project.save(update_fields=["region"])
            log_action(request, "project_update", target_type="Project", target_id=project.id, message=project.name)
            messages.success(request, f"项目“{project.name}”已更新。")
            return redirect("project_list")
    else:
        form = ProjectForm(instance=project)

    init_lat, init_lng = _map_display_latlng(form, project)
    region_centers = {k: {"lat": v[0], "lng": v[1]} for k, v in REGION_CENTER.items()}
    return render(
        request,
        "projects/project_edit.html",
        {
            "form": form,
            "project": project,
            "map_init_lat": init_lat,
            "map_init_lng": init_lng,
            "map_default_lat": DEFAULT_CENTER[0],
            "map_default_lng": DEFAULT_CENTER[1],
            "region_centers_json": json.dumps(region_centers),
        },
    )


@staff_or_admin_required
def project_delete(request, project_id):
    project = get_object_or_404(Project, id=project_id)
    record_count = project.records.count()
    if request.method == "POST":
        name = project.name
        project.delete()
        log_action(
            request,
            "project_delete",
            target_type="Project",
            target_id=str(project_id),
            message=f"删除项目「{name}」，已级联删除游玩记录 {record_count} 条",
        )
        messages.warning(request, f"已删除项目「{name}」，并移除关联游玩记录 {record_count} 条。")
        return redirect("project_list")
    return render(
        request,
        "projects/project_delete_confirm.html",
        {"project": project, "record_count": record_count},
    )


@staff_or_admin_required
def project_toggle_status(request, project_id):
    project = get_object_or_404(Project, id=project_id)
    cycle = {
        Project.STATUS_NORMAL: Project.STATUS_MAINTENANCE,
        Project.STATUS_MAINTENANCE: Project.STATUS_CLOSED,
        Project.STATUS_CLOSED: Project.STATUS_NORMAL,
    }
    project.status = cycle[project.status]
    project.save(update_fields=["status", "updated_at"])
    log_action(request, "project_toggle_status", target_type="Project", target_id=project.id, message=project.get_status_display())
    messages.info(request, f"项目“{project.name}”状态已切换为：{project.get_status_display()}。")
    return redirect("project_list")


@require_POST
def queue_update_count_api(request, project_id):
    """
    第三方扫码/排队系统接入预留接口（当前仅支持推送排队人数）。
    鉴权占位：X-Queue-Api-Key == settings.QUEUE_API_KEY。
    """
    from django.conf import settings

    if request.headers.get("X-Queue-Api-Key", "") != settings.QUEUE_API_KEY:
        return JsonResponse({"code": 401, "message": "unauthorized"}, status=401)

    project = get_object_or_404(Project, id=project_id)
    raw_count = request.POST.get("queue_count", "").strip()
    try:
        queue_count = int(raw_count)
    except ValueError:
        return JsonResponse({"code": 400, "message": "queue_count must be integer"}, status=400)
    if queue_count < 0:
        return JsonResponse({"code": 400, "message": "queue_count must be >= 0"}, status=400)

    project.queue_count = queue_count
    project.save(update_fields=["queue_count", "updated_at"])
    log_action(
        request,
        "project_queue_update",
        target_type="Project",
        target_id=str(project.id),
        message=f"{project.name} queue_count={queue_count}",
    )
    return JsonResponse(
        {
            "code": 0,
            "message": "ok",
            "data": {
                "project_id": project.id,
                "project_name": project.name,
                "queue_count": project.queue_count,
                "cycle_minutes": project.cycle_minutes,
            },
        }
    )
