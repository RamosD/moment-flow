"""Account and JWT authentication routes (mounted under /api/v1/auth/)."""

from django.urls import path
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
    TokenVerifyView,
)

from .views import MeView

app_name = "accounts"

urlpatterns = [
    # JWT (login uses email as the username field).
    path("token/", TokenObtainPairView.as_view(), name="token_obtain_pair"),
    path("token/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
    path("token/verify/", TokenVerifyView.as_view(), name="token_verify"),
    # Authenticated user's own profile.
    path("me/", MeView.as_view(), name="me"),
]
