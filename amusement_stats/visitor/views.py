"""游客端视图：负责游客首页、项目浏览、收藏反馈、行程规划与个人中心等页面的展示逻辑。"""

import json

from django.contrib import messages
from django.contrib.auth import update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import PasswordChangeForm
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST, require_http_methods

from accounts.models import VisitorProfile
from analytics.services.recommendations import build_recommendations
from core.auth_utils import STAFF_GROUP, user_is_admin
from core.models import SiteConfig
from projects.models import Project

from .forms import FeedbackForm, FeedbackReplyForm, VisitorProfileForm
from .models import ItineraryPlan, VisitorFavorite, VisitorFeedback, VisitorFeedbackMessage
from .services import public_hot_ranking
from .weather import build_weather_tip, fetch_park_weather


def _favorite_ids_for_user(request):
    if not request.user.is_authenticated:
        return set()
    return set(VisitorFavorite.objects.filter(user=request.user).values_list("project_id", flat=True))


def visitor_index(request):
    hot_rows = public_hot_ranking(days=7, top_n=8)
    open_count = Project.objects.exclude(status=Project.STATUS_CLOSED).count()
    total = Project.objects.count()
    wx = fetch_park_weather()
    weather_line, weather_tip = build_weather_tip(wx)
    operating_hours_text = SiteConfig.get_solo().operating_hours_text or "10:00-21:00（以现场公告为准）"
    return render(
        request,
        "visitor/index.html",
        {
            "hot_rows": hot_rows,
            "open_count": open_count,
            "project_total": total,
            "weather_line": weather_line,
            "weather_tip": weather_tip,
            "operating_hours_text": operating_hours_text,
        },
    )


def visitor_project_list(request):
    qs = Project.objects.all()
    project_type = request.GET.get("type", "").strip()
    region = request.GET.get("region", "").strip()
    status = request.GET.get("status", "").strip()
    keyword = request.GET.get("q", "").strip()

    if project_type:
        qs = qs.filter(project_type=project_type)
    if region:
        qs = qs.filter(region=region)
    if status:
        qs = qs.filter(status=status)
    if keyword:
        qs = qs.filter(name__icontains=keyword)

    wx = fetch_park_weather()
    weather_line, weather_tip = build_weather_tip(wx)

    return render(
        request,
        "visitor/project_list.html",
        {
            "projects": qs,
            "filter_type": project_type,
            "filter_region": region,
            "filter_status": status,
            "keyword": keyword,
            "type_choices": Project.TYPE_CHOICES,
            "region_choices": Project.REGION_CHOICES,
            "status_choices": Project.STATUS_CHOICES,
            "favorite_project_ids": _favorite_ids_for_user(request),
            "weather_line": weather_line,
            "weather_tip": weather_tip,
        },
    )


def visitor_project_detail(request, project_id):
    project = get_object_or_404(Project, id=project_id)
    fav_ids = _favorite_ids_for_user(request)
    return render(
        request,
        "visitor/project_detail.html",
        {
            "project": project,
            "region_choices": Project.REGION_CHOICES,
            "is_favorited": project.id in fav_ids,
        },
    )


