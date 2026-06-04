from django.conf import settings
from django.contrib.auth.views import redirect_to_login
from django.core.exceptions import PermissionDenied
from django.shortcuts import resolve_url


class StaffRequiredMixin:
    """Restreint une vue aux utilisateurs staff ou superusers."""

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect_to_login(
                request.get_full_path(),
                resolve_url(settings.LOGIN_URL),
            )
        if not (request.user.is_staff or request.user.is_superuser):
            raise PermissionDenied
        return super().dispatch(request, *args, **kwargs)
