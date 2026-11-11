"""HTTP endpoints for the movements import (DC-070, DC-071)."""
from django.http import HttpResponse
from rest_framework import status
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response

from .imports import (
    DATE_FORMATS,
    DECIMAL_SEPARATORS,
    DELIMITERS,
    MAX_BYTES,
    MAX_ROWS,
    TEMPLATE_FILENAME,
    analyze,
    build_template,
    confirm,
    parse_csv,
)
from .views import FinanceView

ROW_FIELDS = ("date", "description", "category", "account", "amount", "time")


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


def _format_options(request) -> tuple[str | None, str | None, str | None]:
    delimiter = request.data.get("delimiter") or None
    date_format = request.data.get("date_format") or None
    decimal_separator = request.data.get("decimal_separator") or None
    if delimiter is not None and delimiter not in DELIMITERS:
        raise ValidationError(
            {"delimiter": "Separatore di colonna non valido."}
        )
    if date_format is not None and date_format not in DATE_FORMATS:
        raise ValidationError({"date_format": "Formato data non valido."})
    if (
        decimal_separator is not None
        and decimal_separator not in DECIMAL_SEPARATORS
    ):
        raise ValidationError(
            {"decimal_separator": "Separatore decimale non valido."}
        )
    return delimiter, date_format, decimal_separator


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
        delimiter, date_format, decimal_separator = _format_options(request)
        upload = request.FILES.get("file")
        if upload is not None:
            if upload.size > MAX_BYTES:
                raise ValidationError(
                    {"file": f"Il file supera {MAX_BYTES // (1024 * 1024)} MB."}
                )
            rows, file_errors, used = parse_csv(upload.read(), delimiter)
            payload = analyze(
                rows,
                profile,
                file_errors,
                delimiter=used,
                date_format=date_format,
                decimal_separator=decimal_separator,
            )
        else:
            payload = analyze(
                _rows_from_request(request),
                profile,
                delimiter=delimiter,
                date_format=date_format,
                decimal_separator=decimal_separator,
            )
        return Response(payload)


class ImportConfirmView(FinanceView):
    def post(self, request):
        profile = self.get_profile(request)
        _, date_format, decimal_separator = _format_options(request)
        result = confirm(
            _rows_from_request(request),
            profile,
            date_format=date_format,
            decimal_separator=decimal_separator,
        )
        return Response(result, status=status.HTTP_201_CREATED)
