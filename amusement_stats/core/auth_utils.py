from functools import wraps

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect


ADMIN_GROUP = "admin"
STAFF_GROUP = "staff"


def user_is_admin(user):
    return user.is_superuser or user.groups.filter(name=ADMIN_GROUP).exists()


def user_is_staff_or_admin(user):
    return user_is_admin(user) or user.groups.filter(name=STAFF_GROUP).exists()


def admin_required(view_func):
    @login_required
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not user_is_admin(request.user):
            messages.error(request, "无权限访问：仅管理员可操作。")
            return redirect("index")
        return view_func(request, *args, **kwargs)

    return wrapper


def staff_or_admin_required(view_func):
    @login_required
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not user_is_staff_or_admin(request.user):
            messages.error(request, "无权限访问：请联系管理员分配角色。")
            return redirect("login")
        return view_func(request, *args, **kwargs)

    return wrapper

