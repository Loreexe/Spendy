from django.core.management.base import BaseCommand

from finance.models import purge_trash


class Command(BaseCommand):
    help = "Elimina definitivamente gli elementi nel cestino da più di 30 giorni."

    def handle(self, *args, **options):
        removed = purge_trash()
        self.stdout.write(f"Cestino: {removed} elementi eliminati definitivamente.")
