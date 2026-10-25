import os
import sys

from django.apps import AppConfig


class ApiConfig(AppConfig):
    name = "api"

    def ready(self):
        # Solo en el proceso que atiende peticiones (no en el vigilante del autoreload ni en otros comandos).
        if "runserver" in sys.argv and (os.environ.get("RUN_MAIN") == "true" or "--noreload" in sys.argv):
            from .views import start_scheduler

            start_scheduler()
