"""Stub de Identidad: usuarios en memoria y emisión de JWT (contrato: docs/api/identidad.json)."""
import os
import uuid
from datetime import datetime, timedelta, timezone

import jwt
from django.contrib.auth.hashers import check_password, make_password
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

from .common import body, error, page, roles, user

JWT_SECRET = os.getenv("JWT_SECRET", "dev-jwt-secret-cambiar")
JWT_TTL = 3600
ROLES = {
    "ADMIN": "Administrador del sistema", "GERENTE": "Gerente general",
    "JEFE_COMPRAS": "Jefe de compras", "AUX_COMPRAS": "Auxiliar de compras",
    "JEFE_BODEGA": "Jefe de bodega central", "BODEGUERO": "Bodeguero",
    "VENDEDOR": "Vendedor de punto", "AUDITOR": "Auditor / contador",
}
DEMO_PASSWORD = "Clave*2026"


def _seed():
    base = [
        ("admin", "Administrador", "ADMIN", []),
        ("gerente", "Gerente General", "GERENTE", []),
        ("jefe.compras", "Jefe de Compras", "JEFE_COMPRAS", []),
        ("jefe.bodega", "Jefe Bodega Central", "JEFE_BODEGA", ["CHI"]),
        ("bodeguero.anserma", "Carlos Gómez", "BODEGUERO", ["ANS"]),
        ("vendedor.manizales", "Laura Ríos", "VENDEDOR", ["MZL"]),
    ]
    now = datetime.now(timezone.utc).isoformat()
    return {
        i: {"id": i, "username": u, "fullName": n, "email": f"{u}@agroinsumos.co", "role": r,
            "warehouseIds": w, "active": True, "createdAt": now, "_pwd": make_password(DEMO_PASSWORD)}
        for i, (u, n, r, w) in enumerate(base, start=1)
    }


USERS = None


def _users():
    global USERS
    if USERS is None:
        USERS = _seed()
    return USERS


def _public(u):
    return {k: v for k, v in u.items() if not k.startswith("_")}


@csrf_exempt
@require_http_methods(["POST"])
def login(request):
    data = body(request)
    if not data or not data.get("username") or not data.get("password"):
        return error(request, 400, "VALIDATION_ERROR", "username y password son obligatorios")
    found = next((u for u in _users().values() if u["username"] == data["username"] and u["active"]), None)
    if not found or not check_password(data["password"], found["_pwd"]):
        return error(request, 401, "INVALID_CREDENTIALS", "Usuario o contraseña incorrectos")
    claims = {
        "sub": str(found["id"]), "role": found["role"], "warehouses": found["warehouseIds"],
        "jti": str(uuid.uuid4()), "exp": datetime.now(timezone.utc) + timedelta(seconds=JWT_TTL),
    }
    token = jwt.encode(claims, JWT_SECRET, algorithm="HS256")
    return JsonResponse({"accessToken": token, "tokenType": "Bearer", "expiresIn": JWT_TTL, "user": _public(found)})


@csrf_exempt
@require_http_methods(["POST"])
@roles()
def logout(request):
    return JsonResponse({}, status=204)


@require_http_methods(["GET"])
@roles()
def me(request):
    u = _users().get(user(request)["id"])
    if not u:
        return error(request, 404, "NOT_FOUND", "Usuario no encontrado")
    return JsonResponse(_public(u))


@csrf_exempt
@require_http_methods(["GET", "POST"])
@roles("ADMIN")
def users(request):
    if request.method == "GET":
        items = [_public(u) for u in _users().values()
                 if request.GET.get("role") in (None, u["role"])]
        return JsonResponse(page(request, items))
    data = body(request)
    required = ["username", "fullName", "email", "role", "password"]
    missing = [f for f in required if not (data or {}).get(f)]
    if missing:
        return error(request, 400, "VALIDATION_ERROR", "Campos obligatorios faltantes", {"missing": missing})
    if data["role"] not in ROLES:
        return error(request, 400, "VALIDATION_ERROR", "Rol inválido", {"allowed": list(ROLES)})
    if len(data["password"]) < 8:
        return error(request, 400, "VALIDATION_ERROR", "La contraseña debe tener al menos 8 caracteres")
    if any(u["username"] == data["username"] for u in _users().values()):
        return error(request, 409, "CONFLICT", "El username ya existe")
    new_id = max(_users()) + 1
    _users()[new_id] = {
        "id": new_id, "username": data["username"], "fullName": data["fullName"], "email": data["email"],
        "role": data["role"], "warehouseIds": data.get("warehouseIds", []), "active": True,
        "createdAt": datetime.now(timezone.utc).isoformat(), "_pwd": make_password(data["password"]),
    }
    return JsonResponse(_public(_users()[new_id]), status=201)


@require_http_methods(["GET"])
@roles("ADMIN")
def user_detail(request, user_id):
    u = _users().get(user_id)
    if not u:
        return error(request, 404, "NOT_FOUND", "Usuario no encontrado")
    return JsonResponse(_public(u))


@require_http_methods(["GET"])
@roles("ADMIN")
def role_list(request):
    return JsonResponse([{"code": c, "name": n, "permissions": []} for c, n in ROLES.items()], safe=False)
