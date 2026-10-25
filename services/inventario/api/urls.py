from django.urls import path

from . import views
from .common import health

urlpatterns = [
    path("warehouses", views.warehouses),
    path("stock", views.stock),
    path("fefo-suggestion", views.fefo_suggestion),
    path("movements", views.movements),
    path("transfers", views.transfers),
    path("transfers/<int:transfer_id>", views.transfer_detail),
    path("transfers/<int:transfer_id>/approve", views.transfer_approve),
    path("transfers/<int:transfer_id>/dispatch", views.transfer_dispatch),
    path("transfers/<int:transfer_id>/receive", views.transfer_receive),
    path("internal/entries", views.internal_entries),
    path("health", health),
]
