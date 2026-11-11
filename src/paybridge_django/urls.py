from django.urls import path

from .views import FlutterwaveWebhookView, PaystackWebhookView, StripeWebhookView

app_name = "paybridge_django"

urlpatterns = [
    path("paystack/webhook/", PaystackWebhookView.as_view(), name="paybridge-paystack-webhook"),
    path(
        "flutterwave/webhook/",
        FlutterwaveWebhookView.as_view(),
        name="paybridge-flutterwave-webhook",
    ),
    path("stripe/webhook/", StripeWebhookView.as_view(), name="paybridge-stripe-webhook"),
]
