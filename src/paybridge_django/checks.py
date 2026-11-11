from django.core.checks import Warning, register

from .conf import get_paybridge_settings


@register()
def paybridge_system_checks(app_configs, **kwargs):
    warnings = []
    config = get_paybridge_settings()

    if config.process_webhooks_async:
        try:
            import celery  # noqa: F401
        except ImportError:
            warnings.append(
                Warning(
                    "PAYBRIDGE['PROCESS_WEBHOOKS_ASYNC'] is enabled but Celery is not installed.",
                    hint="Install the optional celery extra or disable async webhook processing.",
                    id="paybridge_django.W001",
                )
            )

    return warnings
