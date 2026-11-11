from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from asgiref.sync import sync_to_async
from django.http import HttpRequest
from django.utils import timezone
import stripe

from ..constants import (
    SUBSCRIPTION_STATUS_ACTIVE,
    SUBSCRIPTION_STATUS_CANCELLED,
    SUBSCRIPTION_STATUS_INCOMPLETE,
    SUBSCRIPTION_STATUS_PAST_DUE,
    SUBSCRIPTION_STATUS_PENDING,
    SUBSCRIPTION_STATUS_TRIALING,
    WEBHOOK_EVENT_PAYMENT_FAILED,
    WEBHOOK_EVENT_PAYMENT_SUCCESS,
    WEBHOOK_EVENT_SUBSCRIPTION_CANCELLED,
    WEBHOOK_EVENT_SUBSCRIPTION_CREATED,
    WEBHOOK_EVENT_SUBSCRIPTION_UPDATED,
)
from ..models import PayBridgeSubscription
from ..types import CustomerResult, PaymentInitResult, SubscriptionResult, TransactionResult, WebhookEvent
from .base import PaymentGateway
from .processing import record_initialization, record_verification


class StripeService(PaymentGateway):
    gateway_name = "stripe"
    base_url = "https://api.stripe.com/v1"

    def initialize_transaction(
        self,
        amount,
        email: str,
        currency: str = "USD",
        callback_url: str = "",
        **kwargs,
    ) -> PaymentInitResult:
        response = self._request(
            "POST",
            f"{self.base_url}/payment_intents",
            headers=self._headers(),
            data={
                "amount": self._minor_units(amount),
                "currency": currency.lower(),
                "receipt_email": email,
                "description": kwargs.get("description", ""),
                "metadata[callback_url]": callback_url,
                "metadata[reference]": kwargs.get("reference") or f"stripe_{email.replace('@', '_')}",
                "automatic_payment_methods[enabled]": "true",
            },
        )
        result = PaymentInitResult(
            gateway=self.gateway_name,
            reference=str(response["id"]),
            amount=self._coerce_amount(amount),
            currency=str(response["currency"]).upper(),
            email=email,
            client_secret=response.get("client_secret"),
            raw=response,
        )
        record_initialization(result)
        return result

    async def ainitialize_transaction(self, amount, email: str, currency: str = "USD", callback_url: str = "", **kwargs):
        response = await self._arequest(
            "POST",
            f"{self.base_url}/payment_intents",
            headers=self._headers(),
            data={
                "amount": str(self._minor_units(amount)),
                "currency": currency.lower(),
                "receipt_email": email,
                "description": kwargs.get("description", ""),
                "metadata[callback_url]": callback_url,
                "metadata[reference]": kwargs.get("reference") or f"stripe_{email.replace('@', '_')}",
                "automatic_payment_methods[enabled]": "true",
            },
        )
        result = PaymentInitResult(
            gateway=self.gateway_name,
            reference=str(response["id"]),
            amount=self._coerce_amount(amount),
            currency=str(response["currency"]).upper(),
            email=email,
            client_secret=response.get("client_secret"),
            raw=response,
        )
        await sync_to_async(record_initialization)(result)
        return result

    def verify_transaction(self, reference: str) -> TransactionResult:
        response = self._request(
            "GET",
            f"{self.base_url}/payment_intents/{reference}",
            headers=self._headers(),
        )
        result = self._build_transaction_result(response)
        record_verification(result)
        return result

    async def averify_transaction(self, reference: str) -> TransactionResult:
        response = await self._arequest(
            "GET",
            f"{self.base_url}/payment_intents/{reference}",
            headers=self._headers(),
        )
        result = self._build_transaction_result(response)
        await sync_to_async(record_verification)(result)
        return result

    def create_customer(self, email: str, name: str | None = None, **kwargs) -> CustomerResult:
        response = self._request(
            "POST",
            f"{self.base_url}/customers",
            headers=self._headers(),
            data={
                "email": email,
                "name": name or "",
            },
        )
        return CustomerResult(
            gateway=self.gateway_name,
            customer_id=str(response["id"]),
            email=str(response.get("email") or email),
            name=response.get("name") or name,
            raw=response,
        )

    async def acreate_customer(self, email: str, name: str | None = None, **kwargs) -> CustomerResult:
        response = await self._arequest(
            "POST",
            f"{self.base_url}/customers",
            headers=self._headers(),
            data={
                "email": email,
                "name": name or "",
            },
        )
        return CustomerResult(
            gateway=self.gateway_name,
            customer_id=str(response["id"]),
            email=str(response.get("email") or email),
            name=response.get("name") or name,
            raw=response,
        )

    def create_subscription(self, price_id: str, email: str, trial_period_days: int | None = None, **kwargs):
        customer_id = kwargs.get("customer_id")
        if not customer_id:
            customer_id = self.create_customer(email=email, name=kwargs.get("name")).customer_id
        payment_method_id = kwargs.get("payment_method_id")
        if payment_method_id:
            self._request(
                "POST",
                f"{self.base_url}/payment_methods/{payment_method_id}/attach",
                headers=self._headers(),
                data={"customer": customer_id},
            )
            self._request(
                "POST",
                f"{self.base_url}/customers/{customer_id}",
                headers=self._headers(),
                data={"invoice_settings[default_payment_method]": payment_method_id},
            )
        response = self._request(
            "POST",
            f"{self.base_url}/subscriptions",
            headers=self._headers(),
            data={
                "customer": customer_id,
                "items[0][price]": price_id,
                "trial_period_days": trial_period_days or "",
            },
        )
        return self._build_subscription_result(response, email=email)

    async def acreate_subscription(self, price_id: str, email: str, trial_period_days: int | None = None, **kwargs):
        customer_id = kwargs.get("customer_id")
        if not customer_id:
            customer_id = (await self.acreate_customer(email=email, name=kwargs.get("name"))).customer_id
        payment_method_id = kwargs.get("payment_method_id")
        if payment_method_id:
            await self._arequest(
                "POST",
                f"{self.base_url}/payment_methods/{payment_method_id}/attach",
                headers=self._headers(),
                data={"customer": customer_id},
            )
            await self._arequest(
                "POST",
                f"{self.base_url}/customers/{customer_id}",
                headers=self._headers(),
                data={"invoice_settings[default_payment_method]": payment_method_id},
            )
        response = await self._arequest(
            "POST",
            f"{self.base_url}/subscriptions",
            headers=self._headers(),
            data={
                "customer": customer_id,
                "items[0][price]": price_id,
                "trial_period_days": str(trial_period_days or ""),
            },
        )
        return self._build_subscription_result(response, email=email)

    def parse_webhook(self, request: HttpRequest) -> WebhookEvent:
        signature = request.headers.get("stripe-signature")
        stripe.api_key = self.config["stripe_secret_key"]
        event = stripe.Webhook.construct_event(
            payload=request.body,
            sig_header=signature,
            secret=self.config["stripe_webhook_secret"],
        )
        payload = dict(event)
        data = payload["data"]["object"]
        event_name = str(payload["type"])
        return self._build_stripe_webhook_event(data=data, event_name=event_name, payload=payload)

    def refresh_subscription(self, subscription: PayBridgeSubscription):
        response = self._request(
            "GET",
            f"{self.base_url}/subscriptions/{subscription.gateway_subscription_id}",
            headers=self._headers(),
        )
        updated = self._update_subscription_model(response, subscription.customer_email)
        return updated

    def fetch_recent_transactions(self, from_dt, to_dt):
        response = self._request(
            "GET",
            f"{self.base_url}/payment_intents",
            headers=self._headers(),
            params={
                "created[gte]": int(from_dt.timestamp()),
                "created[lte]": int(to_dt.timestamp()),
                "limit": 100,
            },
        )
        return [self._build_transaction_result(item) for item in response.get("data", [])]

    def _build_stripe_webhook_event(self, *, data: dict[str, Any], event_name: str, payload: dict[str, Any]):
        event_type = WEBHOOK_EVENT_SUBSCRIPTION_UPDATED
        if event_name == "payment_intent.succeeded":
            event_type = WEBHOOK_EVENT_PAYMENT_SUCCESS
        elif event_name == "payment_intent.payment_failed":
            event_type = WEBHOOK_EVENT_PAYMENT_FAILED
        elif event_name == "customer.subscription.created":
            event_type = WEBHOOK_EVENT_SUBSCRIPTION_CREATED
        elif event_name == "customer.subscription.deleted":
            event_type = WEBHOOK_EVENT_SUBSCRIPTION_CANCELLED

        metadata = {
            "status": data.get("status"),
            "plan_id": (((data.get("items") or {}).get("data") or [{}])[0].get("price", {}) if isinstance(data.get("items"), dict) else {}),
        }
        price = (((data.get("items") or {}).get("data") or [{}])[0].get("price", {}) if isinstance(data.get("items"), dict) else {})
        metadata["plan_id"] = price.get("id") if isinstance(price, dict) else ""
        metadata["trial_end"] = _timestamp_to_iso(data.get("trial_end"))
        metadata["current_period_end"] = _timestamp_to_iso(data.get("current_period_end"))
        metadata["cancel_at"] = _timestamp_to_iso(data.get("cancel_at"))

        event = WebhookEvent(
            gateway=self.gateway_name,
            event_type=event_type,
            event_name=event_name,
            reference=str(data.get("id")) if event_name.startswith("payment_intent.") else None,
            status=_map_stripe_payment_status(data.get("status")),
            amount=self._coerce_amount((data.get("amount") or 0) / 100) if data.get("amount") is not None else None,
            currency=str(data.get("currency", "")).upper() or None,
            email=str(data.get("receipt_email") or data.get("customer_email") or ""),
            customer_id=str(data.get("customer")) if data.get("customer") else None,
            subscription_id=str(data.get("id")) if event_name.startswith("customer.subscription") else None,
            occurred_at=self._parse_datetime(_timestamp_to_iso(payload.get("created"))),
            metadata=metadata,
            payload=payload,
        )
        return event

    def _build_transaction_result(self, data: dict[str, Any]) -> TransactionResult:
        return TransactionResult(
            gateway=self.gateway_name,
            reference=str(data["id"]),
            status=_map_stripe_payment_status(data.get("status")),
            amount=self._coerce_amount((data.get("amount") or 0) / 100) if data.get("amount") is not None else None,
            currency=str(data.get("currency", "")).upper() or None,
            email=str(data.get("receipt_email") or ""),
            customer_id=str(data.get("customer")) if data.get("customer") else None,
            paid_at=self._parse_datetime(_timestamp_to_iso(data.get("created"))),
            raw=data,
        )

    def _build_subscription_result(self, data: dict[str, Any], *, email: str) -> SubscriptionResult:
        result = SubscriptionResult(
            gateway=self.gateway_name,
            status=_map_stripe_subscription_status(data.get("status")),
            subscription_id=str(data["id"]),
            customer_email=email,
            next_billing_date=self._parse_datetime(_timestamp_to_iso(data.get("current_period_end"))),
            trial_end=self._parse_datetime(_timestamp_to_iso(data.get("trial_end"))),
            raw=data,
        )
        self._update_subscription_model(data, email)
        return result

    def _update_subscription_model(self, data: dict[str, Any], email: str):
        price = (((data.get("items") or {}).get("data") or [{}])[0].get("price", {}) if isinstance(data.get("items"), dict) else {})
        subscription, _ = PayBridgeSubscription.objects.update_or_create(
            gateway_subscription_id=str(data["id"]),
            defaults={
                "customer_email": email,
                "gateway": self.gateway_name,
                "plan_id": price.get("id") if isinstance(price, dict) else "",
                "status": _map_stripe_subscription_status(data.get("status")),
                "trial_end": self._parse_datetime(_timestamp_to_iso(data.get("trial_end"))),
                "current_period_end": self._parse_datetime(_timestamp_to_iso(data.get("current_period_end"))),
                "cancel_at": self._parse_datetime(_timestamp_to_iso(data.get("cancel_at"))),
                "metadata": data,
            },
        )
        return subscription

    def _headers(self):
        return {
            "Authorization": f"Bearer {self.config['stripe_secret_key']}",
        }


def _map_stripe_payment_status(value):
    raw = str(value or "").lower()
    if raw == "succeeded":
        return "SUCCESS"
    if raw in {"canceled"}:
        return "FAILED"
    if raw in {"requires_payment_method", "requires_action", "processing", "requires_confirmation", "requires_capture"}:
        return "PENDING"
    if raw in {"refunded"}:
        return "REFUNDED"
    return "FAILED"


def _map_stripe_subscription_status(value):
    raw = str(value or "").lower()
    mapping = {
        "active": SUBSCRIPTION_STATUS_ACTIVE,
        "trialing": SUBSCRIPTION_STATUS_TRIALING,
        "past_due": SUBSCRIPTION_STATUS_PAST_DUE,
        "canceled": SUBSCRIPTION_STATUS_CANCELLED,
        "incomplete": SUBSCRIPTION_STATUS_INCOMPLETE,
    }
    return mapping.get(raw, SUBSCRIPTION_STATUS_PENDING)


def _timestamp_to_iso(value):
    if not value:
        return None
    return datetime.fromtimestamp(int(value), tz=UTC).isoformat()
