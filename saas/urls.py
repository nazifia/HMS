from django.urls import path

from . import views

app_name = "saas"

urlpatterns = [
    path("signup/", views.signup, name="signup"),
    path("billing/", views.billing, name="billing"),
    path("checkout/", views.checkout, name="checkout"),
    path("request-activation/", views.request_activation, name="request_activation"),
    path("webhook/paystack/", views.paystack_webhook, name="paystack_webhook"),
]
