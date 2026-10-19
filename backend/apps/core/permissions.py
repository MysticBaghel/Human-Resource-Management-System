"""Role-based permission classes.

Every API view must declare one of these (or an explicit combination).
Hiding a button in React is never enough, so the API is the real gate.
"""

from rest_framework.permissions import SAFE_METHODS, BasePermission


class HasRole(BasePermission):
    """Base class: allow the request when the user holds one of `roles`."""

    roles: tuple[str, ...] = ()
    message = "You do not have permission to perform this action."

    def has_permission(self, request, view) -> bool:
        user = request.user
        return bool(
            user
            and user.is_authenticated
            and getattr(user, "role", None) in self.roles
        )


class IsAdmin(HasRole):
    roles = ("admin",)
    message = "Only an admin can perform this action."


class IsHR(HasRole):
    roles = ("hr",)
    message = "Only HR can perform this action."


class IsManager(HasRole):
    roles = ("manager",)
    message = "Only a manager can perform this action."


class IsEmployee(HasRole):
    roles = ("employee",)
    message = "Only an employee can perform this action."


class IsHROrAdmin(HasRole):
    roles = ("hr", "admin")
    message = "Only HR or an admin can perform this action."


class IsManagerOrAbove(HasRole):
    roles = ("manager", "hr", "admin")
    message = "Only a manager, HR or an admin can perform this action."


class IsReadOnly(BasePermission):
    """Allow any authenticated user, but only safe methods.

    Authentication is checked explicitly: a view's `permission_classes`
    replaces the global default, so returning only a method check here would
    let anonymous callers read.
    """

    message = "This endpoint is read-only."

    def has_permission(self, request, view) -> bool:
        user = request.user
        return bool(
            user
            and user.is_authenticated
            and request.method in SAFE_METHODS
        )


class EmployeePermission(BasePermission):
    """Who may do what with employee records.

    Everyone authenticated may read, but the queryset is scoped first, so an
    employee only ever reaches their own record and a manager only their team.
    Writes are HR/admin, except that an employee may change their own phone
    number and nothing else.
    """

    message = "You do not have permission to perform this action."
    HR_ROLES = frozenset({"hr", "admin"})
    SELF_EDITABLE_FIELDS = frozenset({"phone"})

    def has_permission(self, request, view) -> bool:
        user = request.user
        if not (user and user.is_authenticated):
            return False

        action = getattr(view, "action", None)
        if action in {"list", "retrieve"}:
            return True
        if action == "destroy":
            # DELETE is always refused by the view itself (405), so let it
            # through to that handler rather than reporting a permission error.
            return True
        if action in {"create", "deactivate", "reactivate"}:
            return user.role in self.HR_ROLES
        if action in {"update", "partial_update"}:
            # Employees may edit themselves; the object check limits the fields.
            return user.role in self.HR_ROLES or user.role == "employee"
        # Fail closed for any action added later without deciding its rule.
        return False

    def has_object_permission(self, request, view, obj) -> bool:
        user = request.user
        if request.method in SAFE_METHODS:
            # Reaching the object at all already proved it is in the scoped
            # queryset, so reading is allowed.
            return True
        if user.role in self.HR_ROLES:
            return True
        if user.role == "employee" and obj.user_id == user.id:
            sent = set(request.data.keys()) if hasattr(request.data, "keys") else set()
            if sent - self.SELF_EDITABLE_FIELDS:
                self.message = "Employees may only edit their own phone number."
                return False
            return True

        self.message = "You do not have permission to change this employee."
        return False


class TeamPermission(BasePermission):
    """Managers may read the teams they lead; only HR and admin may write."""

    message = "Only HR or an admin can change teams."
    READ_ROLES = frozenset({"manager", "hr", "admin"})
    WRITE_ROLES = frozenset({"hr", "admin"})

    def has_permission(self, request, view) -> bool:
        user = request.user
        if not (user and user.is_authenticated):
            return False
        if request.method in SAFE_METHODS:
            return user.role in self.READ_ROLES
        return user.role in self.WRITE_ROLES
