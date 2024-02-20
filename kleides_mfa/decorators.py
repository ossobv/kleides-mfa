from functools import wraps
from urllib.parse import urlparse

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import REDIRECT_FIELD_NAME
from django.core.exceptions import PermissionDenied
from django.shortcuts import resolve_url
from django.utils.translation import gettext_lazy as _

from .views.mixins import is_recently_verified, is_user_in_setup


def user_passes_test(
    test_func, login_url=None, raise_exception=False,
    redirect_field_name=REDIRECT_FIELD_NAME
):
    '''
    Decorator for views that checks that the user passes the given test,
    redirecting to the log-in page if necessary. The test should be a callable
    that takes the request object and returns True if the user passes.
    If raise_exception is True a PermissionDenied exception is raised instead
    of redicting to the login page.
    '''

    def decorator(view_func):
        @wraps(view_func)
        def _wrapper_view(request, *args, **kwargs):
            if test_func(request):
                return view_func(request, *args, **kwargs)

            if raise_exception:
                raise PermissionDenied

            if request.user.is_verified:
                messages.info(
                    request,
                    _('We need to confirm your identity, please login again.'))

            path = request.build_absolute_uri()
            resolved_login_url = resolve_url(login_url or settings.LOGIN_URL)
            # If the login url is the same scheme and net location then just
            # use the path as the "next" url.
            login_scheme, login_netloc = urlparse(resolved_login_url)[:2]
            current_scheme, current_netloc = urlparse(path)[:2]
            if (not login_scheme or login_scheme == current_scheme) and (
                not login_netloc or login_netloc == current_netloc
            ):
                path = request.get_full_path()
            from django.contrib.auth.views import redirect_to_login

            return redirect_to_login(
                path, resolved_login_url, redirect_field_name)

        return _wrapper_view

    return decorator


def create_decorator(
    function=None, test_func=None, login_url=None, raise_exception=False,
    redirect_field_name=REDIRECT_FIELD_NAME
):
    if not callable(test_func):
        raise ValueError('test_func must be a callable that accepts a request')

    actual_decorator = user_passes_test(
        test_func,
        login_url=login_url, raise_exception=raise_exception,
        redirect_field_name=redirect_field_name,
    )

    if function:
        return actual_decorator(function)

    return actual_decorator


def single_factor_required(*args, **kwargs):
    '''
    Decorator for views that only required a single authentication factor.
    '''
    return create_decorator(
        *args,
        test_func=lambda r: r.user.is_single_factor_authenticated,
        **kwargs)


def multi_factor_required(*args, **kwargs):
    '''
    Decorator for views that require multi factor authentication.
    '''
    return create_decorator(
        *args,
        test_func=lambda r: r.user.is_verified,
        **kwargs)


def recent_multi_factor_required(*args, **kwargs):
    '''
    Decorator for views that require recent multi factor authentication.
    '''
    return create_decorator(*args, test_func=is_recently_verified, **kwargs)


def setup_or_mfa_required(*args, **kwargs):
    '''
    Decorator for views that require multi factor authentication or
    with single factor and is still in the process of account setup.
    '''
    return create_decorator(
        *args,
        test_func=lambda r: r.user.is_verified or is_user_in_setup(r),
        **kwargs)


def setup_or_recent_mfa_required(*args, **kwargs):
    '''
    Decorator for views that require recent multi factor authentication or
    with single factor and is still in the process of account setup.
    '''
    return create_decorator(
        *args,
        test_func=lambda r: is_recently_verified(r) or is_user_in_setup(r),
        **kwargs)
