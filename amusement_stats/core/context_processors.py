from .auth_utils import user_is_admin, user_is_staff_or_admin


def rbac_flags(request):
    user = getattr(request, "user", None)
    if not user or not getattr(user, "is_authenticated", False):
        return {"is_admin": False, "is_staff_or_admin": False}
    return {
        "is_admin": user_is_admin(user),
        "is_staff_or_admin": user_is_staff_or_admin(user),
    }

