"""Baseline smoke tests confirming the project foundation is wired up."""

from django.apps import apps
from django.conf import settings


def test_core_app_is_installed():
    assert "apps.core" in settings.INSTALLED_APPS
    assert apps.is_installed("apps.core")


def test_base_models_are_abstract():
    from apps.core.models import BaseModel, TimeStampedModel, UUIDModel

    assert TimeStampedModel._meta.abstract
    assert UUIDModel._meta.abstract
    assert BaseModel._meta.abstract


def test_rest_framework_defaults_configured():
    rf = settings.REST_FRAMEWORK
    assert (
        "rest_framework_simplejwt.authentication.JWTAuthentication"
        in rf["DEFAULT_AUTHENTICATION_CLASSES"]
    )
    assert (
        "rest_framework.permissions.IsAuthenticated"
        in rf["DEFAULT_PERMISSION_CLASSES"]
    )
