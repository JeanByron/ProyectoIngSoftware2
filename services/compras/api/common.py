"""Utilidades compartidas: formato de error estándar, cabeceras del Gateway, roles, idempotencia."""
import json
import uuid
from functools import wraps

from django.conf import settings
from django.http import JsonResponse

_idempotency_cache = {}


class CorrelationIdMiddleware:
    """Propaga X-Correlation-Id (lo genera si el Gateway no lo envió)."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        request.correlation_id = request.headers.get("X-Correlation-Id") or str(uuid.uuid4())
        response = self.get_response(request)
        response["X-Correlation-Id"] = request.correlation_id
        return response


def error(request, status, code, message, details=None):
    return JsonResponse(
        {"code": code, "message": message, "details": details or {},
         "correlationId": getattr(request, "correlation_id", None)},
        status=status,
    )


def body(request):
    try:
        return json.loads(request.body or b"{}")
    except json.JSONDecodeError:
        return None


def user(request):
    """Datos que el Gateway reenvía tras validar el JWT."""
    warehouses = request.headers.get("X-User-Warehouses", "")
    return {
        "id": int(request.headers.get("X-User-Id", 0) or 0),
        "role": request.headers.get("X-User-Role", ""),
        "warehouses": [w for w in warehouses.split(",") if w],
    }


def roles(*allowed):
    def decorator(view):
        @wraps(view)
        def wrapper(request, *args, **kwargs):
            u = user(request)
            if not u["role"]:
                return error(request, 401, "UNAUTHORIZED", "Faltan cabeceras de usuario del Gateway")
            if allowed and u["role"] not in allowed:
                return error(request, 403, "FORBIDDEN", f"Rol {u['role']} sin permiso")
            return view(request, *args, **kwargs)
        return wrapper
    return decorator


def idempotent(view):
    """Misma Idempotency-Key + misma ruta = misma respuesta, sin repetir el efecto."""
    @wraps(view)
    def wrapper(request, *args, **kwargs):
        key = request.headers.get("Idempotency-Key")
        if not key:
            return view(request, *args, **kwargs)
        cache_key = (request.path, key)
        if cache_key in _idempotency_cache:
            status, content = _idempotency_cache[cache_key]
            return JsonResponse(json.loads(content), status=status, safe=False)
        response = view(request, *args, **kwargs)
        if response.status_code < 500:
            _idempotency_cache[cache_key] = (response.status_code, response.content)
        return response
    return wrapper


def health(request):
    return JsonResponse({"status": "UP", "service": settings.SERVICE_NAME, "db": "UP"})


def page(request, items):
    p = max(int(request.GET.get("page", 1)), 1)
    s = min(max(int(request.GET.get("size", 20)), 1), 100)
    return {"page": p, "size": s, "total": len(items), "items": items[(p - 1) * s: p * s]}