@login_required
def visitor_account(request):
    is_staff_only = request.user.groups.filter(name=STAFF_GROUP).exists() and not user_is_admin(request.user)
    favorite_count = VisitorFavorite.objects.filter(user=request.user).count()
    feedback_count = VisitorFeedback.objects.filter(user=request.user).count()
    unread_admin_reply_count = VisitorFeedbackMessage.objects.filter(
        feedback__user=request.user,
        sender=VisitorFeedbackMessage.SENDER_ADMIN,
        read_by_visitor=False,
    ).count()

    profile, _ = VisitorProfile.objects.get_or_create(user=request.user)

    def build_profile_form(post_data=None):
        """构造资料表单。

        只有资料表单提交时才绑定 POST，避免密码提交失败时把资料表单也绑定成错误状态。
        """

        return VisitorProfileForm(
            post_data,
            instance=profile,
            user=request.user,
            initial={
                "account": request.user.username,
                "email": request.user.email,
                "phone": profile.phone or request.user.first_name,
            },
        )

    def build_password_form(post_data=None):
        """构造密码表单。

        只有密码表单提交时才绑定 POST，避免资料保存失败时把密码表单误判为缺少必填字段。
        """

        password_form = PasswordChangeForm(request.user, post_data)
        for field in password_form.fields.values():
            field.widget.attrs["class"] = "form-control"
        return password_form

    profile_form = build_profile_form()
    pwd_form = build_password_form()

    if request.method == "POST":
        op = request.POST.get("op", "").strip()
        if op == "update_profile":
            # 只绑定资料表单，让页面明确显示资料字段错误，同时保持密码表单为未提交状态。
            profile_form = build_profile_form(request.POST)
            if profile_form.is_valid():
                profile_form.save()
                request.user.username = profile_form.cleaned_data["account"].strip()
                request.user.email = profile_form.cleaned_data.get("email", "").strip()
                request.user.first_name = ""
                request.user.save(update_fields=["username", "email", "first_name"])
                messages.success(request, "个人资料已更新")
                return redirect("visitor_account")
            messages.error(request, "个人资料更新失败，请检查输入")
        elif op == "change_password":
            # 只绑定密码表单，让旧密码错误、两次密码不一致等提示可以准确回显。
            pwd_form = build_password_form(request.POST)
            if pwd_form.is_valid():
                user = pwd_form.save()
                # Django 改密后默认会让旧会话签名失效，这里主动刷新当前会话哈希，保持登录态不掉线。
                update_session_auth_hash(request, user)
                messages.success(request, "密码已更新")
                return redirect("visitor_account")
            messages.error(request, "密码修改失败，请检查输入")

    return render(
        request,
        "visitor/account.html",
        {
            "is_staff_only": is_staff_only,
            "favorite_count": favorite_count,
            "feedback_count": feedback_count,
            "unread_admin_reply_count": unread_admin_reply_count,
            "profile_form": profile_form,
            "pwd_form": pwd_form,
        },
    )


@login_required
def visitor_favorites(request):
    favorites = VisitorFavorite.objects.filter(user=request.user).select_related("project").order_by("-created_at")
    return render(request, "visitor/favorites.html", {"favorites": favorites})


@login_required
def visitor_feedback(request):
    form = FeedbackForm()
    reply_form = FeedbackReplyForm(request.POST or None)

    if request.method == "POST":
        op = request.POST.get("op", "").strip()
        if op == "new_feedback":
            form = FeedbackForm(request.POST)
            if form.is_valid():
                fb = form.save(commit=False)
                fb.user = request.user
                fb.save()
                VisitorFeedbackMessage.objects.create(
                    feedback=fb,
                    sender=VisitorFeedbackMessage.SENDER_VISITOR,
                    content=fb.content,
                    read_by_visitor=True,
                    read_by_admin=False,
                )
                messages.success(request, "反馈已提交，感谢你的意见")
                return redirect("visitor_feedback")
            messages.error(request, "请检查反馈内容是否填写完整")
        elif op == "reply":
            feedback_id = request.POST.get("feedback_id", "").strip()
            fb = get_object_or_404(VisitorFeedback, id=feedback_id, user=request.user)
            if reply_form.is_valid():
                VisitorFeedbackMessage.objects.create(
                    feedback=fb,
                    sender=VisitorFeedbackMessage.SENDER_VISITOR,
                    content=reply_form.cleaned_data["content"].strip(),
                    read_by_visitor=True,
                    read_by_admin=False,
                )
                fb.status = VisitorFeedback.STATUS_PENDING
                fb.resolved_at = None
                fb.save(update_fields=["status", "resolved_at"])
                messages.success(request, "消息已发送，管理员会尽快回复")
                return redirect("visitor_feedback")
            messages.error(request, "消息内容不能为空")
    else:
        form = FeedbackForm()
        reply_form = FeedbackReplyForm()

    feedbacks = VisitorFeedback.objects.filter(user=request.user).prefetch_related("messages").order_by("-created_at")[:50]
    for fb in feedbacks:
        fb.unread_admin_count = fb.messages.filter(
            sender=VisitorFeedbackMessage.SENDER_ADMIN,
            read_by_visitor=False,
        ).count()
    VisitorFeedbackMessage.objects.filter(
        feedback__user=request.user,
        sender=VisitorFeedbackMessage.SENDER_ADMIN,
        read_by_visitor=False,
    ).update(read_by_visitor=True)

    return render(
        request,
        "visitor/feedback.html",
        {
            "feedback_form": form,
            "feedbacks": feedbacks,
            "reply_form": reply_form,
        },
    )


