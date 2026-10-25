from django.urls import path

from . import views
from .common import health

urlpatterns = [
    path("products", views.products),
    path("products/<str:product_id>", views.product_detail),
    path("categories", views.categories),
    path("health", health),
]
