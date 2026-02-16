from rest_framework.permissions import BasePermission


class IsRoleAdmin(BasePermission):
    message = "Admin access required."

    def has_permission(self, request, view):
        user = getattr(request, "user", None)
        if not user:
            return False

        # Allow Django superuser/staff (if request.user supports these attrs)
        if getattr(user, "is_superuser", False) or getattr(user, "is_staff", False):
            return True

        return getattr(user, "role", None) == "admin"


class IsManagerOrAdmin(BasePermission):
    message = "Manager or admin access required."

    def has_permission(self, request, view):
        user = getattr(request, "user", None)
        if not user:
            return False

        # Allow Django superuser/staff (if request.user supports these attrs)
        if getattr(user, "is_superuser", False) or getattr(user, "is_staff", False):
            return True

        return getattr(user, "role", None) in ["manager", "admin"]
