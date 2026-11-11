from .base import PaymentGateway
from .flutterwave import FlutterwaveService
from .paystack import PaystackService
from .stripe import StripeService
from ..conf import get_paybridge_settings


def get_gateway(name: str | None = None) -> PaymentGateway:
    gateway_name = (name or get_paybridge_settings().default_gateway).lower()
    registry = {
        "paystack": PaystackService,
        "flutterwave": FlutterwaveService,
        "stripe": StripeService,
    }
    return registry[gateway_name]()


__all__ = [
    "FlutterwaveService",
    "PaystackService",
    "PaymentGateway",
    "StripeService",
    "get_gateway",
]
