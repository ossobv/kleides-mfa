# -*- coding: utf-8 -*-

"""Kleides Multi Factor Authentication."""

__author__ = """Harm Geerts"""
__email__ = 'hgeerts@osso.nl'
__version__ = '0.1.14'

import django

if django.VERSION < (3, 2):
    default_app_config = 'kleides_mfa.apps.KleidesMfaConfig'
