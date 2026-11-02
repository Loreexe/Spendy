from django.contrib.auth.backends import ModelBackend
from django.db.models import Q

from .models import User


class EmailOrUsernameBackend(ModelBackend):
    """Authenticate with the email or the username, case-insensitively."""

    def authenticate(self, request, username=None, password=None, **kwargs):
        identifier = username or kwargs.get("email")
        if not identifier or password is None:
            return None

        user = (
            User.objects.filter(
                Q(email__iexact=identifier) | Q(username__iexact=identifier)
            )
            .order_by("id")
            .first()
        )
        if user is None:
            User().set_password(password)  # mitigate timing attacks
            return None
        if user.check_password(password) and self.user_can_authenticate(user):
            return user
        return None
