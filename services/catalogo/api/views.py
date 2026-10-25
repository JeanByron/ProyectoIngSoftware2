"""Stub de Catálogo: productos y categorías en memoria (contrato: docs/api/catalogo.json)."""
from datetime import datetime, timezone

from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

from .common import body, error, page, roles

EDITORS = ("ADMIN", "JEFE_COMPRAS")
TYPES = {"FERTILIZANTE", "AGROQUIMICO", "SEMILLA", "HERRAMIENTA", "REPUESTO"}
UNITS = {"BULTO", "LITRO", "KILO", "UNIDAD"}


def _now():
    return datetime.now(timezone.utc).isoformat()


CATEGORIES = {
    "cat-agroquimicos": {"id": "cat-agroquimicos", "name": "Agroquímicos", "parentId": None},
    "cat-fungicidas": {"id": "cat-fungicidas", "name": "Fungicidas", "parentId": "cat-agroquimicos"},
    "cat-fertilizantes": {"id": "cat-fertilizantes", "name": "Fertilizantes", "parentId": None},
}
PRODUCTS = {
    "p-agq-0153": {
        "id": "p-agq-0153", "code": "AGQ-0153", "name": "Fungicida Alto 100 SL 1L", "type": "AGROQUIMICO",
        "categoryId": "cat-fungicidas", "unit": "LITRO", "referencePrice": 98500, "usualSupplierId": 1,
        "requiresLot": True, "icaRegistration": "ICA-1234",
        "technicalSheet": {"activeIngredient": "Ciproconazol", "toxicologicalCategory": "III"},
        "active": True, "createdAt": _now(), "updatedAt": _now(),
    },
    "p-fer-0001": {
        "id": "p-fer-0001", "code": "FER-0001", "name": "Urea 46% bulto 50 kg", "type": "FERTILIZANTE",
        "categoryId": "cat-fertilizantes", "unit": "BULTO", "referencePrice": 165000, "usualSupplierId": 2,
        "requiresLot": False, "icaRegistration": None, "technicalSheet": {},
        "active": True, "createdAt": _now(), "updatedAt": _now(),
    },
}


def _descendants(category_id):
    ids = {category_id}
    for c in CATEGORIES.values():
        if c["parentId"] == category_id:
            ids |= _descendants(c["id"])
    return ids


@csrf_exempt
@require_http_methods(["GET", "POST"])
@roles()
def products(request):
    if request.method == "POST":
        return _create_product(request)
    f = request.GET
    q = (f.get("q") or "").lower()
    cats = _descendants(f["categoryId"]) if f.get("categoryId") else None
    supplier = int(f["supplierId"]) if f.get("supplierId", "").isdigit() else None
    active = f.get("active", "true").lower() == "true"
    items = [
        p for p in PRODUCTS.values()
        if p["active"] == active
        and (not q or q in p["name"].lower() or q in p.get("description", "").lower())
        and f.get("code") in (None, p["code"])
        and (cats is None or p["categoryId"] in cats)
        and supplier in (None, p["usualSupplierId"])
        and f.get("type") in (None, p["type"])
        and (not f.get("updatedSince") or p["updatedAt"] >= f["updatedSince"])
    ]
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
    if data["categoryId"] not in CATEGORIES:
        return error(request, 400, "VALIDATION_ERROR", "Categoría inexistente")
    if any(p["code"] == data["code"] for p in PRODUCTS.values()):
        return error(request, 409, "CONFLICT", "Código de producto duplicado")
    pid = f"p-{data['code'].lower()}"
    PRODUCTS[pid] = {**data, "id": pid, "active": True, "createdAt": _now(), "updatedAt": _now()}
    return JsonResponse(PRODUCTS[pid], status=201)


@require_http_methods(["GET"])
@roles()
def product_detail(request, product_id):
    p = PRODUCTS.get(product_id)
    return JsonResponse(p) if p else error(request, 404, "NOT_FOUND", "Producto no encontrado")


@csrf_exempt
@require_http_methods(["GET", "POST"])
@roles()
def categories(request):
    if request.method == "GET":
        parent = request.GET.get("parentId")
        return JsonResponse([c for c in CATEGORIES.values() if c["parentId"] == parent], safe=False)
    return _create_category(request)


@roles(*EDITORS)
def _create_category(request):
    data = body(request) or {}
    if not data.get("name"):
        return error(request, 400, "VALIDATION_ERROR", "name es obligatorio")
    if data.get("parentId") and data["parentId"] not in CATEGORIES:
        return error(request, 400, "VALIDATION_ERROR", "parentId inexistente")
    cid = "cat-" + data["name"].lower().replace(" ", "-")
    if cid in CATEGORIES:
        return error(request, 409, "CONFLICT", "Categoría duplicada")
    CATEGORIES[cid] = {"id": cid, "name": data["name"], "parentId": data.get("parentId")}
    return JsonResponse(CATEGORIES[cid], status=201)
