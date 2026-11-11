from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime
from decimal import Decimal
from typing import Any

from .constants import (
    SUBSCRIPTION_STATUS_PENDING,
    TRANSACTION_STATUS_PENDING,
    WEBHOOK_EVENT_UNKNOWN,
)


def _serialize(value: Any) -> Any:
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, dict):
        return {key: _serialize(nested) for key, nested in value.items()}
    if isinstance(value, list):
        return [_serialize(item) for item in value]
    return value


def _deserialize_datetime(value: Any) -> datetime | None:
    if not value:
        return None
    if isinstance(value, datetime):
        return value
    return datetime.fromisoformat(str(value))


def _deserialize_decimal(value: Any) -> Decimal | None:
    if value is None or value == "":
        return None
    return Decimal(str(value))


@dataclass(slots=True)
class PaymentInitResult:
    gateway: str
    reference: str
    amount: Decimal
    currency: str
    email: str
    payment_url: str | None = None
    client_secret: str | None = None
    access_code: str | None = None
    status: str = TRANSACTION_STATUS_PENDING
    raw: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return _serialize(asdict(self))


@dataclass(slots=True)
class TransactionResult:
    gateway: str
    reference: str
    status: str
    amount: Decimal | None = None
    currency: str | None = None
    email: str | None = None
    customer_id: str | None = None
    paid_at: datetime | None = None
    raw: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return _serialize(asdict(self))

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "TransactionResult":
        return cls(
            gateway=str(payload["gateway"]),
            reference=str(payload["reference"]),
            status=str(payload["status"]),
            amount=_deserialize_decimal(payload.get("amount")),
            currency=payload.get("currency"),
            email=payload.get("email"),
            customer_id=payload.get("customer_id"),
            paid_at=_deserialize_datetime(payload.get("paid_at")),
            raw=payload.get("raw") or {},
        )


@dataclass(slots=True)
class CustomerResult:
    gateway: str
    customer_id: str
    email: str
    name: str | None = None
    raw: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return _serialize(asdict(self))


@dataclass(slots=True)
class SubscriptionResult:
    gateway: str
    status: str = SUBSCRIPTION_STATUS_PENDING
    subscription_id: str | None = None
    customer_email: str | None = None
    checkout_url: str | None = None
    next_billing_date: datetime | None = None
    trial_end: datetime | None = None
    raw: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return _serialize(asdict(self))


@dataclass(slots=True)
class WebhookEvent:
    gateway: str
    event_type: str = WEBHOOK_EVENT_UNKNOWN
    event_name: str = "unknown"
    reference: str | None = None
    status: str | None = None
    amount: Decimal | None = None
    currency: str | None = None
    email: str | None = None
    customer_id: str | None = None
    subscription_id: str | None = None
    occurred_at: datetime | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    payload: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return _serialize(asdict(self))

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "WebhookEvent":
        return cls(
            gateway=str(payload["gateway"]),
            event_type=str(payload.get("event_type", WEBHOOK_EVENT_UNKNOWN)),
            event_name=str(payload.get("event_name", "unknown")),
            reference=payload.get("reference"),
            status=payload.get("status"),
            amount=_deserialize_decimal(payload.get("amount")),
            currency=payload.get("currency"),
            email=payload.get("email"),
            customer_id=payload.get("customer_id"),
            subscription_id=payload.get("subscription_id"),
            occurred_at=_deserialize_datetime(payload.get("occurred_at")),
            metadata=payload.get("metadata") or {},
            payload=payload.get("payload") or {},
        )
