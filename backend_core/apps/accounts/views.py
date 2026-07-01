"""Account views: the authenticated user's profile endpoint."""

from drf_spectacular.utils import extend_schema, extend_schema_view
from rest_framework import generics, permissions
from rest_framework.response import Response

from .serializers import UserProfileUpdateSerializer, UserSerializer


@extend_schema_view(
    get=extend_schema(
        responses=UserSerializer,
        summary="Get the authenticated user",
        description="Returns the profile of the currently authenticated user.",
    ),
    put=extend_schema(
        request=UserProfileUpdateSerializer,
        responses=UserSerializer,
        summary="Replace the authenticated user's basic profile",
    ),
    patch=extend_schema(
        request=UserProfileUpdateSerializer,
        responses=UserSerializer,
        summary="Partially update the authenticated user's basic profile",
    ),
)
class MeView(generics.RetrieveUpdateAPIView):
    """Retrieve or update the profile of the authenticated user."""

    permission_classes = [permissions.IsAuthenticated]
    serializer_class = UserSerializer

    def get_object(self):
        return self.request.user

    def get_serializer_class(self):
        if self.request.method in ("PUT", "PATCH"):
            return UserProfileUpdateSerializer
        return UserSerializer

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop("partial", False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        # Always respond with the full profile representation.
        output = UserSerializer(instance, context=self.get_serializer_context())
        return Response(output.data)
