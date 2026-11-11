import asyncio
import json

import pytest
import responses
import respx
from django.test import RequestFactory

from paybridge_django.services import get_gateway


@pytest.mark.django_db
@responses.activate
def test_flutterwave_initialize_and_verify():
    service = get_gateway("flutterwave")

    responses.post(
        "https://api.flutterwave.com/v3/payments",
        json={
            "status": "success",
            "message": "Hosted link created",
            "data": {
                "link": "https://checkout.flutterwave.com/pay/123",
            },
        },
        status=200,
    )
    init_result = service.initialize_transaction(
        amount="150.00",
        email="owner@example.com",
        currency="NGN",
        callback_url="https://example.com/return/",
    )
    assert init_result.payment_url == "https://checkout.flutterwave.com/pay/123"

    responses.get(
        "https://api.flutterwave.com/v3/transactions/verify_by_reference",
        json={
            "status": "success",
            "message": "Verified",
            "data": {
                "tx_ref": init_result.reference,
                "status": "successful",
                "amount": 150,
                "currency": "NGN",
                "created_at": "2026-05-07T12:00:00+00:00",
                "customer": {
                    "email": "owner@example.com",
                    "id": 99,
                },
            },
        },
        status=200,
    )
    verify_result = service.verify_transaction(init_result.reference)
    assert verify_result.status == "SUCCESS"


@pytest.mark.asyncio
@pytest.mark.django_db
async def test_flutterwave_async_subscription():
    service = get_gateway("flutterwave")
    with respx.mock(base_url="https://api.flutterwave.com") as router:
        router.post("/v3/payment-plans").respond(
            200,
            json={
                "status": "success",
                "message": "Plan created",
                "data": {"id": 22},
            },
        )
        router.post("/v3/payments").respond(
            200,
            json={
                "status": "success",
                "message": "Link created",
                "data": {"link": "https://checkout.flutterwave.com/sub/123"},
            },
        )
        result = await service.acreate_subscription(
            amount="500.00",
            email="billing@example.com",
            currency="NGN",
            callback_url="https://example.com/billing/return/",
            interval="monthly",
            plan_name="Growth",
        )

    assert result.subscription_id == "22"


@pytest.mark.django_db
def test_flutterwave_webhook_parsing():
    service = get_gateway("flutterwave")
    payload = json.dumps(
        {
            "event": "charge.completed",
            "data": {
                "tx_ref": "flw_ref_123",
                "status": "successful",
                "amount": 150,
                "currency": "NGN",
                "customer": {
                    "email": "buyer@example.com",
                    "id": 44,
                },
            },
        }
    ).encode("utf-8")
    request = RequestFactory().post(
        "/payments/flutterwave/webhook/",
        data=payload,
        content_type="application/json",
        HTTP_VERIF_HASH="flw_secret_hash",
    )
    request._body = payload

    event = service.parse_webhook(request)

    assert event.event_type == "PAYMENT_SUCCESS"
    assert event.reference == "flw_ref_123"
