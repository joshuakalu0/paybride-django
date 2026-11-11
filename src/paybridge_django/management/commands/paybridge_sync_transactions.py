from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from ...services import get_gateway
from ...services.processing import record_verification


class Command(BaseCommand):
    help = "Fetch recent gateway transactions and reconcile them with local PayBridge records."

    def add_arguments(self, parser):
        parser.add_argument("--gateway", required=True)
        parser.add_argument("--days", type=int, default=7)

    def handle(self, *args, **options):
        gateway_name = str(options["gateway"]).lower()
        days = int(options["days"])
        service = get_gateway(gateway_name)
        now = timezone.now()
        from_dt = now - timedelta(days=days)
        synced = 0

        for result in service.fetch_recent_transactions(from_dt=from_dt, to_dt=now):
            record_verification(result)
            synced += 1

        self.stdout.write(self.style.SUCCESS(f"Reconciled {synced} transaction(s) for {gateway_name}."))
