from __future__ import annotations

from decimal import Decimal

from django.db import models

from .constants import (
    SUBSCRIPTION_STATUS_CHOICES,
    SUBSCRIPTION_STATUS_PENDING,
    SUPPORTED_GATEWAYS,
    TRANSACTION_STATUS_CHOICES,
    TRANSACTION_STATUS_FAILED,
    TRANSACTION_STATUS_PENDING,
    TRANSACTION_STATUS_SUCCESS,
)
from .types import WebhookEvent


class PayBridgeTransactionQuerySet(models.QuerySet):
    def by_email(self, email: str):
        return self.filter(email__iexact=email)

    def by_gateway(self, gateway: str):
        return self.filter(gateway=gateway)

    def failed(self):
        return self.filter(status=TRANSACTION_STATUS_FAILED)

    def successful(self):
        return self.filter(status=TRANSACTION_STATUS_SUCCESS)


class PayBridgeTransaction(models.Model):
    reference = models.CharField(max_length=255, unique=True)
    gateway = models.CharField(max_length=32, choices=[(item, item.title()) for item in SUPPORTED_GATEWAYS])
    amount = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True)
    currency = models.CharField(max_length=8, default="NGN")
    status = models.CharField(
        max_length=16,
        choices=TRANSACTION_STATUS_CHOICES,
        default=TRANSACTION_STATUS_PENDING,
    )
    email = models.EmailField(blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    webhook_payload = models.JSONField(null=True, blank=True)
    webhook_received_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = PayBridgeTransactionQuerySet.as_manager()

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["gateway", "status", "created_at"]),
            models.Index(fields=["email", "created_at"]),
        ]

    def __str__(self) -> str:
        return f"{self.gateway}:{self.reference}"

    @classmethod
    def get_manager(cls):
        return cls.objects

    def to_webhook_event(self) -> WebhookEvent:
        return WebhookEvent(
            gateway=self.gateway,
            event_type=str(self.metadata.get("event_type", "UNKNOWN")),
            event_name=str(self.metadata.get("event_name", "unknown")),
            reference=self.reference,
            status=self.status,
            amount=self.amount if isinstance(self.amount, Decimal) else None,
            currency=self.currency or None,
            email=self.email or None,
            customer_id=_string_or_none(self.metadata.get("customer_id")),
            subscription_id=_string_or_none(self.metadata.get("subscription_id")),
            metadata=self.metadata,
            payload=self.webhook_payload or {},
        )


class PayBridgeSubscription(models.Model):
    customer_email = models.EmailField()
    gateway = models.CharField(max_length=32, choices=[(item, item.title()) for item in SUPPORTED_GATEWAYS])
    gateway_subscription_id = models.CharField(max_length=255, unique=True)
    plan_id = models.CharField(max_length=255, blank=True)
    status = models.CharField(
        max_length=24,
        choices=SUBSCRIPTION_STATUS_CHOICES,
        default=SUBSCRIPTION_STATUS_PENDING,
    )
    trial_end = models.DateTimeField(null=True, blank=True)
    current_period_end = models.DateTimeField(null=True, blank=True)
    cancel_at = models.DateTimeField(null=True, blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["gateway", "status"]),
            models.Index(fields=["customer_email", "status"]),
        ]

    def __str__(self) -> str:
        return f"{self.gateway}:{self.gateway_subscription_id}"


def _string_or_none(value):
    if value is None:
        return None
    text = str(value).strip()
    return text or None
