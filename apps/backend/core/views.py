from django.conf import settings
from django.db import connection
from django.utils import timezone
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.permissions import IsGlobalAdmin

from .system import fetch_latest_release, is_newer, read_backup_status


class HealthView(APIView):
    """Liveness/readiness endpoint used by Docker and CI."""

    permission_classes = [AllowAny]
    authentication_classes: list = []

    def get(self, request):
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
                cursor.fetchone()
        except Exception:
            return Response(
                {"status": "error", "database": "unavailable"},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )
        return Response({"status": "ok", "database": "ok"})


class AdminSystemView(APIView):
    """Read-only system information and optional GitHub release check."""

    permission_classes = [IsGlobalAdmin]

    def get(self, request):
        database = "ok"
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
                cursor.fetchone()
        except Exception:
            database = "unavailable"

        payload = {
            "current_version": getattr(settings, "SPENDY_VERSION", "0.0.0"),
            "database": database,
            "checked_at": None,
            "latest": None,
            "update_available": False,
            "error": None,
            "backup": read_backup_status(),
        }

        if request.query_params.get("check") in {"1", "true", "yes"}:
            release, error = fetch_latest_release()
            payload["checked_at"] = timezone.now().isoformat()
            payload["error"] = error
            if release is not None:
                payload["latest"] = {
                    "version": release.version,
                    "tag": release.tag,
                    "url": release.url,
                    "published_at": release.published_at,
                    "notes": release.notes,
                }
                payload["update_available"] = is_newer(
                    payload["current_version"], release.version
                )

        return Response(payload)
