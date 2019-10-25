#!/usr/bin/env python
# -*- coding: utf-8 -*-•
from __future__ import absolute_import, unicode_literals

import os
import sys

import django
from django.conf import settings
from django.test.utils import get_runner


def test_runner():
    os.environ['DJANGO_SETTINGS_MODULE'] = 'tests.settings'
    django.setup()
    TestRunner = get_runner(settings)
    return TestRunner()


def test_suite():
    return test_runner().build_suite(test_labels=None)


if __name__ == "__main__":
    failures = test_runner().run_tests(test_labels=None)
    sys.exit(bool(failures))
