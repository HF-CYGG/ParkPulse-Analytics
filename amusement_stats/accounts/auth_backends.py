import re
from django.contrib.auth.backends import ModelBackend
from django.contrib.auth import get_user_model

from accounts.models import VisitorProfile


class MultiIdentifierBackend(ModelBackend):
    """支持账号/昵称/手机号/邮箱单字段登录。"""

    def authenticate(self, request, username=None, password=None, **kwargs):
        identifier = (username or kwargs.get("username") or "").strip()
        if not identifier or password is None:
            return None

        User = get_user_model()
        user_obj = None

        # 邮箱
        if "@" in identifier:
            user_obj = User.objects.filter(email__iexact=identifier).first()
        # 手机号（仅数字，可含+）
        elif re.fullmatch(r"\+?\d{6,20}", identifier):
            profile = VisitorProfile.objects.select_related("user").filter(phone=identifier).first()
            if profile:
                user_obj = profile.user

        # 账号 / 昵称兜底
        if user_obj is None:
            user_obj = User.objects.filter(username__iexact=identifier).first()
        if user_obj is None:
            profile = VisitorProfile.objects.select_related("user").filter(nickname__iexact=identifier).first()
            if profile:
                user_obj = profile.user

        if user_obj and user_obj.check_password(password) and self.user_can_authenticate(user_obj):
            return user_obj
        return None