@login_required
@require_POST
def visitor_toggle_favorite(request):
    raw_id = request.POST.get("project_id", "")
    try:
        pid = int(raw_id)
    except (TypeError, ValueError):
        messages.error(request, "无效的项目")
        return redirect("visitor_index")

    project = get_object_or_404(Project, id=pid)
    next_url = (request.POST.get("next") or "").strip()
    if not (next_url.startswith("/") and not next_url.startswith("//")):
        next_url = ""

    fav, created = VisitorFavorite.objects.get_or_create(user=request.user, project=project)
    if not created:
        fav.delete()
        messages.info(request, "已取消收藏")
    else:
        messages.success(request, "已加入收藏")

    if next_url:
        return redirect(next_url)
    return redirect("visitor_project_detail", project_id=project.id)


def visitor_analytics(request):
    try:
        from .explore_charts import build_play_analytics_html

        plot_html = build_play_analytics_html()
    except ModuleNotFoundError as e:
        name = getattr(e, "name", None) or "plotly"
        plot_html = (
            '<div class="alert alert-warning mb-0">'
            f"交互图表需要安装 <code>{name}</code>。请在项目目录执行："
            "<code>pip install -r requirements.txt</code>（或 <code>pip install plotly</code>）。"
            "</div>"
        )
    return render(request, "visitor/analytics.html", {"plot_html": plot_html})


def visitor_map(request):
    try:
        from .explore_charts import build_folium_map_html

        map_html = build_folium_map_html()
    except ModuleNotFoundError as e:
        name = getattr(e, "name", None) or "folium"
        map_html = (
            '<div class="alert alert-warning mb-0">'
            f"地图需要安装 <code>{name}</code>。请在项目目录执行："
            "<code>pip install -r requirements.txt</code>（或 <code>pip install folium</code>）。"
            "</div>"
        )
    return render(request, "visitor/map.html", {"map_html": map_html})


def visitor_api_hot(request):
    """公开 JSON：热门参考（档位化，不含原始人次）。"""
    days = request.GET.get("days", "7").strip()
    top_n = request.GET.get("top", "10").strip()
    try:
        days_i = max(1, min(int(days), 31))
    except ValueError:
        days_i = 7
    try:
        top_i = max(1, min(int(top_n), 30))
    except ValueError:
        top_i = 10

    data = public_hot_ranking(days=days_i, top_n=top_i)
    return JsonResponse({"code": 0, "message": "ok", "data": {"items": data}})


def visitor_recommendations(request):
    profile_data = _recommendation_profile_from_request(request)
    recommendations = build_recommendations(profile_data)
    if request.method == "POST" and request.user.is_authenticated:
        profile, _ = VisitorProfile.objects.get_or_create(user=request.user)
        profile.preference_tags = profile_data["preference_tags"]
        profile.age_group = profile_data["age_group"]
        profile.consumption_level = profile_data["budget_level"]
        profile.available_minutes = profile_data["available_minutes"]
        profile.budget_amount = profile_data["budget_amount"]
        profile.with_children = profile_data["with_children"]
        profile.with_elderly = profile_data["with_elderly"]
        profile.save(
            update_fields=[
                "preference_tags",
                "age_group",
                "consumption_level",
                "available_minutes",
                "budget_amount",
                "with_children",
                "with_elderly",
                "updated_at",
            ]
        )
        messages.success(request, "已根据你的画像生成推荐路线，并同步保存到个人资料。")
    return render(
        request,
        "visitor/recommendations.html",
        {
            "profile_data": profile_data,
            "recommendations": recommendations,
            "age_choices": VisitorProfile.AGE_CHOICES,
            "budget_choices": VisitorProfile.CONSUMPTION_CHOICES,
        },
    )


