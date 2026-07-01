"""Tests for the email-based UserManager."""

import pytest
from django.contrib.auth import get_user_model

User = get_user_model()


@pytest.mark.django_db
class TestUserManager:
    def test_create_user(self):
        user = User.objects.create_user(
            email="User@Example.com", password="pass-12345"
        )
        # normalize_email lowercases the domain part.
        assert user.email == "User@example.com"
        assert user.check_password("pass-12345")
        assert user.is_active is True
        assert user.is_staff is False
        assert user.is_superuser is False
        assert user.id is not None
        assert user.USERNAME_FIELD == "email"

    def test_create_user_without_email_raises(self):
        with pytest.raises(ValueError):
            User.objects.create_user(email="", password="pass-12345")

    def test_create_superuser(self):
        admin = User.objects.create_superuser(
            email="admin@example.com", password="pass-12345"
        )
        assert admin.is_staff is True
        assert admin.is_superuser is True
        assert admin.is_active is True

    def test_create_superuser_with_invalid_flags_raises(self):
        with pytest.raises(ValueError):
            User.objects.create_superuser(
                email="admin2@example.com",
                password="pass-12345",
                is_superuser=False,
            )
        with pytest.raises(ValueError):
            User.objects.create_superuser(
                email="admin3@example.com",
                password="pass-12345",
                is_staff=False,
            )

    def test_email_is_unique(self):
        from django.db import IntegrityError

        User.objects.create_user(email="dup@example.com", password="pass-12345")
        with pytest.raises(IntegrityError):
            User.objects.create_user(email="dup@example.com", password="pass-12345")
