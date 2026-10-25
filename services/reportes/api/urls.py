from django.urls import path

from . import views
from .common import health

urlpatterns = [
    path("dashboard", views.dashboard),
    path("reports/stock", views.stock_report),
    path("sync/status", views.sync_status),
    path("sync/run", views.sync_run),
    path("health", health),
]
