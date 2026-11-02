from rest_framework.permissions import BasePermission


class IsGlobalAdmin(BasePermission):
    message = "Riservato all'amministratore globale."

    def has_permission(self, request, view) -> bool:
        user = request.user
        return bool(
            user
            and user.is_authenticated
            and getattr(user, "is_global_admin", False)
            and user.is_active
        )
