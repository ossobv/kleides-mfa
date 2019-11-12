=======
History
=======

0.1.4 (2019-11-12)
------------------

* Add setting to disable patching of the User models.
* Patch AnonymousUser to share the properties of the User model.
* Add configurable redirect for users that login without 2 step
  authentication.
* Fix 2 step test login when another user was logged in.


0.1.3 (2019-11-07)
------------------

* Cleanup plugin button/table alignment.
* Add Yubikey plugin for `django-otp-yubikey`_.
* Only patch AdminSite when admin is installed.
* Remove python 2 compatibility classifiers.

.. _django-otp-yubikey: https://github.com/django-otp/django-otp-yubikey


0.1.2 (2019-11-06)
------------------

* Improve and fix documentation.


0.1.1 (2019-11-04)
------------------

* Set defaul device name if omitted from POST data.


0.1.0 (2019-11-04)
------------------

* First release on PyPI.
