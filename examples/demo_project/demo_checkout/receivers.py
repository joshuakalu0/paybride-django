from django.dispatch import receiver

from paybridge_django.signals import paybridge_payment_failed, paybridge_payment_success


@receiver(paybridge_payment_success)
def log_payment_success(sender, event, transaction, **kwargs):
    print(f"Payment succeeded for {transaction.reference if transaction else event.reference}")


@receiver(paybridge_payment_failed)
def log_payment_failed(sender, event, transaction, **kwargs):
    print(f"Payment failed for {transaction.reference if transaction else event.reference}")
