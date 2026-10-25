#!/usr/bin/env python
"""Servicio compras (stub de desarrollo). Ejecutar: python manage.py runserver 8004"""
import os
import sys

if __name__ == "__main__":
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
    from django.core.management import execute_from_command_line

    execute_from_command_line(sys.argv)
