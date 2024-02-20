'''
These are the available settings, accessed through
``kleides_mfa.conf.app_settings``. All attributes prefixed ``KLEIDES_MFA_*``
can be overridden from your Django project's settings module by defining a
setting with the same name.

For instance, to enable mfa on the the admin interface:

.. code-block:: python

    KLEIDES_MFA_PATCH_ADMIN = True
'''
from __future__ import annotations

from dataclasses import dataclass
from typing import Any
import warnings

from django.conf import settings as django_settings

# All attributes accessed with this prefix are possible to overwrite
# through django.conf.settings.
settings_prefix = "KLEIDES_MFA_"


@dataclass(frozen=True)
class AppSettings:
    '''Access this instance as ``kleides_mfa.conf.app_settings``.'''

    # The sorting order of the plugins on the mfa listing using the
    # plugin.slug. # These are known plugins in order of security.
    # hardware tokens > software tokens > backup codes.
    KLEIDES_MFA_PLUGIN_PRIORITY: list[str] | tuple[str] = (
        'u2f', 'yubikey', 'totp', 'recovery-code',
    )

    # Patch the AdminSite class and default admin site instance to require
    # 2 step authentication.
    KLEIDES_MFA_PATCH_ADMIN: bool = True

    # The default url to redirect to after login when the user has no 2 step
    # authentication devices active on the account.
    KLEIDES_MFA_SINGLE_FACTOR_URL: str = 'kleides_mfa:index'

    # Amount of seconds before a user is required to verify his authenticate
    # again to pass the recently authenticated requirement. This is can be used
    # to protect views that modify authentication settings.
    KLEIDES_MFA_VERIFIED_TIMEOUT: int | None = 900

    # Update the verification time on every request that passes the
    # recently_verified test to act as recent activity tracking. This prevents
    # a forced verified timeout while the user is actively using the account.
    KLEIDES_MFA_VERIFIED_UPDATE: bool = True

    def __getattribute__(self, name: str) -> Any:
        '''
        Check if a Django project settings should override the app default.

        Only allow settings from the settings prefix in order to avoid
        returning any random properties of the django settings we the settings
        prefix.
        '''
        if name == 'KLEIDES_MFA_PATCH_ADMIN':
            value = getattr(django_settings, 'KLEIDES_MFA_PATCH_ADMIN', True)
            if value:
                warnings.warn(
                    'The KLEIDES_MFA_PATCH_ADMIN=True setting is deprecated. '
                    'Use the default_site="kleides_mfa.admin.KleidesMfaAdmin" '
                    'attribute on your project AppConfig and remove the '
                    'django.contrib.admin app. '
                    'Then set KLEIDES_MFA_PATCH_ADMIN to False. '
                    'https://docs.djangoproject.com/en/5.0/ref/contrib/admin/'
                    '#overriding-the-default-admin-site', DeprecationWarning)
            return value

        if name.startswith(settings_prefix) and hasattr(django_settings, name):
            return getattr(django_settings, name)

        return super().__getattribute__(name)


app_settings = AppSettings()
