===================================
Kleides Multi Factor Authentication
===================================


.. image:: https://img.shields.io/pypi/v/kleides_mfa.svg
        :target: https://pypi.python.org/pypi/kleides_mfa

.. image:: https://img.shields.io/travis/Urth/kleides_mfa.svg
        :target: https://travis-ci.org/Urth/kleides_mfa

.. image:: https://readthedocs.org/projects/kleides-mfa/badge/?version=latest
        :target: https://kleides-mfa.readthedocs.io/en/latest/?badge=latest
        :alt: Documentation Status




Interface components to configure and manage multi factor authentication


* Free software: GNU General Public License v3
* Documentation: https://kleides-mfa.readthedocs.io.

Install
-------

.. code-block::

   pip install kleides-mfa

Add `kleides_mfa` to your `INSTALLED_APPS` and `crispy_forms`_ if you
are going to use the default templates::

   INSTALLED_APPS = [
       ...
       'kleides_mfa',
       'crispy_forms',
       ...
   ]

.. _crispy_forms: https://django-crispy-forms.readthedocs.io/en/latest/

Add `kleides_mfa.middleware.KleidesAuthenticationMiddleware` to the
`MIDDLEWARE` setting::

   MIDDLEWARE = [
       ...
       'django.contrib.auth.middleware.AuthenticationMiddleware',
       'kleides_mfa.middleware.KleidesAuthenticationMiddleware',
       ...
   ]

Include `kleides_mfa.urls` in your urlpatterns::

   urlpatterns = [
       path('', include('kleides_mfa.urls')),
   ]
