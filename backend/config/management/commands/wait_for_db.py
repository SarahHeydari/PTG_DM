import time
from django.core.management.base import BaseCommand
from django.db import connections
from django.db.utils import OperationalError


class Command(BaseCommand):
    help = "Wait for database to be available"

    def handle(self, *args, **options):
        self.stdout.write("Waiting for database...")

        retries = 60
        while retries > 0:
            try:
                connections["default"].cursor()
                self.stdout.write(self.style.SUCCESS("Database available!"))
                return
            except OperationalError:
                retries -= 1
                time.sleep(1)

        raise OperationalError("Database not available after waiting.")
