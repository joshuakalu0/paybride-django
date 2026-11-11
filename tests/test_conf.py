import pytest
from django.core.exceptions import ImproperlyConfigured
from django.test import override_settings

from paybridge_django.conf import get_paybridge_settings
from paybridge_django.services import PaystackService, get_gateway


def test_get_gateway_uses_default_gateway():
    service = get_gateway()
    assert isinstance(service, PaystackService)


@override_settings(PAYBRIDGE={"DEFAULT_GATEWAY": "stripe", "STRIPE_SECRET_KEY": ""})
def test_conf_raises_for_missing_default_gateway_keys():
    with pytest.raises(ImproperlyConfigured):
        get_paybridge_settings()
