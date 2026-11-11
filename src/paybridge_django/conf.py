from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from typing import Any

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured

from .constants import DEFAULT_GATEWAY, SUPPORTED_GATEWAYS


@dataclass(frozen=True, slots=True)
class PayBridgeSettings:
    default_gateway: str
    process_webhooks_async: bool
    timeout_seconds: int
    paystack_secret_key: str | None
    paystack_webhook_secret: str | None
    flutterwave_public_key: str | None
    flutterwave_secret_key: str | None
    flutterwave_webhook_secret: str | None
    stripe_secret_key: str | None
    stripe_webhook_secret: str | None


def clear_paybridge_settings_cache() -> None:
    get_paybridge_settings.cache_clear()


@lru_cache(maxsize=1)
def get_paybridge_settings() -> PayBridgeSettings:
    payload = dict(getattr(settings, "PAYBRIDGE", {}))
    default_gateway = str(payload.get("DEFAULT_GATEWAY", DEFAULT_GATEWAY)).lower()

    if default_gateway not in SUPPORTED_GATEWAYS:
        raise ImproperlyConfigured(
            f"PAYBRIDGE['DEFAULT_GATEWAY'] must be one of {', '.join(SUPPORTED_GATEWAYS)}."
        )

    config = PayBridgeSettings(
        default_gateway=default_gateway,
        process_webhooks_async=bool(payload.get("PROCESS_WEBHOOKS_ASYNC", False)),
        timeout_seconds=int(payload.get("TIMEOUT_SECONDS", 10)),
        paystack_secret_key=_optional(payload.get("PAYSTACK_SECRET_KEY")),
        paystack_webhook_secret=_optional(payload.get("PAYSTACK_WEBHOOK_SECRET")),
        flutterwave_public_key=_optional(payload.get("FLUTTERWAVE_PUBLIC_KEY")),
        flutterwave_secret_key=_optional(payload.get("FLUTTERWAVE_SECRET_KEY")),
        flutterwave_webhook_secret=_optional(payload.get("FLUTTERWAVE_WEBHOOK_SECRET")),
        stripe_secret_key=_optional(payload.get("STRIPE_SECRET_KEY")),
        stripe_webhook_secret=_optional(payload.get("STRIPE_WEBHOOK_SECRET")),
    )

    validate_gateway_settings(default_gateway, config)
    return config


def validate_gateway_settings(gateway: str, config: PayBridgeSettings | None = None) -> None:
    resolved = config or get_paybridge_settings()
    required_by_gateway: dict[str, dict[str, Any]] = {
        "paystack": {
            "PAYSTACK_SECRET_KEY": resolved.paystack_secret_key,
        },
        "flutterwave": {
            "FLUTTERWAVE_PUBLIC_KEY": resolved.flutterwave_public_key,
            "FLUTTERWAVE_SECRET_KEY": resolved.flutterwave_secret_key,
            "FLUTTERWAVE_WEBHOOK_SECRET": resolved.flutterwave_webhook_secret,
        },
        "stripe": {
            "STRIPE_SECRET_KEY": resolved.stripe_secret_key,
            "STRIPE_WEBHOOK_SECRET": resolved.stripe_webhook_secret,
        },
    }

    missing = [key for key, value in required_by_gateway[gateway].items() if not value]
    if missing:
        joined = ", ".join(missing)
        raise ImproperlyConfigured(f"Missing PAYBRIDGE settings for {gateway}: {joined}.")


def gateway_config(gateway: str) -> dict[str, Any]:
    config = get_paybridge_settings()
    validate_gateway_settings(gateway, config)
    return {
        "default_gateway": config.default_gateway,
        "process_webhooks_async": config.process_webhooks_async,
        "timeout_seconds": config.timeout_seconds,
        "paystack_secret_key": config.paystack_secret_key,
        "paystack_webhook_secret": config.paystack_webhook_secret,
        "flutterwave_public_key": config.flutterwave_public_key,
        "flutterwave_secret_key": config.flutterwave_secret_key,
        "flutterwave_webhook_secret": config.flutterwave_webhook_secret,
        "stripe_secret_key": config.stripe_secret_key,
        "stripe_webhook_secret": config.stripe_webhook_secret,
    }


def _optional(value: Any) -> str | None:
    if value is None:
        return None
    cleaned = str(value).strip()
    return cleaned or None
