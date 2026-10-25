from django.urls import path

from . import views
from .common import health

urlpatterns = [
    path("auth/login", views.login),
    path("auth/logout", views.logout),
    path("auth/me", views.me),
    path("users", views.users),
    path("users/<int:user_id>", views.user_detail),
    path("roles", views.role_list),
    path("health", health),
]
