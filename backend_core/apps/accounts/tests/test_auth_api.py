"""Tests for the JWT auth endpoints and /api/v1/auth/me/."""

import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

User = get_user_model()

ME_URL = "/api/v1/auth/me/"
TOKEN_URL = "/api/v1/auth/token/"
REFRESH_URL = "/api/v1/auth/token/refresh/"


@pytest.fixture
def user(db):
    return User.objects.create_user(
        email="me@example.com",
        password="pass-12345",
        full_name="Me User",
    )


@pytest.mark.django_db
class TestMeEndpoint:
    def test_anonymous_is_rejected(self):
        client = APIClient()
        response = client.get(ME_URL)
        assert response.status_code == 401

    def test_authenticated_user_can_read_profile(self, user):
        client = APIClient()
        client.force_authenticate(user=user)
        response = client.get(ME_URL)
        assert response.status_code == 200
        assert response.data["email"] == "me@example.com"
        assert response.data["full_name"] == "Me User"
        assert "password" not in response.data

    def test_authenticated_user_can_update_basic_profile(self, user):
        client = APIClient()
        client.force_authenticate(user=user)
        response = client.patch(
            ME_URL, {"display_name": "DJ Me", "timezone": "Europe/Lisbon"},
            format="json",
        )
        assert response.status_code == 200
        assert response.data["display_name"] == "DJ Me"
        assert response.data["timezone"] == "Europe/Lisbon"
        user.refresh_from_db()
        assert user.display_name == "DJ Me"


@pytest.mark.django_db
class TestJWTAuth:
    def test_obtain_token_with_email_and_password(self, user):
        client = APIClient()
        response = client.post(
            TOKEN_URL,
            {"email": "me@example.com", "password": "pass-12345"},
            format="json",
        )
        assert response.status_code == 200
        assert "access" in response.data
        assert "refresh" in response.data

    def test_obtain_token_with_wrong_password_fails(self, user):
        client = APIClient()
        response = client.post(
            TOKEN_URL,
            {"email": "me@example.com", "password": "wrong"},
            format="json",
        )
        assert response.status_code == 401

    def test_access_token_grants_access_to_me(self, user):
        client = APIClient()
        token_response = client.post(
            TOKEN_URL,
            {"email": "me@example.com", "password": "pass-12345"},
            format="json",
        )
        access = token_response.data["access"]
        client.credentials(HTTP_AUTHORIZATION=f"Bearer {access}")
        response = client.get(ME_URL)
        assert response.status_code == 200
        assert response.data["email"] == "me@example.com"

    def test_refresh_returns_new_access(self, user):
        client = APIClient()
        token_response = client.post(
            TOKEN_URL,
            {"email": "me@example.com", "password": "pass-12345"},
            format="json",
        )
        refresh = token_response.data["refresh"]
        response = client.post(REFRESH_URL, {"refresh": refresh}, format="json")
        assert response.status_code == 200
        assert "access" in response.data
