import hashlib
import hmac
import json

import pytest
from django.test import RequestFactory, override_settings

from paybridge_django.models import PayBridgeTransaction
from paybridge_django.signals import paybridge_payment_success
from paybridge_django.views import PaystackWebhookView


@pytest.mark.django_db
def test_paystack_webhook_view_persists_and_fires_signal():
    calls = []

    def receiver(sender, event, transaction, **kwargs):
        calls.append((event.reference, transaction.reference))

    paybridge_payment_success.connect(receiver)
    try:
        payload = json.dumps(
            {
                "event": "charge.success",
                "data": {
                    "reference": "pst_view_123",
                    "status": "success",
                    "amount": 15000,
                    "currency": "NGN",
                    "customer": {
                        "email": "buyer@example.com",
                        "customer_code": "CUS_123",
                    },
                },
            }
        ).encode("utf-8")
        signature = hmac.new(b"sk_test_paystack", payload, hashlib.sha512).hexdigest()
        request = RequestFactory().post(
            "/payments/paystack/webhook/",
            data=payload,
            content_type="application/json",
            HTTP_X_PAYSTACK_SIGNATURE=signature,
        )
        request._body = payload

        response = PaystackWebhookView.as_view()(request)

        assert response.status_code == 200
        assert PayBridgeTransaction.objects.get(reference="pst_view_123").status == "SUCCESS"
        assert calls == [("pst_view_123", "pst_view_123")]
    finally:
        paybridge_payment_success.disconnect(receiver)


@pytest.mark.django_db
@override_settings(
    PAYBRIDGE={
        "DEFAULT_GATEWAY": "paystack",
        "PAYSTACK_SECRET_KEY": "sk_test_paystack",
        "PAYSTACK_WEBHOOK_SECRET": "sk_test_paystack",
        "FLUTTERWAVE_PUBLIC_KEY": "FLWPUBK_TEST",
        "FLUTTERWAVE_SECRET_KEY": "FLWSECK_TEST",
        "FLUTTERWAVE_WEBHOOK_SECRET": "flw_secret_hash",
        "STRIPE_SECRET_KEY": "sk_test_stripe",
        "STRIPE_WEBHOOK_SECRET": "whsec_test",
        "PROCESS_WEBHOOKS_ASYNC": True,
    }
)
def test_async_webhook_processing_falls_back_cleanly_without_celery():
    payload = json.dumps(
        {
            "event": "charge.success",
            "data": {
                "reference": "pst_async_view_123",
                "status": "success",
                "amount": 15000,
                "currency": "NGN",
            },
        }
    ).encode("utf-8")
    signature = hmac.new(b"sk_test_paystack", payload, hashlib.sha512).hexdigest()
    request = RequestFactory().post(
        "/payments/paystack/webhook/",
        data=payload,
        content_type="application/json",
        HTTP_X_PAYSTACK_SIGNATURE=signature,
    )
    request._body = payload

    response = PaystackWebhookView.as_view()(request)

    assert response.status_code == 200
