from django.apps import AppConfig


class PayBridgeDjangoConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "paybridge_django"
    verbose_name = "PayBridge Django"

    def ready(self) -> None:
        from . import checks  # noqa: F401
        from .conf import get_paybridge_settings
        from . import signals  # noqa: F401

        get_paybridge_settings()
