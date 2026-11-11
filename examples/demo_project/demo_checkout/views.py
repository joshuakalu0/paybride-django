from decimal import Decimal

from django.http import JsonResponse
from django.shortcuts import render
from django.views.decorators.http import require_POST

from paybridge_django import get_gateway


def home(request):
    return render(request, "demo_checkout/home.html")


@require_POST
def demo_initialize_payment(request):
    gateway = get_gateway()
    payment = gateway.initialize_transaction(
        amount=Decimal("150.00"),
        email=request.POST.get("email", "demo@example.com"),
        currency="NGN",
        callback_url="https://example.com/payments/return/",
        reference="demo_order_001",
    )
    return JsonResponse(payment.to_dict())
