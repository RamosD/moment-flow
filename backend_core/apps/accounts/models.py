"""Custom user model.

Identity is email-based: there is no ``username`` field and ``email`` is the
``USERNAME_FIELD``. The primary key is a UUID so user ids are non-sequential.
"""

import uuid

from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin
from django.db import models
from django.utils.timezone import now
from django.utils.translation import gettext_lazy as _

from .managers import UserManager


class User(AbstractBaseUser, PermissionsMixin):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    email = models.EmailField(_("email address"), unique=True)
    full_name = models.CharField(_("full name"), max_length=255, blank=True)
    display_name = models.CharField(_("display name"), max_length=150, blank=True)
    avatar_url = models.URLField(_("avatar URL"), blank=True)
    preferred_language = models.CharField(
        _("preferred language"), max_length=10, default="en"
    )
    timezone = models.CharField(_("timezone"), max_length=64, default="UTC")
    email_verified_at = models.DateTimeField(
        _("email verified at"), null=True, blank=True
    )

    is_active = models.BooleanField(_("active"), default=True)
    is_staff = models.BooleanField(_("staff status"), default=False)
    date_joined = models.DateTimeField(_("date joined"), default=now)

    objects = UserManager()

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []

    class Meta:
        verbose_name = _("user")
        verbose_name_plural = _("users")
        ordering = ["-date_joined"]

    def __str__(self):
        return self.email

    @property
    def is_email_verified(self) -> bool:
        return self.email_verified_at is not None
