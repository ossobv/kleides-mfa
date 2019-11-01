# -*- coding: utf-8 -*-
from __future__ import absolute_import, unicode_literals

import factory
from factory.django import DjangoModelFactory


class UserFactory(DjangoModelFactory):
    class Meta:
        model = 'auth.User'
        inline_args = ('username', 'email', 'password')

    username = factory.Faker('user_name')
    email = factory.Faker('email')
    password = factory.Faker('password')
    is_active = True

    @classmethod
    def _create(cls, model_class, username, email, password, **kwargs):
        instance = model_class.objects._create_user(
            username, email, password, **kwargs)
        instance.raw_password = password
        return instance
