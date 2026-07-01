"""Django Admin registration for the custom email-based user."""

from django import forms
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.forms import ReadOnlyPasswordHashField
from django.utils.translation import gettext_lazy as _

from .models import User


class UserCreationForm(forms.ModelForm):
    """Admin form to create a user with a hashed password (no username)."""

    password1 = forms.CharField(label=_("Password"), widget=forms.PasswordInput)
    password2 = forms.CharField(
        label=_("Password confirmation"), widget=forms.PasswordInput
    )

    class Meta:
        model = User
        fields = ("email", "full_name", "display_name")

    def clean_password2(self):
        password1 = self.cleaned_data.get("password1")
        password2 = self.cleaned_data.get("password2")
        if password1 and password2 and password1 != password2:
            raise forms.ValidationError(_("The two password fields didn't match."))
        return password2

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data["password1"])
        if commit:
            user.save()
        return user


class UserChangeForm(forms.ModelForm):
    """Admin form to edit a user; shows the password hash read-only."""

    password = ReadOnlyPasswordHashField(
        label=_("Password"),
        help_text=_(
            "Raw passwords are not stored, so there is no way to see this "
            "user's password, but you can change it using "
            '<a href="../password/">this form</a>.'
        ),
    )

    class Meta:
        model = User
        fields = "__all__"


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    add_form = UserCreationForm
    form = UserChangeForm

    ordering = ("-date_joined",)
    list_display = (
        "email",
        "full_name",
        "display_name",
        "is_active",
        "is_staff",
        "is_superuser",
        "date_joined",
    )
    list_filter = ("is_active", "is_staff", "is_superuser", "preferred_language")
    search_fields = ("email", "full_name", "display_name")
    readonly_fields = ("id", "last_login", "date_joined")
    filter_horizontal = ("groups", "user_permissions")

    fieldsets = (
        (None, {"fields": ("id", "email", "password")}),
        (
            _("Profile"),
            {
                "fields": (
                    "full_name",
                    "display_name",
                    "avatar_url",
                    "preferred_language",
                    "timezone",
                )
            },
        ),
        (_("Verification"), {"fields": ("email_verified_at",)}),
        (
            _("Permissions"),
            {
                "fields": (
                    "is_active",
                    "is_staff",
                    "is_superuser",
                    "groups",
                    "user_permissions",
                )
            },
        ),
        (_("Important dates"), {"fields": ("last_login", "date_joined")}),
    )

    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": (
                    "email",
                    "full_name",
                    "display_name",
                    "password1",
                    "password2",
                    "is_staff",
                    "is_superuser",
                ),
            },
        ),
    )
