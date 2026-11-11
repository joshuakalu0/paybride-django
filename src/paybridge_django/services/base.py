from __future__ import annotations

import asyncio
import base64
import hmac
import json
from abc import ABC, abstractmethod
from datetime import datetime, timezone as dt_timezone
from decimal import Decimal, ROUND_HALF_UP
from hashlib import sha256, sha512
from typing import Any

import httpx
import requests
from django.http import HttpRequest
from django.utils import timezone

from ..conf import gateway_config
from ..exceptions import PayBridgeError
from ..types import CustomerResult, PaymentInitResult, SubscriptionResult, TransactionResult, WebhookEvent


class PaymentGateway(ABC):
    gateway_name: str

    def __init__(self) -> None:
        self.config = gateway_config(self.gateway_name)
        self.timeout = float(self.config["timeout_seconds"])

    @abstractmethod
    def initialize_transaction(
        self,
        amount: Decimal | int | float | str,
        email: str,
        currency: str,
        callback_url: str,
        **kwargs,
    ) -> PaymentInitResult:
        raise NotImplementedError

    @abstractmethod
    def verify_transaction(self, reference: str) -> TransactionResult:
        raise NotImplementedError

    @abstractmethod
    def create_customer(self, email: str, name: str | None = None, **kwargs) -> CustomerResult:
        raise NotImplementedError

    @abstractmethod
    def create_subscription(self, *args, **kwargs) -> SubscriptionResult:
        raise NotImplementedError

    @abstractmethod
    def parse_webhook(self, request: HttpRequest) -> WebhookEvent:
        raise NotImplementedError

    async def ainitialize_transaction(
        self,
        amount: Decimal | int | float | str,
        email: str,
        currency: str,
        callback_url: str,
        **kwargs,
    ) -> PaymentInitResult:
        return await asyncio.to_thread(
            self.initialize_transaction,
            amount,
            email,
            currency,
            callback_url,
            **kwargs,
        )

    async def averify_transaction(self, reference: str) -> TransactionResult:
        return await asyncio.to_thread(self.verify_transaction, reference)

    async def acreate_customer(self, email: str, name: str | None = None, **kwargs) -> CustomerResult:
        return await asyncio.to_thread(self.create_customer, email, name, **kwargs)

    async def acreate_subscription(self, *args, **kwargs) -> SubscriptionResult:
        return await asyncio.to_thread(self.create_subscription, *args, **kwargs)

    async def aparse_webhook(self, request: HttpRequest) -> WebhookEvent:
        return await asyncio.to_thread(self.parse_webhook, request)

    def fetch_recent_transactions(self, from_dt: datetime, to_dt: datetime) -> list[TransactionResult]:
        raise PayBridgeError(
            f"{self.gateway_name} does not implement transaction synchronization.",
            code="unsupported_operation",
            gateway=self.gateway_name,
        )

    def refresh_subscription(self, subscription):
        raise PayBridgeError(
            f"{self.gateway_name} does not implement subscription synchronization.",
            code="unsupported_operation",
            gateway=self.gateway_name,
        )

    def _request(self, method: str, url: str, **kwargs) -> dict[str, Any]:
        response = requests.request(method, url, timeout=self.timeout, **kwargs)
        try:
            payload = response.json()
        except ValueError as error:
            raise PayBridgeError(
                "Gateway response could not be parsed as JSON.",
                code="parse_error",
                gateway=self.gateway_name,
            ) from error

        if response.status_code >= 400:
            raise PayBridgeError(
                payload.get("message") or f"{self.gateway_name} request failed.",
                code="gateway_error",
                gateway=self.gateway_name,
            )

        return payload

    async def _arequest(self, method: str, url: str, **kwargs) -> dict[str, Any]:
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.request(method, url, **kwargs)
        try:
            payload = response.json()
        except ValueError as error:
            raise PayBridgeError(
                "Gateway response could not be parsed as JSON.",
                code="parse_error",
                gateway=self.gateway_name,
            ) from error

        if response.status_code >= 400:
            raise PayBridgeError(
                payload.get("message") or f"{self.gateway_name} request failed.",
                code="gateway_error",
                gateway=self.gateway_name,
            )

        return payload

    def _coerce_amount(self, amount: Decimal | int | float | str) -> Decimal:
        return Decimal(str(amount)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    def _minor_units(self, amount: Decimal | int | float | str) -> int:
        return int((self._coerce_amount(amount) * Decimal("100")).to_integral_value())

    def _parse_datetime(self, value: Any) -> datetime | None:
        if value in (None, ""):
            return None
        if isinstance(value, datetime):
            return value
        text = str(value).replace("Z", "+00:00")
        try:
            parsed = datetime.fromisoformat(text)
        except ValueError:
            return None
        if timezone.is_naive(parsed):
            return timezone.make_aware(parsed, dt_timezone.utc)
        return parsed

    def _json_body(self, request: HttpRequest) -> dict[str, Any]:
        try:
            return json.loads(request.body.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as error:
            raise PayBridgeError(
                "Webhook payload could not be decoded.",
                code="invalid_webhook",
                gateway=self.gateway_name,
            ) from error

    def _verify_hmac_hex(self, secret: str, payload: bytes, signature: str, *, algorithm=sha512) -> bool:
        expected = hmac.new(secret.encode("utf-8"), payload, algorithm).hexdigest()
        return hmac.compare_digest(expected, signature)

    def _verify_hmac_base64(self, secret: str, payload: bytes, signature: str) -> bool:
        expected = hmac.new(secret.encode("utf-8"), payload, sha256).digest()
        return hmac.compare_digest(expected, base64.b64decode(signature.encode("utf-8")))
