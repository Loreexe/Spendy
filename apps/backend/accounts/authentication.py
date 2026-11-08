from datetime import timedelta

from django.utils import timezone
from rest_framework.authentication import BaseAuthentication, get_authorization_header
from rest_framework.exceptions import AuthenticationFailed

from .models import DeviceToken


class DeviceTokenAuthentication(BaseAuthentication):
    """Bearer token per dispositivo (DC-103).

    Il token in chiaro non viene mai salvato: ogni richiesta calcola l'hash e
    cerca il dispositivo attivo. ``last_used_at`` viene aggiornato al massimo
    una volta al minuto per evitare una scrittura a ogni chiamata.
    """

    keyword = "Bearer"

    def authenticate(self, request):
        header = get_authorization_header(request).split()
        if not header:
            return None
        if header[0].lower() != self.keyword.lower().encode():
            return None
        if len(header) != 2:
            raise AuthenticationFailed("Token non valido.")
        try:
            raw_key = header[1].decode("utf-8")
        except UnicodeError as exc:  # pragma: no cover - difensivo
            raise AuthenticationFailed("Token non valido.") from exc

        token = (
            DeviceToken.objects.select_related("user")
            .filter(key_hash=DeviceToken.hash_key(raw_key), revoked_at__isnull=True)
            .first()
        )
        if token is None:
            raise AuthenticationFailed("Token non valido o revocato.")
        if not token.user.is_active:
            raise AuthenticationFailed("Account non attivo.")

        now = timezone.now()
        if token.last_used_at is None or now - token.last_used_at > timedelta(minutes=1):
            DeviceToken.objects.filter(pk=token.pk).update(last_used_at=now)
            token.last_used_at = now
        return (token.user, token)

    def authenticate_header(self, request):
        return self.keyword


try:  # pragma: no cover - dipende da drf-spectacular
    from drf_spectacular.extensions import OpenApiAuthenticationExtension

    class DeviceTokenScheme(OpenApiAuthenticationExtension):
        target_class = "accounts.authentication.DeviceTokenAuthentication"
        name = "deviceToken"

        def get_security_definition(self, auto_schema):
            return {
                "type": "http",
                "scheme": "bearer",
                "bearerFormat": "DeviceToken",
            }

except ImportError:  # pragma: no cover
    pass
