import pytest
import responses
from django.core.management import call_command

from paybridge_django.models import PayBridgeSubscription, PayBridgeTransaction


@pytest.mark.django_db
@responses.activate
def test_sync_transactions_command_reconciles_gateway_data():
    responses.get(
        "https://api.paystack.co/transaction",
        json={
            "status": True,
            "message": "Fetched",
            "data": [
                {
                    "reference": "pst_sync_123",
                    "status": "success",
                    "amount": 12500,
                    "currency": "NGN",
                    "paid_at": "2026-05-07T12:00:00+00:00",
                    "customer": {
                        "email": "owner@example.com",
                        "customer_code": "CUS_777",
                    },
                }
            ],
        },
        status=200,
    )

    call_command("paybridge_sync_transactions", gateway="paystack", days=7)

    transaction = PayBridgeTransaction.objects.get(reference="pst_sync_123")
    assert transaction.status == "SUCCESS"


@pytest.mark.django_db
@responses.activate
def test_check_subscriptions_command_refreshes_stripe_status():
    PayBridgeSubscription.objects.create(
        customer_email="billing@example.com",
        gateway="stripe",
        gateway_subscription_id="sub_sync_123",
        plan_id="price_old",
        status="PENDING",
    )

    responses.get(
        "https://api.stripe.com/v1/subscriptions/sub_sync_123",
        json={
            "id": "sub_sync_123",
            "status": "active",
            "trial_end": None,
            "current_period_end": 1746700000,
            "cancel_at": None,
            "items": {
                "data": [
                    {
                        "price": {
                            "id": "price_new"
                        }
                    }
                ]
            },
        },
        status=200,
    )

    call_command("paybridge_check_subscriptions")

    subscription = PayBridgeSubscription.objects.get(gateway_subscription_id="sub_sync_123")
    assert subscription.status == "ACTIVE"
    assert subscription.plan_id == "price_new"
