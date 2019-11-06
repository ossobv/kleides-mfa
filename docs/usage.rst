=====
Usage
=====

To use Kleides Multi Factor Authentication in a project register your
authentication method in the `AppConfig.ready` handler::

.. code-block::

    class YourAppConfig(AppConfig):
        def ready(self):
            from kleides_mfa.registry import registry
            registry.register(
                'Authentication Name', DjangoOTPModelClass)

Your can provide any additional parameters accepted by
:class:`kleides_mfa.registry.KleidesMfaPlugin`.

The `model` parameter does not have to be a Django OTP Device subclass
but it must use the same interface and manager interface.
