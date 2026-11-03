"""CSV export of the register (DC-072).

The file uses the same columns and sign convention as the import, so it can be
opened in a spreadsheet and re-imported where the model allows it. Transfers
are exported as one row per account (the two sides), savings movements only
through their account side.
"""
import csv
import io
from datetime import date

from django.http import HttpResponse
from django.utils import timezone

from .models import ZERO, Transaction
from .views import FinanceView

HEADER = ("data", "descrizione", "categoria", "conto", "importo")


def _parse_date(value: str | None) -> date | None:
    if not value:
        return None
    try:
        return date.fromisoformat(value)
    except ValueError:
        return None


def _amount(value) -> str:
    return f"{value:.2f}".replace(".", ",")


class ExportTransactionsView(FinanceView):
    def get(self, request):
        profile = self.get_profile(request)
        queryset = (
            Transaction.objects.filter(profile=profile)
            .prefetch_related("lines__account")
            .order_by("date", "id")
        )
        account_id = request.query_params.get("account")
        savings_id = request.query_params.get("savings")
        if account_id:
            queryset = queryset.filter(lines__account_id=account_id)
        if savings_id:
            queryset = queryset.filter(lines__savings_id=savings_id)
        start = _parse_date(request.query_params.get("start"))
        end = _parse_date(request.query_params.get("end"))
        if start is not None:
            queryset = queryset.filter(date__gte=start)
        if end is not None:
            queryset = queryset.filter(date__lte=end)
        if account_id or savings_id:
            queryset = queryset.distinct()

        buffer = io.StringIO()
        writer = csv.writer(buffer, delimiter=";", lineterminator="\r\n")
        writer.writerow(HEADER)
        for operation in queryset:
            per_account: dict[int, object] = {}
            names: dict[int, str] = {}
            for line in operation.lines.all():
                if line.account_id is None:
                    continue
                per_account[line.account_id] = (
                    per_account.get(line.account_id, ZERO) + line.amount
                )
                names[line.account_id] = line.account.name
            for account_pk, net in per_account.items():
                if net == ZERO:
                    continue
                writer.writerow(
                    [
                        operation.date.strftime("%d-%m-%Y"),
                        operation.description or operation.get_kind_display(),
                        operation.get_kind_display(),
                        names[account_pk],
                        _amount(-net),
                    ]
                )

        content = b"\xef\xbb\xbf" + buffer.getvalue().encode("utf-8")
        response = HttpResponse(content, content_type="text/csv; charset=utf-8")
        filename = f"spendy-movimenti-{timezone.localdate().isoformat()}.csv"
        response["Content-Disposition"] = f'attachment; filename="{filename}"'
        return response
