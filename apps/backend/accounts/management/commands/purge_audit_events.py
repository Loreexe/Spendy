"""Elimina gli eventi di audit più vecchi della retention configurata."""
from datetime import timedelta

from django.conf import settings
from django.core.management.base import BaseCommand
from django.utils import timezone

from accounts.models import AuditEvent


class Command(BaseCommand):
    help = "Elimina gli eventi di audit oltre la retention (SPENDY_AUDIT_RETENTION_DAYS)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--days",
            type=int,
            default=getattr(settings, "AUDIT_RETENTION_DAYS", 180),
            help="Giorni di conservazione (default dalla configurazione).",
        )

    def handle(self, *args, **options):
        days = max(1, int(options["days"]))
        now = timezone.now()
        cutoff = now - timedelta(days=days)
        deleted, _ = (
            AuditEvent.objects.filter(created_at__lt=cutoff)
            .exclude(action=AuditEvent.Action.MCP_CALL)
            .delete()
        )
        mcp_days = max(
            1, int(getattr(settings, "MCP_AUDIT_RETENTION_DAYS", 30))
        )
        mcp_cutoff = now - timedelta(days=mcp_days)
        deleted_mcp, _ = AuditEvent.objects.filter(
            action=AuditEvent.Action.MCP_CALL,
            created_at__lt=mcp_cutoff,
        ).delete()
        self.stdout.write(
            self.style.SUCCESS(
                "Eventi di audit eliminati: "
                f"{deleted} oltre {days} giorni, "
                f"{deleted_mcp} MCP oltre {mcp_days} giorni."
            )
        )
