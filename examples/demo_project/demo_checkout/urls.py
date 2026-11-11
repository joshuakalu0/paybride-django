from django.urls import path

from .views import demo_initialize_payment, home

urlpatterns = [
    path("", home, name="home"),
    path("demo-init/", demo_initialize_payment, name="demo-init"),
]
