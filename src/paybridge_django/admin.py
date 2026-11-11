import json

from django.contrib import admin, messages

from .models import PayBridgeSubscription, PayBridgeTransaction
from .services.processing import replay_transaction_event


@admin.action(description="Retry webhook signal dispatch")
def retry_webhook(modeladmin, request, queryset):
    count = 0
    for transaction in queryset:
        replay_transaction_event(transaction)
        count += 1
    messages.success(request, f"Replayed {count} stored webhook event(s).")


@admin.register(PayBridgeTransaction)
class PayBridgeTransactionAdmin(admin.ModelAdmin):
    actions = [retry_webhook]
    list_display = ("reference", "gateway", "amount", "currency", "status", "email", "created_at")
    list_filter = ("gateway", "status", "currency")
    readonly_fields = ("created_at", "updated_at", "webhook_received_at", "formatted_webhook_payload")
    search_fields = ("reference", "email")

    @admin.display(description="Webhook payload")
    def formatted_webhook_payload(self, obj):
        if not obj.webhook_payload:
            return "No webhook payload stored."
        return json.dumps(obj.webhook_payload, indent=2, sort_keys=True)


@admin.register(PayBridgeSubscription)
class PayBridgeSubscriptionAdmin(admin.ModelAdmin):
    list_display = (
        "gateway_subscription_id",
        "gateway",
        "customer_email",
        "plan_id",
        "status",
        "current_period_end",
    )
    list_filter = ("gateway", "status")
    readonly_fields = ("created_at", "updated_at")
    search_fields = ("gateway_subscription_id", "customer_email")
