"""Configuración mínima del stub de identidad: sin BD (datos en memoria), solo API JSON."""
import os

SECRET_KEY = os.getenv("SECRET_KEY", "dev-only-insecure-key")
DEBUG = os.getenv("DEBUG", "1") == "1"
ALLOWED_HOSTS = ["*"]
INSTALLED_APPS = ["django.contrib.contenttypes", "django.contrib.auth", "api"]
MIDDLEWARE = ["api.common.CorrelationIdMiddleware"]
ROOT_URLCONF = "config.urls"
DATABASES = {}
USE_TZ = True
APPEND_SLASH = False
SERVICE_NAME = "identidad"
