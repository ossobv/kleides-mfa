from django.contrib.admin.apps import AdminConfig


class TestAdminConfig(AdminConfig):
    default_site = 'kleides_mfa.admin.KleidesMfaAdminSite'
