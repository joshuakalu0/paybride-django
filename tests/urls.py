from django.urls import include, path

urlpatterns = [
    path("payments/", include("paybridge_django.urls")),
]
