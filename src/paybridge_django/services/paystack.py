from __future__ import annotations

from datetime import timedelta
from typing import Any

from asgiref.sync import sync_to_async
from django.http import HttpRequest
from django.utils import timezone

from ..constants import WEBHOOK_EVENT_PAYMENT_FAILED, WEBHOOK_EVENT_PAYMENT_SUCCESS
from ..exceptions import PayBridgeError
from ..types import CustomerResult, PaymentInitResult, SubscriptionResult, TransactionResult, WebhookEvent
from .base import PaymentGateway
from .processing import record_initialization, record_verification


class PaystackService(PaymentGateway):
    gateway_name = "paystack"
    base_url = "https://api.paystack.co"

    def initialize_transaction(
        self,
        amount,
        email: str,
        currency: str = "NGN",
        callback_url: str = "",
        **kwargs,
    ) -> PaymentInitResult:
        response = self._request(
            "POST",
            f"{self.base_url}/transaction/initialize",
            headers=self._headers(),
            json={
                "amount": self._minor_units(amount),
                "callback_url": callback_url,
                "currency": currency,
                "email": email,
                "metadata": kwargs.get("metadata") or {},
                "reference": kwargs.get("reference"),
            },
        )
        data = response["data"]
        result = PaymentInitResult(
            gateway=self.gateway_name,
            reference=str(data["reference"]),
            amount=self._coerce_amount(amount),
            currency=currency,
            email=email,
            payment_url=data.get("authorization_url"),
            access_code=data.get("access_code"),
            raw=response,
        )
        record_initialization(result)
        return result

    async def ainitialize_transaction(self, amount, email: str, currency: str = "NGN", callback_url: str = "", **kwargs):
        response = await self._arequest(
            "POST",
            f"{self.base_url}/transaction/initialize",
            headers=self._headers(),
            json={
                "amount": self._minor_units(amount),
                "callback_url": callback_url,
                "currency": currency,
                "email": email,
                "metadata": kwargs.get("metadata") or {},
                "reference": kwargs.get("reference"),
            },
        )
        data = response["data"]
        result = PaymentInitResult(
            gateway=self.gateway_name,
            reference=str(data["reference"]),
            amount=self._coerce_amount(amount),
            currency=currency,
            email=email,
            payment_url=data.get("authorization_url"),
            access_code=data.get("access_code"),
            raw=response,
        )
        await sync_to_async(record_initialization)(result)
        return result

    def verify_transaction(self, reference: str) -> TransactionResult:
        response = self._request(
            "GET",
            f"{self.base_url}/transaction/verify/{reference}",
            headers=self._headers(),
        )
        result = self._build_transaction_result(response["data"])
        record_verification(result)
        return result

    async def averify_transaction(self, reference: str) -> TransactionResult:
        response = await self._arequest(
            "GET",
            f"{self.base_url}/transaction/verify/{reference}",
            headers=self._headers(),
        )
        result = self._build_transaction_result(response["data"])
        await sync_to_async(record_verification)(result)
        return result

    def create_customer(self, email: str, name: str | None = None, **kwargs) -> CustomerResult:
        first_name, last_name = _split_name(name)
        response = self._request(
            "POST",
            f"{self.base_url}/customer",
            headers=self._headers(),
            json={
                "email": email,
                "first_name": first_name,
                "last_name": last_name,
                "phone": kwargs.get("phone"),
                "metadata": kwargs.get("metadata") or {},
            },
        )
        data = response["data"]
        return CustomerResult(
            gateway=self.gateway_name,
            customer_id=str(data["customer_code"]),
            email=data["email"],
            name=name,
            raw=response,
        )

    async def acreate_customer(self, email: str, name: str | None = None, **kwargs) -> CustomerResult:
        first_name, last_name = _split_name(name)
        response = await self._arequest(
            "POST",
            f"{self.base_url}/customer",
            headers=self._headers(),
            json={
                "email": email,
                "first_name": first_name,
                "last_name": last_name,
                "phone": kwargs.get("phone"),
                "metadata": kwargs.get("metadata") or {},
            },
        )
        data = response["data"]
        return CustomerResult(
            gateway=self.gateway_name,
            customer_id=str(data["customer_code"]),
            email=data["email"],
            name=name,
            raw=response,
        )

    def create_subscription(self, amount, email: str, currency: str = "NGN", callback_url: str = "", **kwargs):
        payload = {
            "amount": self._minor_units(amount),
            "callback_url": callback_url,
            "currency": currency,
            "email": email,
            "metadata": kwargs.get("metadata") or {},
            "plan": kwargs.get("plan_code"),
            "reference": kwargs.get("reference"),
        }
        if not payload["plan"] and kwargs.get("plan_name") and kwargs.get("interval"):
            payload["plan"] = self._create_plan(
                amount=amount,
                currency=currency,
                interval=str(kwargs["interval"]),
                name=str(kwargs["plan_name"]),
            )
        if not payload["plan"]:
            raise PayBridgeError(
                "Paystack subscriptions require plan_code or plan_name + interval.",
                code="invalid_request",
                gateway=self.gateway_name,
            )
        response = self._request(
            "POST",
            f"{self.base_url}/transaction/initialize",
            headers=self._headers(),
            json=payload,
        )
        data = response["data"]
        return SubscriptionResult(
            gateway=self.gateway_name,
            status="PENDING",
            subscription_id=str(payload["plan"]),
            customer_email=email,
            checkout_url=data.get("authorization_url"),
            raw=response,
        )

    async def acreate_subscription(self, amount, email: str, currency: str = "NGN", callback_url: str = "", **kwargs):
        payload = {
            "amount": self._minor_units(amount),
            "callback_url": callback_url,
            "currency": currency,
            "email": email,
            "metadata": kwargs.get("metadata") or {},
            "plan": kwargs.get("plan_code"),
            "reference": kwargs.get("reference"),
        }
        if not payload["plan"] and kwargs.get("plan_name") and kwargs.get("interval"):
            payload["plan"] = await self._acreate_plan(
                amount=amount,
                currency=currency,
                interval=str(kwargs["interval"]),
                name=str(kwargs["plan_name"]),
            )
        if not payload["plan"]:
            raise PayBridgeError(
                "Paystack subscriptions require plan_code or plan_name + interval.",
                code="invalid_request",
                gateway=self.gateway_name,
            )
        response = await self._arequest(
            "POST",
            f"{self.base_url}/transaction/initialize",
            headers=self._headers(),
            json=payload,
        )
        data = response["data"]
        return SubscriptionResult(
            gateway=self.gateway_name,
            status="PENDING",
            subscription_id=str(payload["plan"]),
            customer_email=email,
            checkout_url=data.get("authorization_url"),
            raw=response,
        )

    def parse_webhook(self, request: HttpRequest) -> WebhookEvent:
        signature = request.headers.get("x-paystack-signature")
        if not signature or not self._verify_hmac_hex(
            self.config["paystack_webhook_secret"] or self.config["paystack_secret_key"],
            request.body,
            signature,
        ):
            raise PayBridgeError(
                "Paystack webhook signature is invalid.",
                code="invalid_signature",
                gateway=self.gateway_name,
            )

        payload = self._json_body(request)
        data = payload.get("data") or {}
        status = _map_paystack_status(data.get("status"))
        event_type = WEBHOOK_EVENT_PAYMENT_SUCCESS if status == "SUCCESS" else WEBHOOK_EVENT_PAYMENT_FAILED
        event = WebhookEvent(
            gateway=self.gateway_name,
            event_type=event_type,
            event_name=str(payload.get("event", "unknown")),
            reference=_string_or_none(data.get("reference")),
            status=status,
            amount=self._coerce_amount((data.get("amount") or 0) / 100) if data.get("amount") is not None else None,
            currency=_string_or_none(data.get("currency")),
            email=((data.get("customer") or {}).get("email") if isinstance(data.get("customer"), dict) else None),
            customer_id=((data.get("customer") or {}).get("customer_code") if isinstance(data.get("customer"), dict) else None),
            occurred_at=self._parse_datetime(data.get("paid_at")),
            metadata={"gateway_status": data.get("status")},
            payload=payload,
        )
        return event

    def fetch_recent_transactions(self, from_dt, to_dt):
        response = self._request(
            "GET",
            f"{self.base_url}/transaction",
            headers=self._headers(),
            params={
                "from": from_dt.date().isoformat(),
                "to": to_dt.date().isoformat(),
                "perPage": 100,
            },
        )
        return [self._build_transaction_result(item) for item in response.get("data", [])]

    def _create_plan(self, *, amount, currency: str, interval: str, name: str) -> str:
        response = self._request(
            "POST",
            f"{self.base_url}/plan",
            headers=self._headers(),
            json={
                "amount": self._minor_units(amount),
                "currency": currency,
                "interval": interval,
                "name": name,
            },
        )
        return str(response["data"]["plan_code"])

    async def _acreate_plan(self, *, amount, currency: str, interval: str, name: str) -> str:
        response = await self._arequest(
            "POST",
            f"{self.base_url}/plan",
            headers=self._headers(),
            json={
                "amount": self._minor_units(amount),
                "currency": currency,
                "interval": interval,
                "name": name,
            },
        )
        return str(response["data"]["plan_code"])

    def _build_transaction_result(self, data: dict[str, Any]) -> TransactionResult:
        return TransactionResult(
            gateway=self.gateway_name,
            reference=str(data["reference"]),
            status=_map_paystack_status(data.get("status")),
            amount=self._coerce_amount((data.get("amount") or 0) / 100) if data.get("amount") is not None else None,
            currency=_string_or_none(data.get("currency")),
            email=((data.get("customer") or {}).get("email") if isinstance(data.get("customer"), dict) else None),
            customer_id=((data.get("customer") or {}).get("customer_code") if isinstance(data.get("customer"), dict) else None),
            paid_at=self._parse_datetime(data.get("paid_at")),
            raw=data,
        )

    def _headers(self):
        return {
            "Authorization": f"Bearer {self.config['paystack_secret_key']}",
            "Content-Type": "application/json",
        }


def _map_paystack_status(value):
    raw = str(value or "").lower()
    if raw == "success":
        return "SUCCESS"
    if raw in {"reversed", "refunded"}:
        return "REFUNDED"
    if raw in {"failed", "abandoned"}:
        return "FAILED"
    return "PENDING"


def _split_name(name: str | None):
    if not name:
        return "", ""
    parts = name.split()
    return parts[0], " ".join(parts[1:])


def _string_or_none(value):
    if value is None:
        return None
    text = str(value).strip()
    return text or None
