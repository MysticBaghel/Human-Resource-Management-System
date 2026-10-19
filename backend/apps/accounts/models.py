"""Custom user model: email login with a role.

AUTH_USER_MODEL is pointed at this model in base.py and the initial migration
is committed with it. Changing AUTH_USER_MODEL after migrations exist is
painful, which is why it is created before anything else.
"""

from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _


class UserManager(BaseUserManager):
    """Manager for the email-based user model."""

    use_in_migrations = True

    def _create_user(self, email: str, password: str | None, **extra):
        if not email:
            raise ValueError("An email address is required.")
        # Lowercase the whole address, not just the domain: login lowercases
        # the input, so a mixed-case local part would otherwise be stored in a
        # form that can never be matched.
        email = self.normalize_email(email).lower()
        user = self.model(email=email, **extra)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_user(self, email: str, password: str | None = None, **extra):
        extra.setdefault("is_staff", False)
        extra.setdefault("is_superuser", False)
        return self._create_user(email, password, **extra)

    def create_superuser(self, email: str, password: str | None = None, **extra):
        extra.setdefault("is_staff", True)
        extra.setdefault("is_superuser", True)
        extra.setdefault("role", User.Role.ADMIN)

        if extra.get("is_staff") is not True:
            raise ValueError("A superuser must have is_staff=True.")
        if extra.get("is_superuser") is not True:
            raise ValueError("A superuser must have is_superuser=True.")

        return self._create_user(email, password, **extra)


class User(AbstractBaseUser, PermissionsMixin):
    """Application user. Identified by email, authorised by role."""

    class Role(models.TextChoices):
        ADMIN = "admin", _("Admin")
        HR = "hr", _("HR")
        MANAGER = "manager", _("Manager")
        EMPLOYEE = "employee", _("Employee")

    email = models.EmailField(_("email address"), unique=True)
    role = models.CharField(
        _("role"),
        max_length=20,
        choices=Role.choices,
        default=Role.EMPLOYEE,
    )
    is_staff = models.BooleanField(
        _("staff status"),
        default=False,
        help_text=_("Can sign in to the Django admin."),
    )
    is_active = models.BooleanField(
        _("active"),
        default=True,
        help_text=_("Deactivated users cannot log in. Employees are never deleted."),
    )
    date_joined = models.DateTimeField(_("date joined"), default=timezone.now)

    objects = UserManager()

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS: list[str] = []

    class Meta:
        verbose_name = _("user")
        verbose_name_plural = _("users")
        ordering = ["email"]

    def __str__(self) -> str:
        return self.email

    @property
    def is_hr(self) -> bool:
        return self.role == self.Role.HR

    @property
    def is_admin_role(self) -> bool:
        return self.role == self.Role.ADMIN

    @property
    def is_manager_role(self) -> bool:
        return self.role == self.Role.MANAGER

    def get_full_name(self) -> str:
        return self.email

    def get_short_name(self) -> str:
        return self.email
