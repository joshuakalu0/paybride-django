from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", include("demo_checkout.urls")),
    path("payments/", include("paybridge_django.urls")),
]
