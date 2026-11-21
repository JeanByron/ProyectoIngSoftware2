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
SERVICE_NAME = "reportes"
MONGO_URI = os.getenv("MONGO_URI", "mongodb://127.0.0.1:27017")
MONGO_DB = os.getenv("MONGO_DB", "reportes")
