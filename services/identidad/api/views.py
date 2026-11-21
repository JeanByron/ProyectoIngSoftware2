import os
import uuid
from datetime import datetime, timedelta, timezone

import jwt
from django.contrib.auth.hashers import check_password, make_password
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

from .common import body, error, page, roles, user
from .models import Usuario

JWT_SECRET = os.getenv("JWT_SECRET", "dev-jwt-secret-cambiar")
JWT_TTL = 3600
ROLES = {
    "ADMIN": "Administrador del sistema", "GERENTE": "Gerente general",
    "JEFE_COMPRAS": "Jefe de compras", "AUX_COMPRAS": "Auxiliar de compras",
    "JEFE_BODEGA": "Jefe de bodega central", "BODEGUERO": "Bodeguero",
    "VENDEDOR": "Vendedor de punto", "AUDITOR": "Auditor / contador",
}


@csrf_exempt
@require_http_methods(["POST"])
def login(request):
    data = body(request)
    if not data or not data.get("username") or not data.get("password"):
        return error(request, 400, "VALIDATION_ERROR", "username y password son obligatorios")
    found = Usuario.objects.filter(username=data["username"], active=True).first()
    if not found or not check_password(data["password"], found.password):
        return error(request, 401, "INVALID_CREDENTIALS", "Usuario o contraseña incorrectos")
    claims = {
        "sub": str(found.id), "role": found.role, "warehouses": found.warehouse_ids,
        "jti": str(uuid.uuid4()), "exp": datetime.now(timezone.utc) + timedelta(seconds=JWT_TTL),
    }
    token = jwt.encode(claims, JWT_SECRET, algorithm="HS256")
    return JsonResponse({"accessToken": token, "tokenType": "Bearer", "expiresIn": JWT_TTL, "user": found.to_dict()})


@csrf_exempt
@require_http_methods(["POST"])
@roles()
def logout(request):
    return JsonResponse({}, status=204)


@require_http_methods(["GET"])
@roles()
def me(request):
    u = Usuario.objects.filter(id=user(request)["id"]).first()
    if not u:
        return error(request, 404, "NOT_FOUND", "Usuario no encontrado")
    return JsonResponse(u.to_dict())


@csrf_exempt
@require_http_methods(["GET", "POST"])
@roles("ADMIN")
def users(request):
    if request.method == "GET":
        qs = Usuario.objects.all()
        if request.GET.get("role"):
            qs = qs.filter(role=request.GET["role"])
        items = [u.to_dict() for u in qs]
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
    if Usuario.objects.filter(username=data["username"]).exists():
        return error(request, 409, "CONFLICT", "El username ya existe")
    u = Usuario.objects.create(
        username=data["username"], full_name=data["fullName"], email=data["email"], role=data["role"],
        warehouse_ids=data.get("warehouseIds", []), password=make_password(data["password"]),
    )
    return JsonResponse(u.to_dict(), status=201)


@require_http_methods(["GET"])
@roles("ADMIN")
def user_detail(request, user_id):
    u = Usuario.objects.filter(id=user_id).first()
    if not u:
        return error(request, 404, "NOT_FOUND", "Usuario no encontrado")
    return JsonResponse(u.to_dict())


@require_http_methods(["GET"])
@roles("ADMIN")
def role_list(request):
    return JsonResponse([{"code": c, "name": n, "permissions": []} for c, n in ROLES.items()], safe=False)
