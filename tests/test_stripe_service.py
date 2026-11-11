import hashlib
import hmac
import json
import time

import pytest
import responses
import respx
from django.test import RequestFactory

from paybridge_django.models import PayBridgeSubscription
from paybridge_django.services import get_gateway
from paybridge_django.subscriptions import has_active_subscription


@pytest.mark.django_db
@responses.activate
def test_stripe_initialize_and_subscription():
    service = get_gateway("stripe")

    responses.post(
        "https://api.stripe.com/v1/payment_intents",
        json={
            "id": "pi_123",
            "amount": 15000,
            "currency": "ngn",
            "client_secret": "pi_123_secret",
            "status": "requires_payment_method",
            "created": 1746624000,
        },
        status=200,
    )
    init_result = service.initialize_transaction(
        amount="150.00",
        email="owner@example.com",
        currency="NGN",
        callback_url="https://example.com/return/",
    )
    assert init_result.client_secret == "pi_123_secret"

    responses.post(
        "https://api.stripe.com/v1/customers",
        json={"id": "cus_123", "email": "owner@example.com", "name": "Owner"},
        status=200,
    )
    responses.post(
        "https://api.stripe.com/v1/subscriptions",
        json={
            "id": "sub_123",
            "status": "active",
            "trial_end": 1746624100,
            "current_period_end": 1746700000,
            "items": {"data": [{"price": {"id": "price_123"}}]},
        },
        status=200,
    )
    subscription = service.create_subscription(price_id="price_123", email="owner@example.com")
    assert subscription.subscription_id == "sub_123"
    assert PayBridgeSubscription.objects.filter(gateway_subscription_id="sub_123").exists()
    assert has_active_subscription("owner@example.com") is True


@pytest.mark.asyncio
@pytest.mark.django_db
async def test_stripe_async_verify():
    service = get_gateway("stripe")
    with respx.mock(base_url="https://api.stripe.com") as router:
        router.get("/v1/payment_intents/pi_123").respond(
            200,
            json={
                "id": "pi_123",
                "amount": 15000,
                "currency": "ngn",
                "status": "succeeded",
                "created": 1746624000,
                "receipt_email": "owner@example.com",
                "customer": "cus_123",
            },
        )
        result = await service.averify_transaction("pi_123")

    assert result.status == "SUCCESS"


@pytest.mark.django_db
def test_stripe_webhook_parsing():
    service = get_gateway("stripe")
    body = json.dumps(
        {
            "id": "evt_123",
            "type": "customer.subscription.updated",
            "created": 1746624200,
            "data": {
                "object": {
                    "id": "sub_123",
                    "status": "active",
                    "customer_email": "billing@example.com",
                    "trial_end": 1746624300,
                    "current_period_end": 1746700000,
                    "items": {
                        "data": [
                            {
                                "price": {
                                    "id": "price_123"
                                }
                            }
                        ]
                    },
                }
            },
        }
    ).encode("utf-8")
    timestamp = str(int(time.time()))
    signed_payload = f"{timestamp}.{body.decode('utf-8')}".encode("utf-8")
    signature = hmac.new(b"whsec_test", signed_payload, hashlib.sha256).hexdigest()
    request = RequestFactory().post(
        "/payments/stripe/webhook/",
        data=body,
        content_type="application/json",
        HTTP_STRIPE_SIGNATURE=f"t={timestamp},v1={signature}",
    )
    request._body = body

    event = service.parse_webhook(request)

    assert event.event_type == "SUBSCRIPTION_UPDATED"
    assert event.subscription_id == "sub_123"
