"""Configuración mínima del stub de catalogo: sin BD (datos en memoria), solo API JSON."""
import os

SECRET_KEY = os.getenv("SECRET_KEY", "dev-only-insecure-key")
DEBUG = os.getenv("DEBUG", "1") == "1"
ALLOWED_HOSTS = ["*"]
INSTALLED_APPS = ["api"]
MIDDLEWARE = ["api.common.CorrelationIdMiddleware"]
ROOT_URLCONF = "config.urls"
DATABASES = {}
USE_TZ = True
APPEND_SLASH = False
SERVICE_NAME = "catalogo"