@csrf_exempt
@require_http_methods(["GET", "POST"])
def visitor_api_recommendations(request):
    if request.method == "POST":
        try:
            raw = json.loads(request.body.decode("utf-8") or "{}")
        except json.JSONDecodeError:
            raw = request.POST
    else:
        raw = request.GET
    profile_data = _recommendation_profile_from_mapping(raw)
    return JsonResponse(
        {"code": 0, "message": "ok", "data": build_recommendations(profile_data)},
        json_dumps_params={"ensure_ascii": False},
    )


def _recommendation_profile_from_request(request) -> dict:
    if request.method == "POST":
        return _recommendation_profile_from_mapping(request.POST)
    if request.user.is_authenticated:
        profile, _ = VisitorProfile.objects.get_or_create(user=request.user)
        return {
            "age_group": profile.age_group or VisitorProfile.AGE_ADULT,
            "preference_tags": profile.preference_tags or "亲子,低排队",
            "budget_level": profile.consumption_level or VisitorProfile.CONSUMPTION_MEDIUM,
            "available_minutes": profile.available_minutes or 180,
            "budget_amount": profile.budget_amount or 0,
            "with_children": profile.with_children,
            "with_elderly": profile.with_elderly,
        }
    return {
        "age_group": VisitorProfile.AGE_FAMILY,
        "preference_tags": "亲子,低排队",
        "budget_level": VisitorProfile.CONSUMPTION_MEDIUM,
        "available_minutes": 180,
        "budget_amount": 0,
        "with_children": True,
        "with_elderly": False,
    }


def _recommendation_profile_from_mapping(data) -> dict:
    return {
        "age_group": (data.get("age_group") or VisitorProfile.AGE_FAMILY).strip(),
        "preference_tags": (data.get("preference_tags") or "").strip(),
        "budget_level": (data.get("budget_level") or data.get("consumption_level") or VisitorProfile.CONSUMPTION_MEDIUM).strip(),
        "available_minutes": _bounded_int(data.get("available_minutes"), default=180, min_value=30, max_value=720),
        "budget_amount": _bounded_int(data.get("budget_amount"), default=0, min_value=0, max_value=99999),
        "with_children": _truthy(data.get("with_children")),
        "with_elderly": _truthy(data.get("with_elderly")),
    }


def _bounded_int(value, *, default: int, min_value: int, max_value: int) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        parsed = default
    return max(min_value, min(parsed, max_value))


def _truthy(value) -> bool:
    if isinstance(value, bool):
        return value
    return str(value).lower() in {"1", "true", "on", "yes", "是"}


def visitor_itinerary(request):
    plans = ItineraryPlan.objects.filter(is_active=True).prefetch_related("items__project").order_by("name")
    audience = request.GET.get("audience", "").strip()
    preference = request.GET.get("preference", "").strip()
    if audience:
        plans = plans.filter(audience=audience)
    if preference:
        plans = plans.filter(preference_tag__icontains=preference)

    plan_cards = []
    for plan in plans:
        # 先转成列表，避免模板中多次访问 `plan.items.all` 造成重复排序和重复组装。
        items = list(plan.items.all().order_by("seq", "id"))
        plan_cards.append(
            {
                "plan": plan,
                "items": items,
                "preview_items": items[:3],
            }
        )

    preference_options = list(
        ItineraryPlan.objects.exclude(preference_tag="")
        .values_list("preference_tag", flat=True)
        .distinct()
        .order_by("preference_tag")
    )
    return render(
        request,
        "visitor/itinerary.html",
        {
            "plan_cards": plan_cards,
            "audience": audience,
            "preference": preference,
            "preference_options": preference_options,
            "audience_choices": ItineraryPlan.AUDIENCE_CHOICES,
            "current_query": request.GET.urlencode(),
        },
    )


def visitor_itinerary_detail(request, plan_id: int):
    plan = get_object_or_404(
        ItineraryPlan.objects.filter(is_active=True).prefetch_related("items__project"),
        id=plan_id,
    )
    items = list(plan.items.all().order_by("seq", "id"))

    back_query = (request.GET.get("from_qs") or "").strip()
    back_url = reverse("visitor_itinerary")
    if back_query:
        back_url = f"{back_url}?{back_query}"

    return render(
        request,
        "visitor/itinerary_detail.html",
        {
            "plan": plan,
            "items": items,
            "back_url": back_url,
        },
    )
