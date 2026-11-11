from .constants import SUBSCRIPTION_STATUS_ACTIVE, SUBSCRIPTION_STATUS_TRIALING
from .models import PayBridgeSubscription


def has_active_subscription(email: str) -> bool:
    return PayBridgeSubscription.objects.filter(
        customer_email__iexact=email,
        status__in=[SUBSCRIPTION_STATUS_ACTIVE, SUBSCRIPTION_STATUS_TRIALING],
    ).exists()
