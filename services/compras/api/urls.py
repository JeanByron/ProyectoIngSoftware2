from django.urls import path

from . import views
from .common import health

urlpatterns = [
    path("suppliers", views.suppliers),
    path("purchase-orders", views.purchase_orders),
    path("purchase-orders/<int:order_id>", views.order_detail),
    path("purchase-orders/<int:order_id>/approve", views.order_approve),
    path("purchase-orders/<int:order_id>/send", views.order_send),
    path("purchase-orders/<int:order_id>/receipts", views.order_receipts),
    path("health", health),
]
