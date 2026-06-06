from django.contrib.auth.forms import AuthenticationForm


class StyledAuthenticationForm(AuthenticationForm):
    """登录页：为 Bootstrap 输入框补充样式类。"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        base = {"class": "form-control form-control-lg"}
        self.fields["username"].widget.attrs.update(
            {
                **base,
                "placeholder": "账号 / 昵称 / 手机号 / 邮箱",
                "autocomplete": "username",
                "autofocus": True,
            }
        )
        self.fields["password"].widget.attrs.update(
            {
                **base,
                "placeholder": "密码",
                "autocomplete": "current-password",
            }
        )
