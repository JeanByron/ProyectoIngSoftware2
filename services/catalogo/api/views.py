import re
from datetime import datetime, timezone

from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

from .common import body, error, page, roles
from .db import collection

EDITORS = ("ADMIN", "JEFE_COMPRAS")
TYPES = {"FERTILIZANTE", "AGROQUIMICO", "SEMILLA", "HERRAMIENTA", "REPUESTO"}
UNITS = {"BULTO", "LITRO", "KILO", "UNIDAD"}
NO_ID = {"_id": 0}


def _now():
    return datetime.now(timezone.utc).isoformat()


def _descendants(category_id):
    ids = {category_id}
    for c in collection("categories").find({"parentId": category_id}, NO_ID):
        ids |= _descendants(c["id"])
    return ids


@csrf_exempt
@require_http_methods(["GET", "POST"])
@roles()
def products(request):
    if request.method == "POST":
        return _create_product(request)
    f = request.GET
    query = {"active": f.get("active", "true").lower() == "true"}
    if f.get("q"):
        pattern = re.compile(re.escape(f["q"]), re.IGNORECASE)
        query["$or"] = [{"name": pattern}, {"description": pattern}]
    if f.get("code") is not None:
        query["code"] = f["code"]
    if f.get("categoryId"):
        query["categoryId"] = {"$in": list(_descendants(f["categoryId"]))}
    if f.get("supplierId", "").isdigit():
        query["usualSupplierId"] = int(f["supplierId"])
    if f.get("type") is not None:
        query["type"] = f["type"]
    if f.get("updatedSince"):
        query["updatedAt"] = {"$gte": f["updatedSince"]}
    items = list(collection("products").find(query, NO_ID).sort("_id", 1))
    return JsonResponse(page(request, items))


@roles(*EDITORS)
def _create_product(request):
    data = body(request) or {}
    required = ["code", "name", "type", "categoryId", "unit", "referencePrice", "requiresLot"]
    missing = [f for f in required if data.get(f) in (None, "")]
    if missing:
        return error(request, 400, "VALIDATION_ERROR", "Campos obligatorios faltantes", {"missing": missing})
    if data["type"] not in TYPES or data["unit"] not in UNITS:
        return error(request, 400, "VALIDATION_ERROR", "type o unit inválido",
                     {"types": sorted(TYPES), "units": sorted(UNITS)})
    if not collection("categories").find_one({"_id": data["categoryId"]}):
        return error(request, 400, "VALIDATION_ERROR", "Categoría inexistente")
    if collection("products").find_one({"code": data["code"]}):
        return error(request, 409, "CONFLICT", "Código de producto duplicado")
    pid = f"p-{data['code'].lower()}"
    product = {**data, "id": pid, "active": True, "createdAt": _now(), "updatedAt": _now()}
    collection("products").insert_one({**product, "_id": pid})
    return JsonResponse(product, status=201)


@require_http_methods(["GET"])
@roles()
def product_detail(request, product_id):
    p = collection("products").find_one({"_id": product_id}, NO_ID)
    return JsonResponse(p) if p else error(request, 404, "NOT_FOUND", "Producto no encontrado")


@csrf_exempt
@require_http_methods(["GET", "POST"])
@roles()
def categories(request):
    if request.method == "GET":
        parent = request.GET.get("parentId")
        return JsonResponse(list(collection("categories").find({"parentId": parent}, NO_ID)), safe=False)
    return _create_category(request)


@roles(*EDITORS)
def _create_category(request):
    data = body(request) or {}
    if not data.get("name"):
        return error(request, 400, "VALIDATION_ERROR", "name es obligatorio")
    if data.get("parentId") and not collection("categories").find_one({"_id": data["parentId"]}):
        return error(request, 400, "VALIDATION_ERROR", "parentId inexistente")
    cid = "cat-" + data["name"].lower().replace(" ", "-")
    if collection("categories").find_one({"_id": cid}):
        return error(request, 409, "CONFLICT", "Categoría duplicada")
    category = {"id": cid, "name": data["name"], "parentId": data.get("parentId")}
    collection("categories").insert_one({**category, "_id": cid})
    return JsonResponse(category, status=201)
