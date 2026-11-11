from __future__ import annotations

import base64
import hmac
from hashlib import sha256
from typing import Any

from asgiref.sync import sync_to_async
from django.http import HttpRequest

from ..constants import WEBHOOK_EVENT_PAYMENT_FAILED, WEBHOOK_EVENT_PAYMENT_SUCCESS
from ..exceptions import PayBridgeError
from ..types import CustomerResult, PaymentInitResult, SubscriptionResult, TransactionResult, WebhookEvent
from .base import PaymentGateway
from .processing import record_initialization, record_verification


class FlutterwaveService(PaymentGateway):
    gateway_name = "flutterwave"
    base_url = "https://api.flutterwave.com"

    def initialize_transaction(
        self,
        amount,
        email: str,
        currency: str = "NGN",
        callback_url: str = "",
        **kwargs,
    ) -> PaymentInitResult:
        tx_ref = kwargs.get("reference") or f"flw_{email.replace('@', '_')}"
        response = self._request(
            "POST",
            f"{self.base_url}/v3/payments",
            headers=self._headers(),
            json={
                "amount": float(self._coerce_amount(amount)),
                "currency": currency,
                "customer": {
                    "email": email,
                    "name": kwargs.get("name") or email.split("@")[0],
                    "phonenumber": kwargs.get("phone"),
                },
                "meta": kwargs.get("metadata") or {},
                "redirect_url": callback_url,
                "tx_ref": tx_ref,
            },
        )
        result = PaymentInitResult(
            gateway=self.gateway_name,
            reference=tx_ref,
            amount=self._coerce_amount(amount),
            currency=currency,
            email=email,
            payment_url=response["data"].get("link"),
            raw=response,
        )
        record_initialization(result)
        return result

    async def ainitialize_transaction(self, amount, email: str, currency: str = "NGN", callback_url: str = "", **kwargs):
        tx_ref = kwargs.get("reference") or f"flw_{email.replace('@', '_')}"
        response = await self._arequest(
            "POST",
            f"{self.base_url}/v3/payments",
            headers=self._headers(),
            json={
                "amount": float(self._coerce_amount(amount)),
                "currency": currency,
                "customer": {
                    "email": email,
                    "name": kwargs.get("name") or email.split("@")[0],
                    "phonenumber": kwargs.get("phone"),
                },
                "meta": kwargs.get("metadata") or {},
                "redirect_url": callback_url,
                "tx_ref": tx_ref,
            },
        )
        result = PaymentInitResult(
            gateway=self.gateway_name,
            reference=tx_ref,
            amount=self._coerce_amount(amount),
            currency=currency,
            email=email,
            payment_url=response["data"].get("link"),
            raw=response,
        )
        await sync_to_async(record_initialization)(result)
        return result

    def verify_transaction(self, reference: str) -> TransactionResult:
        response = self._request(
            "GET",
            f"{self.base_url}/v3/transactions/verify_by_reference",
            headers=self._headers(),
            params={"tx_ref": reference},
        )
        result = self._build_transaction_result(response["data"])
        record_verification(result)
        return result

    async def averify_transaction(self, reference: str) -> TransactionResult:
        response = await self._arequest(
            "GET",
            f"{self.base_url}/v3/transactions/verify_by_reference",
            headers=self._headers(),
            params={"tx_ref": reference},
        )
        result = self._build_transaction_result(response["data"])
        await sync_to_async(record_verification)(result)
        return result

    def create_customer(self, email: str, name: str | None = None, **kwargs) -> CustomerResult:
        response = self._request(
            "POST",
            f"{self.base_url}/customers",
            headers=self._headers(),
            json={
                "email": email,
                "name": name,
                "phone_number": kwargs.get("phone"),
            },
        )
        data = response["data"]
        return CustomerResult(
            gateway=self.gateway_name,
            customer_id=str(data["id"]),
            email=data["email"],
            name=data.get("name") or name,
            raw=response,
        )

    async def acreate_customer(self, email: str, name: str | None = None, **kwargs) -> CustomerResult:
        response = await self._arequest(
            "POST",
            f"{self.base_url}/customers",
            headers=self._headers(),
            json={
                "email": email,
                "name": name,
                "phone_number": kwargs.get("phone"),
            },
        )
        data = response["data"]
        return CustomerResult(
            gateway=self.gateway_name,
            customer_id=str(data["id"]),
            email=data["email"],
            name=data.get("name") or name,
            raw=response,
        )

    def create_subscription(self, amount, email: str, currency: str = "NGN", callback_url: str = "", **kwargs):
        plan_id = kwargs.get("plan_id") or self._create_plan(
            amount=amount,
            currency=currency,
            interval=str(kwargs.get("interval", "monthly")),
            name=str(kwargs.get("plan_name", "PayBridge Plan")),
        )
        response = self._request(
            "POST",
            f"{self.base_url}/v3/payments",
            headers=self._headers(),
            json={
                "currency": currency,
                "customer": {
                    "email": email,
                    "name": kwargs.get("name") or email.split("@")[0],
                    "phonenumber": kwargs.get("phone"),
                },
                "payment_plan": plan_id,
                "redirect_url": callback_url,
                "tx_ref": kwargs.get("reference") or f"flw_sub_{email.replace('@', '_')}",
            },
        )
        return SubscriptionResult(
            gateway=self.gateway_name,
            customer_email=email,
            checkout_url=response["data"].get("link"),
            status="PENDING",
            subscription_id=str(plan_id),
            raw=response,
        )

    async def acreate_subscription(self, amount, email: str, currency: str = "NGN", callback_url: str = "", **kwargs):
        plan_id = kwargs.get("plan_id") or await self._acreate_plan(
            amount=amount,
            currency=currency,
            interval=str(kwargs.get("interval", "monthly")),
            name=str(kwargs.get("plan_name", "PayBridge Plan")),
        )
        response = await self._arequest(
            "POST",
            f"{self.base_url}/v3/payments",
            headers=self._headers(),
            json={
                "currency": currency,
                "customer": {
                    "email": email,
                    "name": kwargs.get("name") or email.split("@")[0],
                    "phonenumber": kwargs.get("phone"),
                },
                "payment_plan": plan_id,
                "redirect_url": callback_url,
                "tx_ref": kwargs.get("reference") or f"flw_sub_{email.replace('@', '_')}",
            },
        )
        return SubscriptionResult(
            gateway=self.gateway_name,
            customer_email=email,
            checkout_url=response["data"].get("link"),
            status="PENDING",
            subscription_id=str(plan_id),
            raw=response,
        )

    def parse_webhook(self, request: HttpRequest) -> WebhookEvent:
        signature = request.headers.get("flutterwave-signature")
        legacy_signature = request.headers.get("verif-hash") or request.headers.get("verifi-hash")
        secret = str(self.config["flutterwave_webhook_secret"])
        if signature:
            expected = base64.b64encode(
                hmac.new(secret.encode("utf-8"), request.body, sha256).digest()
            ).decode("utf-8")
            valid = hmac.compare_digest(expected, signature)
        else:
            valid = bool(legacy_signature and hmac.compare_digest(secret, legacy_signature))

        if not valid:
            raise PayBridgeError(
                "Flutterwave webhook signature is invalid.",
                code="invalid_signature",
                gateway=self.gateway_name,
            )

        payload = self._json_body(request)
        data = payload.get("data") or {}
        status = _map_flutterwave_status(data.get("status"))
        event_type = WEBHOOK_EVENT_PAYMENT_SUCCESS if status == "SUCCESS" else WEBHOOK_EVENT_PAYMENT_FAILED
        event = WebhookEvent(
            gateway=self.gateway_name,
            event_type=event_type,
            event_name=str(payload.get("event", "unknown")),
            reference=_string_or_none(data.get("tx_ref")),
            status=status,
            amount=self._coerce_amount(data.get("amount")) if data.get("amount") is not None else None,
            currency=_string_or_none(data.get("currency")),
            email=((data.get("customer") or {}).get("email") if isinstance(data.get("customer"), dict) else None),
            customer_id=((data.get("customer") or {}).get("id") if isinstance(data.get("customer"), dict) else None),
            occurred_at=self._parse_datetime(data.get("created_at")),
            metadata={"gateway_status": data.get("status")},
            payload=payload,
        )
        return event

    def fetch_recent_transactions(self, from_dt, to_dt):
        response = self._request(
            "GET",
            f"{self.base_url}/v3/transactions",
            headers=self._headers(),
            params={
                "from": from_dt.date().isoformat(),
                "to": to_dt.date().isoformat(),
                "page": 1,
            },
        )
        return [self._build_transaction_result(item) for item in response.get("data", [])]

    def _create_plan(self, *, amount, currency: str, interval: str, name: str) -> str:
        response = self._request(
            "POST",
            f"{self.base_url}/v3/payment-plans",
            headers=self._headers(),
            json={
                "amount": float(self._coerce_amount(amount)),
                "currency": currency,
                "interval": interval,
                "name": name,
            },
        )
        return str(response["data"]["id"])

    async def _acreate_plan(self, *, amount, currency: str, interval: str, name: str) -> str:
        response = await self._arequest(
            "POST",
            f"{self.base_url}/v3/payment-plans",
            headers=self._headers(),
            json={
                "amount": float(self._coerce_amount(amount)),
                "currency": currency,
                "interval": interval,
                "name": name,
            },
        )
        return str(response["data"]["id"])

    def _build_transaction_result(self, data: dict[str, Any]) -> TransactionResult:
        return TransactionResult(
            gateway=self.gateway_name,
            reference=str(data["tx_ref"]),
            status=_map_flutterwave_status(data.get("status")),
            amount=self._coerce_amount(data.get("amount")) if data.get("amount") is not None else None,
            currency=_string_or_none(data.get("currency")),
            email=((data.get("customer") or {}).get("email") if isinstance(data.get("customer"), dict) else None),
            customer_id=((data.get("customer") or {}).get("id") if isinstance(data.get("customer"), dict) else None),
            paid_at=self._parse_datetime(data.get("created_at")),
            raw=data,
        )

    def _headers(self):
        return {
            "Authorization": f"Bearer {self.config['flutterwave_secret_key']}",
            "Content-Type": "application/json",
        }


def _map_flutterwave_status(value):
    raw = str(value or "").lower()
    if raw in {"successful", "completed"}:
        return "SUCCESS"
    if raw in {"failed", "cancelled"}:
        return "FAILED"
    if raw in {"refunded", "reversed"}:
        return "REFUNDED"
    return "PENDING"


def _string_or_none(value):
    if value is None:
        return None
    text = str(value).strip()
    return text or None
