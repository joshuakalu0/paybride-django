# paybridge-django

Reusable Django payment infrastructure for Paystack, Flutterwave, and Stripe.

`paybridge-django` is the Django-native counterpart to the Node PayBridge package. Instead of wiring three different gateways, webhook formats, and transaction models yourself, you install one app, add it to `INSTALLED_APPS`, include the URLs, and get a payment foundation with models, admin, signals, and operational commands.

## What it gives you

- Normalized gateway services for Paystack, Flutterwave, and Stripe
- Sync APIs with true async counterparts for the networked service methods
- Built-in webhook views with signature validation
- Transaction and subscription models with Django admin support
- Signals for payment success, payment failure, and subscription updates
- Management commands for reconciliation and subscription health checks
- Optional Celery tasks for async webhook processing and receipt emails

## Install

```bash
pip install paybridge-django
```

Optional Celery support:

```bash
pip install "paybridge-django[celery]"
```

## Quick start

1. Add the app:

```python
INSTALLED_APPS = [
    # ...
    "paybridge_django",
]
```

2. Configure `PAYBRIDGE`:

```python
PAYBRIDGE = {
    "DEFAULT_GATEWAY": "paystack",
    "PAYSTACK_SECRET_KEY": "...",
    "PAYSTACK_WEBHOOK_SECRET": "...",
    "FLUTTERWAVE_PUBLIC_KEY": "...",
    "FLUTTERWAVE_SECRET_KEY": "...",
    "FLUTTERWAVE_WEBHOOK_SECRET": "...",
    "STRIPE_SECRET_KEY": "...",
    "STRIPE_WEBHOOK_SECRET": "...",
    "PROCESS_WEBHOOKS_ASYNC": False,
}
```

3. Include the URLs:

```python
from django.urls import include, path

urlpatterns = [
    path("payments/", include("paybridge_django.urls")),
]
```

4. Run migrations:

```bash
python manage.py migrate
```

## Initialize a payment in a view

```python
from decimal import Decimal

from django.http import JsonResponse

from paybridge_django import get_gateway


def start_checkout(request):
    gateway = get_gateway()
    payment = gateway.initialize_transaction(
        amount=Decimal("150.00"),
        email="buyer@example.com",
        currency="NGN",
        callback_url="https://example.com/payments/return/",
        reference="order_123",
    )
    return JsonResponse(payment.to_dict())
```

## Public service surface

- `get_gateway(name: str | None = None)`
- `has_active_subscription(email: str)`

Each concrete gateway service exposes:

- `initialize_transaction(...)`
- `verify_transaction(reference)`
- `create_customer(email, name=None, **kwargs)`
- `create_subscription(...)`
- `parse_webhook(request)`
- `ainitialize_transaction(...)`
- `averify_transaction(reference)`
- `acreate_customer(...)`
- `acreate_subscription(...)`
- `aparse_webhook(request)`

## Webhook endpoints

Include `paybridge_django.urls` and configure your provider dashboards to point to:

- `/payments/paystack/webhook/`
- `/payments/flutterwave/webhook/`
- `/payments/stripe/webhook/`

The built-in webhook views:

- read the raw request body
- validate the signature
- normalize the event
- persist transaction or subscription changes
- fire Django signals
- return HTTP `200`

## Signals

Signals are emitted after normalized webhook processing:

- `paybridge_payment_success`
- `paybridge_payment_failed`
- `paybridge_subscription_updated`

Example:

```python
from django.dispatch import receiver

from paybridge_django.signals import paybridge_payment_success


@receiver(paybridge_payment_success)
def handle_payment_success(sender, event, transaction, **kwargs):
    print(transaction.reference if transaction else event.reference)
```

## Models

### `PayBridgeTransaction`

- `reference`
- `gateway`
- `amount`
- `currency`
- `status`
- `email`
- `metadata`
- `webhook_payload`
- `webhook_received_at`
- timestamps

Convenience queryset helpers:

- `successful()`
- `failed()`
- `by_gateway(gateway)`
- `by_email(email)`

### `PayBridgeSubscription`

- `customer_email`
- `gateway`
- `gateway_subscription_id`
- `plan_id`
- `status`
- `trial_end`
- `current_period_end`
- `cancel_at`
- `metadata`

## Django admin

The package registers both models in Django admin with:

- gateway/status/currency filters
- reference and email search
- readonly webhook payload visibility
- a `retry_webhook` admin action that replays the stored normalized signal flow

## Management commands

Reconcile gateway transactions:

```bash
python manage.py paybridge_sync_transactions --gateway paystack --days 7
```

Check stored subscriptions:

```bash
python manage.py paybridge_check_subscriptions
```

## Async support

The package exposes explicit async service methods backed by `httpx`.

```python
gateway = get_gateway("stripe")
result = await gateway.ainitialize_transaction(
    amount="49.99",
    email="buyer@example.com",
    currency="USD",
    callback_url="https://example.com/return/",
)
```

Built-in webhook views remain synchronous drop-ins for host apps. If you enable:

```python
PAYBRIDGE = {
    # ...
    "PROCESS_WEBHOOKS_ASYNC": True,
}
```

validated webhook events will be queued through `process_webhook_async`. Installing the optional Celery extra is recommended for production async processing.

## Optional tasks

- `process_webhook_async`
- `send_payment_receipt_email`

## Example project

A working demo host project lives under [examples/demo_project](./examples/demo_project). It shows:

- `INSTALLED_APPS` wiring
- `PAYBRIDGE` settings
- URL inclusion
- a simple initialization view
- signal receivers

## Development

From `python/paybridge-django`:

```bash
uv sync --all-groups
uv run ruff check .
uv run pytest
uv run python -m build
```

Example project check:

```bash
uv run python examples/demo_project/manage.py check
```

## Release flow

- Pull requests run Ruff, pytest, and package build checks
- Version tags build the package and publish to PyPI
- `CHANGELOG.md` tracks releases from the first version onward

## Environment variables

See [.env.example](./.env.example) for the full list.
