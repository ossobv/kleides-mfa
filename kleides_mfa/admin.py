# -*- coding: utf-8 -*-
from __future__ import absolute_import, unicode_literals

from django.conf import settings
from django.contrib.auth import REDIRECT_FIELD_NAME
from django.contrib.auth.views import redirect_to_login
from django.shortcuts import resolve_url
try:
    from django.utils.http import url_has_allowed_host_and_scheme
except ImportError:  # Django 2.2
    from django.utils.http import (
        is_safe_url as url_has_allowed_host_and_scheme)


class AdminSiteMfaRequiredMixin():
    """
    Mixin for enforcing MFA verified staff users.

    Custom admin views should either be wrapped using :meth:`admin_view` or
    use :meth:`has_permission` in order to secure those views.
    """

    def has_permission(self, request):
        """
        Returns True if the given HttpRequest has permission to view
        *at least one* page in the admin site and uses MFA authentication.
        """
        if not super().has_permission(request):
            return False
        return request.user.is_verified

    def login(self, request, extra_context=None):
        """
        Redirects to the site login page for the given HttpRequest.
        """
        redirect_to = request.POST.get(
            REDIRECT_FIELD_NAME,
            request.GET.get(REDIRECT_FIELD_NAME, '')
        )
        url_is_allowed = url_has_allowed_host_and_scheme(
            url=redirect_to,
            allowed_hosts={request.get_host()},
            require_https=request.is_secure(),
        )

        if not redirect_to or not url_is_allowed:
            redirect_to = resolve_url(settings.LOGIN_REDIRECT_URL)

        return redirect_to_login(redirect_to)
