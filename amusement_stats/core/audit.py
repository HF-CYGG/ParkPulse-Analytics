from .models import AuditLog


def get_client_ip(request):
    xff = request.META.get("HTTP_X_FORWARDED_FOR")
    if xff:
        return xff.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR")


def log_action(request, action: str, *, target_type: str = "", target_id: str = "", message: str = ""):
    AuditLog.objects.create(
        action=action,
        actor=getattr(request, "user", None) if getattr(getattr(request, "user", None), "is_authenticated", False) else None,
        target_type=target_type,
        target_id=str(target_id) if target_id is not None else "",
        message=message,
        ip=get_client_ip(request),
        path=request.path,
    )

