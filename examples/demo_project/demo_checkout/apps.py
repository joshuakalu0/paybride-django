from django.apps import AppConfig


class DemoCheckoutConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "demo_checkout"

    def ready(self) -> None:
        from . import receivers  # noqa: F401
