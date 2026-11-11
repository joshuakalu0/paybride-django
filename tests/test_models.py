import pytest

from paybridge_django.models import PayBridgeSubscription, PayBridgeTransaction
from paybridge_django.subscriptions import has_active_subscription


@pytest.mark.django_db
def test_transaction_queryset_helpers():
    PayBridgeTransaction.objects.create(
        reference="pay_1",
        gateway="paystack",
        amount="150.00",
        currency="NGN",
        status="SUCCESS",
        email="owner@example.com",
    )
    PayBridgeTransaction.objects.create(
        reference="pay_2",
        gateway="stripe",
        amount="70.00",
        currency="USD",
        status="FAILED",
        email="owner@example.com",
    )

    assert PayBridgeTransaction.objects.successful().count() == 1
    assert PayBridgeTransaction.objects.failed().count() == 1
    assert PayBridgeTransaction.objects.by_gateway("stripe").count() == 1
    assert PayBridgeTransaction.objects.by_email("owner@example.com").count() == 2


@pytest.mark.django_db
def test_has_active_subscription_checks_status():
    PayBridgeSubscription.objects.create(
        customer_email="member@example.com",
        gateway="stripe",
        gateway_subscription_id="sub_123",
        plan_id="price_123",
        status="ACTIVE",
    )

    assert has_active_subscription("member@example.com") is True
    assert has_active_subscription("missing@example.com") is False
