import hashlib
import hmac
import json

import pytest
import responses
import respx
from django.test import RequestFactory

from paybridge_django.services import get_gateway


@pytest.mark.django_db
@responses.activate
def test_paystack_initialize_and_verify():
    service = get_gateway("paystack")

    responses.post(
        "https://api.paystack.co/transaction/initialize",
        json={
            "status": True,
            "message": "Authorization URL created",
            "data": {
                "reference": "pst_ref_123",
                "authorization_url": "https://checkout.paystack.com/ref",
                "access_code": "ACCESS_123",
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
    assert init_result.reference == "pst_ref_123"

    responses.get(
        "https://api.paystack.co/transaction/verify/pst_ref_123",
        json={
            "status": True,
            "message": "Verification successful",
            "data": {
                "reference": "pst_ref_123",
                "status": "success",
                "amount": 15000,
                "currency": "NGN",
                "paid_at": "2026-05-07T12:00:00+00:00",
                "customer": {
                    "email": "owner@example.com",
                    "customer_code": "CUS_123",
                },
            },
        },
        status=200,
    )
    verify_result = service.verify_transaction("pst_ref_123")
    assert verify_result.status == "SUCCESS"
    assert str(verify_result.amount) == "150.00"


@pytest.mark.asyncio
@pytest.mark.django_db
async def test_paystack_async_initialize():
    service = get_gateway("paystack")
    with respx.mock(base_url="https://api.paystack.co") as router:
        router.post("/transaction/initialize").respond(
            200,
            json={
                "status": True,
                "message": "Authorization URL created",
                "data": {
                    "reference": "pst_async_123",
                    "authorization_url": "https://checkout.paystack.com/async",
                    "access_code": "ACCESS_ASYNC",
                },
            },
        )
        result = await service.ainitialize_transaction(
            amount="250.00",
            email="async@example.com",
            currency="NGN",
            callback_url="https://example.com/return/",
        )

    assert result.reference == "pst_async_123"


@pytest.mark.django_db
def test_paystack_webhook_parsing():
    service = get_gateway("paystack")
    payload = json.dumps(
        {
            "event": "charge.success",
            "data": {
                "reference": "pst_webhook_123",
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

    event = service.parse_webhook(request)

    assert event.event_type == "PAYMENT_SUCCESS"
    assert event.reference == "pst_webhook_123"
