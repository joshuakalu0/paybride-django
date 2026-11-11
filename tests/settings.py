SECRET_KEY = "test-secret"
DEBUG = True
USE_TZ = True
TIME_ZONE = "UTC"
ROOT_URLCONF = "tests.urls"
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "paybridge_django",
]

MIDDLEWARE = [
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
]

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": ":memory:",
    }
}

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ]
        },
    }
]

DEFAULT_FROM_EMAIL = "test-payments@example.com"
EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"

PAYBRIDGE = {
    "DEFAULT_GATEWAY": "paystack",
    "PAYSTACK_SECRET_KEY": "sk_test_paystack",
    "PAYSTACK_WEBHOOK_SECRET": "sk_test_paystack",
    "FLUTTERWAVE_PUBLIC_KEY": "FLWPUBK_TEST",
    "FLUTTERWAVE_SECRET_KEY": "FLWSECK_TEST",
    "FLUTTERWAVE_WEBHOOK_SECRET": "flw_secret_hash",
    "STRIPE_SECRET_KEY": "sk_test_stripe",
    "STRIPE_WEBHOOK_SECRET": "whsec_test",
}
