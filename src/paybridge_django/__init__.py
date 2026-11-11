from __future__ import annotations

from typing import TYPE_CHECKING

from .apps import PayBridgeDjangoConfig
from .exceptions import PayBridgeError
from .types import CustomerResult, PaymentInitResult, SubscriptionResult, TransactionResult, WebhookEvent

if TYPE_CHECKING:
    from .services import PaymentGateway

__all__ = [
    "CustomerResult",
    "PayBridgeDjangoConfig",
    "PayBridgeError",
    "PaymentInitResult",
    "SubscriptionResult",
    "TransactionResult",
    "WebhookEvent",
    "get_gateway",
    "has_active_subscription",
]

__version__ = "0.1.0"


def get_gateway(name: str | None = None) -> "PaymentGateway":
    from .services import get_gateway as _get_gateway

    return _get_gateway(name)


def has_active_subscription(email: str) -> bool:
    from .subscriptions import has_active_subscription as _has_active_subscription

    return _has_active_subscription(email)
