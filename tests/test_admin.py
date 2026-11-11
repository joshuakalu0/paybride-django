import pytest
from django.contrib import admin
from django.contrib.messages.storage.fallback import FallbackStorage
from django.test import RequestFactory

from paybridge_django.admin import PayBridgeTransactionAdmin, retry_webhook
from paybridge_django.models import PayBridgeTransaction
from paybridge_django.signals import paybridge_payment_success


@pytest.mark.django_db
def test_retry_webhook_admin_action_replays_signal():
    transaction = PayBridgeTransaction.objects.create(
        reference="pst_retry_123",
        gateway="paystack",
        amount="100.00",
        currency="NGN",
        status="SUCCESS",
        email="buyer@example.com",
        metadata={
            "event_name": "charge.success",
            "event_type": "PAYMENT_SUCCESS",
        },
        webhook_payload={"event": "charge.success"},
    )

    calls = []

    def receiver(sender, event, transaction, **kwargs):
        calls.append(event.reference)

    paybridge_payment_success.connect(receiver)
    try:
        request = RequestFactory().post("/admin/paybridge/retry/")
        request.session = {}
        setattr(request, "_messages", FallbackStorage(request))
        model_admin = PayBridgeTransactionAdmin(PayBridgeTransaction, admin.site)

        retry_webhook(model_admin, request, PayBridgeTransaction.objects.filter(pk=transaction.pk))

        assert calls == ["pst_retry_123"]
    finally:
        paybridge_payment_success.disconnect(receiver)
