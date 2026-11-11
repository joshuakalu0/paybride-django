from __future__ import annotations

from django.conf import settings
from django.core.mail import send_mail

from .models import PayBridgeTransaction
from .services.processing import process_webhook_event
from .types import WebhookEvent

try:
    from celery import shared_task
except ImportError:
    def shared_task(*args, **kwargs):  # type: ignore[override]
        def decorator(func):
            func.delay = func
            return func

        return decorator


@shared_task(name="paybridge_django.process_webhook_async")
def process_webhook_async(event_payload: dict) -> None:
    process_webhook_event(WebhookEvent.from_dict(event_payload))


@shared_task(name="paybridge_django.send_payment_receipt_email")
def send_payment_receipt_email(reference: str) -> None:
    transaction = PayBridgeTransaction.objects.get(reference=reference)
    if not transaction.email:
        return
    send_mail(
        subject=f"Payment receipt for {transaction.reference}",
        message=(
            f"Your payment via {transaction.gateway} has status {transaction.status} "
            f"for {transaction.amount} {transaction.currency}."
        ),
        from_email=getattr(settings, "DEFAULT_FROM_EMAIL", "payments@example.com"),
        recipient_list=[transaction.email],
        fail_silently=False,
    )
