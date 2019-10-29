# -*- coding: utf-8 -*-
from __future__ import absolute_import, unicode_literals

from django.conf import settings

# The sorting order of the plugins on the mfa listing using the plugin.slug.
# These are known plugins in order of security.
# hardware tokens > software tokens > backup codes.
PLUGIN_PRIORITY = getattr(settings, 'KLEIDES_MFA_PLUGIN_PRIORITY', [
    'u2f', 'yubikey', 'totp', 'recovery-code',
])

PATCH_ADMIN = getattr(settings, 'KLEIDES_MFA_PATCH_ADMIN', True)
