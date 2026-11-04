"""HTTP endpoints for the profile archive (DC-074)."""
from django.http import HttpResponse
from django.utils import timezone
from rest_framework import status
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response

from .archive import (
    MAX_ARCHIVE_BYTES,
    analyze_archive,
    build_archive,
    restore_archive,
)
from .views import FinanceView


def _read_upload(request) -> bytes:
    upload = request.FILES.get("file")
    if upload is None:
        raise ValidationError({"file": "Carica un archivio ZIP."})
    if upload.size > MAX_ARCHIVE_BYTES:
        raise ValidationError(
            {
                "file": (
                    "L'archivio supera "
                    f"{MAX_ARCHIVE_BYTES // (1024 * 1024)} MB."
                )
            }
        )
    return upload.read()


class ExportArchiveView(FinanceView):
    def get(self, request):
        profile = self.get_profile(request)
        content = build_archive(profile)
        response = HttpResponse(content, content_type="application/zip")
        filename = f"spendy-archivio-{timezone.localdate().isoformat()}.zip"
        response["Content-Disposition"] = f'attachment; filename="{filename}"'
        return response


class ImportArchiveAnalyzeView(FinanceView):
    def post(self, request):
        profile = self.get_profile(request)
        return Response(analyze_archive(_read_upload(request), profile))


class ImportArchiveConfirmView(FinanceView):
    def post(self, request):
        profile = self.get_profile(request)
        result = restore_archive(_read_upload(request), profile)
        return Response(result, status=status.HTTP_201_CREATED)
