from __future__ import annotations

from decimal import Decimal
from typing import Any

from django.utils import timezone

from ..constants import (
    SUBSCRIPTION_STATUS_ACTIVE,
    SUBSCRIPTION_STATUS_CANCELLED,
    SUBSCRIPTION_STATUS_INCOMPLETE,
    SUBSCRIPTION_STATUS_PENDING,
    SUBSCRIPTION_STATUS_PAST_DUE,
    SUBSCRIPTION_STATUS_TRIALING,
    WEBHOOK_EVENT_PAYMENT_FAILED,
    WEBHOOK_EVENT_PAYMENT_SUCCESS,
    WEBHOOK_EVENT_SUBSCRIPTION_CANCELLED,
    WEBHOOK_EVENT_SUBSCRIPTION_CREATED,
    WEBHOOK_EVENT_SUBSCRIPTION_UPDATED,
)
from ..models import PayBridgeSubscription, PayBridgeTransaction
from ..signals import (
    paybridge_payment_failed,
    paybridge_payment_success,
    paybridge_subscription_updated,
)
from ..types import PaymentInitResult, TransactionResult, WebhookEvent


def record_initialization(result: PaymentInitResult) -> PayBridgeTransaction:
    transaction, _ = PayBridgeTransaction.objects.update_or_create(
        reference=result.reference,
        defaults={
            "gateway": result.gateway,
            "amount": result.amount,
            "currency": result.currency,
            "email": result.email,
            "metadata": {
                "init_status": result.status,
            },
            "status": result.status,
        },
    )
    return transaction


def record_verification(result: TransactionResult) -> PayBridgeTransaction:
    transaction, _ = PayBridgeTransaction.objects.update_or_create(
        reference=result.reference,
        defaults={
            "gateway": result.gateway,
            "amount": result.amount,
            "currency": result.currency or "NGN",
            "email": result.email or "",
            "metadata": {
                "customer_id": result.customer_id,
                "paid_at": result.paid_at.isoformat() if result.paid_at else None,
            },
            "status": result.status,
        },
    )
    return transaction


def process_webhook_event(event: WebhookEvent) -> tuple[PayBridgeTransaction | None, PayBridgeSubscription | None]:
    transaction = None
    subscription = None

    if event.reference:
        transaction, _ = PayBridgeTransaction.objects.update_or_create(
            reference=event.reference,
            defaults={
                "gateway": event.gateway,
                "amount": event.amount,
                "currency": event.currency or "NGN",
                "email": event.email or "",
                "metadata": _build_transaction_metadata(event),
                "status": event.status or _status_for_event(event.event_type),
                "webhook_payload": event.payload,
                "webhook_received_at": timezone.now(),
            },
        )

    if event.subscription_id:
        subscription, _ = PayBridgeSubscription.objects.update_or_create(
            gateway_subscription_id=event.subscription_id,
            defaults={
                "customer_email": event.email or "",
                "gateway": event.gateway,
                "plan_id": str(event.metadata.get("plan_id", "")),
                "status": _subscription_status_for_event(event),
                "trial_end": _datetime_or_none(event.metadata.get("trial_end")),
                "current_period_end": _datetime_or_none(event.metadata.get("current_period_end")),
                "cancel_at": _datetime_or_none(event.metadata.get("cancel_at")),
                "metadata": event.metadata,
            },
        )

    dispatch_webhook_event(event, transaction=transaction, subscription=subscription)
    return transaction, subscription


def dispatch_webhook_event(
    event: WebhookEvent,
    *,
    transaction: PayBridgeTransaction | None = None,
    subscription: PayBridgeSubscription | None = None,
) -> None:
    if event.event_type == WEBHOOK_EVENT_PAYMENT_SUCCESS:
        paybridge_payment_success.send(
            sender=PayBridgeTransaction,
            event=event,
            transaction=transaction,
        )
    elif event.event_type == WEBHOOK_EVENT_PAYMENT_FAILED:
        paybridge_payment_failed.send(
            sender=PayBridgeTransaction,
            event=event,
            transaction=transaction,
        )

    if event.event_type in {
        WEBHOOK_EVENT_SUBSCRIPTION_CANCELLED,
        WEBHOOK_EVENT_SUBSCRIPTION_CREATED,
        WEBHOOK_EVENT_SUBSCRIPTION_UPDATED,
    }:
        paybridge_subscription_updated.send(
            sender=PayBridgeSubscription,
            event=event,
            subscription=subscription,
        )


def replay_transaction_event(transaction: PayBridgeTransaction) -> None:
    dispatch_webhook_event(transaction.to_webhook_event(), transaction=transaction)


def _build_transaction_metadata(event: WebhookEvent) -> dict[str, Any]:
    metadata = dict(event.metadata)
    metadata.update(
        {
            "event_name": event.event_name,
            "event_type": event.event_type,
            "customer_id": event.customer_id,
            "subscription_id": event.subscription_id,
        }
    )
    return metadata


def _status_for_event(event_type: str) -> str:
    if event_type == WEBHOOK_EVENT_PAYMENT_SUCCESS:
        return "SUCCESS"
    if event_type == WEBHOOK_EVENT_PAYMENT_FAILED:
        return "FAILED"
    return "PENDING"


def _subscription_status_for_event(event: WebhookEvent) -> str:
    raw_status = str(event.metadata.get("status", "")).lower()
    mapped = {
        "active": SUBSCRIPTION_STATUS_ACTIVE,
        "trialing": SUBSCRIPTION_STATUS_TRIALING,
        "past_due": SUBSCRIPTION_STATUS_PAST_DUE,
        "incomplete": SUBSCRIPTION_STATUS_INCOMPLETE,
        "canceled": SUBSCRIPTION_STATUS_CANCELLED,
        "cancelled": SUBSCRIPTION_STATUS_CANCELLED,
    }
    if event.event_type == WEBHOOK_EVENT_SUBSCRIPTION_CANCELLED:
        return SUBSCRIPTION_STATUS_CANCELLED
    if event.event_type == WEBHOOK_EVENT_SUBSCRIPTION_CREATED:
        return mapped.get(raw_status, SUBSCRIPTION_STATUS_ACTIVE)
    if event.event_type == WEBHOOK_EVENT_SUBSCRIPTION_UPDATED:
        return mapped.get(raw_status, SUBSCRIPTION_STATUS_PENDING)
    return SUBSCRIPTION_STATUS_PENDING


def _datetime_or_none(value: Any):
    if not value:
        return None
    if hasattr(value, "tzinfo"):
        return value
    from datetime import datetime

    text = str(value).replace("Z", "+00:00")
    return datetime.fromisoformat(text)
