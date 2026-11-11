from django.core.management.base import BaseCommand

from ...models import PayBridgeSubscription
from ...services import get_gateway


class Command(BaseCommand):
    help = "Refresh active PayBridge subscription records from their upstream gateway."

    def handle(self, *args, **options):
        refreshed = 0
        for subscription in PayBridgeSubscription.objects.exclude(status="CANCELLED"):
            service = get_gateway(subscription.gateway)
            try:
                service.refresh_subscription(subscription)
            except Exception:  # noqa: BLE001
                continue
            refreshed += 1

        self.stdout.write(self.style.SUCCESS(f"Checked {refreshed} subscription(s)."))
