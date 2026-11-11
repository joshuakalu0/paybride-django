from __future__ import annotations

from django.http import HttpRequest, HttpResponse, HttpResponseBadRequest
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.csrf import csrf_exempt

from .conf import get_paybridge_settings
from .exceptions import PayBridgeError
from .services import get_gateway
from .services.processing import process_webhook_event
from .tasks import process_webhook_async


@method_decorator(csrf_exempt, name="dispatch")
class BaseWebhookView(View):
    gateway_name: str

    def post(self, request: HttpRequest, *args, **kwargs) -> HttpResponse:
        service = get_gateway(self.gateway_name)
        try:
            event = service.parse_webhook(request)
        except PayBridgeError as error:
            return HttpResponseBadRequest(str(error))

        self._process_event(event)

        return HttpResponse(status=200)

    def _process_event(self, event) -> None:
        if get_paybridge_settings().process_webhooks_async and getattr(process_webhook_async, "delay", None):
            try:
                process_webhook_async.delay(event.to_dict())
                return
            except Exception:
                # Fall back to synchronous processing if Celery is installed but not runnable.
                pass

        process_webhook_event(event)


class PaystackWebhookView(BaseWebhookView):
    gateway_name = "paystack"


class FlutterwaveWebhookView(BaseWebhookView):
    gateway_name = "flutterwave"


class StripeWebhookView(BaseWebhookView):
    gateway_name = "stripe"
