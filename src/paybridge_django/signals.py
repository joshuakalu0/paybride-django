from django.dispatch import Signal


paybridge_payment_success = Signal()
paybridge_payment_failed = Signal()
paybridge_subscription_updated = Signal()
