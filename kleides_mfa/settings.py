# -*- coding: utf-8 -*-
from django.conf import settings

# The sorting order of the plugins on the mfa listing using the plugin.slug.
# These are known plugins in order of security.
# hardware tokens > software tokens > backup codes.
PLUGIN_PRIORITY = getattr(settings, 'KLEIDES_MFA_PLUGIN_PRIORITY', [
    'u2f', 'yubikey', 'totp', 'recovery-code',
])

# Patch the AdminSite class and default admin site instance to require
# 2 step authentication.
PATCH_ADMIN = getattr(settings, 'KLEIDES_MFA_PATCH_ADMIN', True)

# The default url to redirect to after login when the user has no 2 step
# authentication devices active on the account.
SINGLE_FACTOR_URL = getattr(
    settings, 'KLEIDES_MFA_SINGLE_FACTOR_URL', 'kleides_mfa:index')
