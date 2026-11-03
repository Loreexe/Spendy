"""HTTP endpoints for the movements import (DC-070)."""
from django.http import HttpResponse
from rest_framework import status
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response

from .imports import (
    MAX_BYTES,
    MAX_ROWS,
    TEMPLATE_FILENAME,
    analyze,
    build_template,
    confirm,
    parse_csv,
)
from .views import FinanceView

ROW_FIELDS = ("date", "description", "category", "account", "amount")


def _rows_from_request(request) -> list[dict]:
    rows = request.data.get("rows")
    if not isinstance(rows, list) or not rows:
        raise ValidationError({"rows": "Nessuna riga da analizzare."})
    if len(rows) > MAX_ROWS:
        raise ValidationError({"rows": f"Troppe righe: il massimo è {MAX_ROWS}."})
    cleaned = []
    for row in rows:
        if not isinstance(row, dict):
            raise ValidationError({"rows": "Formato delle righe non valido."})
        item = {field: row.get(field, "") for field in ROW_FIELDS}
        item["not_duplicate"] = bool(row.get("not_duplicate"))
        item["row_number"] = row.get("row_number")
        cleaned.append(item)
    return cleaned


class ImportTemplateView(FinanceView):
    def get(self, request):
        self.get_profile(request)
        response = HttpResponse(
            build_template(), content_type="text/csv; charset=utf-8"
        )
        response["Content-Disposition"] = (
            f'attachment; filename="{TEMPLATE_FILENAME}"'
        )
        return response


class ImportAnalyzeView(FinanceView):
    def post(self, request):
        profile = self.get_profile(request)
        upload = request.FILES.get("file")
        if upload is not None:
            if upload.size > MAX_BYTES:
                raise ValidationError(
                    {"file": f"Il file supera {MAX_BYTES // (1024 * 1024)} MB."}
                )
            rows, file_errors = parse_csv(upload.read())
            payload = analyze(rows, profile, file_errors)
        else:
            payload = analyze(_rows_from_request(request), profile)
        return Response(payload)


class ImportConfirmView(FinanceView):
    def post(self, request):
        profile = self.get_profile(request)
        result = confirm(_rows_from_request(request), profile)
        return Response(result, status=status.HTTP_201_CREATED)
