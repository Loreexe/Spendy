from django.core.management.base import BaseCommand
from django.utils import timezone

from finance.automations import run_all


class Command(BaseCommand):
    help = "Esegue le automazioni periodiche dei salvadanai in scadenza."

    def add_arguments(self, parser):
        parser.add_argument(
            "--date",
            help="Data di riferimento in formato AAAA-MM-GG (default: oggi).",
        )

    def handle(self, *args, **options):
        today = None
        if options.get("date"):
            from datetime import date

            today = date.fromisoformat(options["date"])
        outcome = run_all(today=today, now=timezone.now())
        self.stdout.write(
            "Automazioni: {rules} regole, {created} occorrenze create, "
            "{executed} eseguite, {retried} recuperate dopo errore, "
            "{pending_choice} in attesa di scelta.".format(**outcome)
        )
