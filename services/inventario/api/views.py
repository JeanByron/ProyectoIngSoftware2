"""Stub de Inventario: existencias por lote en memoria, FEFO, movimientos y traslados
(contrato: docs/api/inventario.json)."""
from datetime import datetime, timezone

from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

from .common import body, error, idempotent, page, roles, user

WAREHOUSES = {
    "CHI": {"id": "CHI", "name": "Chinchiná", "type": "CENTRAL", "active": True},
    "MZL": {"id": "MZL", "name": "Manizales", "type": "PUNTO_VENTA", "active": True},
    "SRC": {"id": "SRC", "name": "Santa Rosa de Cabal", "type": "PUNTO_VENTA", "active": True},
    "ANS": {"id": "ANS", "name": "Anserma", "type": "RURAL", "active": True},
    "RSU": {"id": "RSU", "name": "Riosucio", "type": "RURAL", "active": True},
}
PRODUCTS = {
    "p-agq-0153": {"productId": "p-agq-0153", "code": "AGQ-0153", "name": "Fungicida Alto 100 SL 1L",
                   "unit": "LITRO", "requiresLot": True},
    "p-fer-0001": {"productId": "p-fer-0001", "code": "FER-0001", "name": "Urea 46% bulto 50 kg",
                   "unit": "BULTO", "requiresLot": False},
}
# (productId, warehouseId, lotNumber) -> {"expiryDate", "quantity", "updatedAt"}
STOCK = {
    ("p-agq-0153", "CHI", "L2026-031"): {"expiryDate": "2027-01-15", "quantity": 120},
    ("p-agq-0153", "CHI", "L2026-007"): {"expiryDate": "2026-12-01", "quantity": 40},
    ("p-fer-0001", "CHI", None): {"expiryDate": None, "quantity": 600},
    ("p-fer-0001", "ANS", None): {"expiryDate": None, "quantity": 5},
}
MOVEMENTS = []
TRANSFERS = {}
ALL_ROLES = ()


def _now():
    return datetime.now(timezone.utc).isoformat()


def _stock_row(key, value):
    product_id, warehouse_id, lot = key
    return {"product": PRODUCTS.get(product_id), "warehouseId": warehouse_id, "lotNumber": lot,
            "expiryDate": value["expiryDate"], "quantity": value["quantity"], "updatedAt": value.get("updatedAt")}


def _fefo(product_id, warehouse_id, quantity):
    """Asigna lotes del que vence primero al último. Devuelve None si no alcanza."""
    lots = sorted(
        ((k[2], v) for k, v in STOCK.items() if k[0] == product_id and k[1] == warehouse_id and v["quantity"] > 0),
        key=lambda item: item[1]["expiryDate"] or "9999-12-31",
    )
    allocations, remaining = [], quantity
    for lot, value in lots:
        if remaining <= 0:
            break
        take = min(value["quantity"], remaining)
        allocations.append({"lotNumber": lot, "expiryDate": value["expiryDate"], "quantity": take})
        remaining -= take
    return allocations if remaining <= 0 else None


def _apply(mtype, product_id, warehouse_id, lot, qty, reason, uid, ref_type="MANUAL", ref_id=None, expiry=None):
    key = (product_id, warehouse_id, lot)
    row = STOCK.setdefault(key, {"expiryDate": expiry, "quantity": 0})
    row["quantity"] += qty
    row["updatedAt"] = _now()
    movement = {"id": len(MOVEMENTS) + 1, "type": mtype, "productId": product_id, "warehouseId": warehouse_id,
                "lotNumber": lot, "quantity": qty, "balanceAfter": row["quantity"], "reason": reason,
                "referenceType": ref_type, "referenceId": ref_id, "userId": uid, "createdAt": _now()}
    MOVEMENTS.append(movement)
    return movement


def _can_use_warehouse(request, warehouse_id):
    allowed = user(request)["warehouses"]
    return not allowed or warehouse_id in allowed


@require_http_methods(["GET"])
@roles()
def warehouses(request):
    return JsonResponse(list(WAREHOUSES.values()), safe=False)


@require_http_methods(["GET"])
@roles()
def stock(request):
    f = request.GET
    items = [_stock_row(k, v) for k, v in STOCK.items()
             if f.get("productId") in (None, k[0]) and f.get("warehouseId") in (None, k[1])
             and f.get("lotNumber") in (None, k[2])]
    return JsonResponse(page(request, items))


@require_http_methods(["GET"])
@roles("JEFE_BODEGA", "BODEGUERO", "VENDEDOR")
def fefo_suggestion(request):
    product_id, warehouse_id = request.GET.get("productId"), request.GET.get("warehouseId")
    try:
        quantity = float(request.GET.get("quantity", 0))
    except ValueError:
        quantity = 0
    if not product_id or not warehouse_id or quantity <= 0:
        return error(request, 400, "VALIDATION_ERROR", "productId, warehouseId y quantity > 0 son obligatorios")
    allocations = _fefo(product_id, warehouse_id, quantity)
    if allocations is None:
        return error(request, 422, "INSUFFICIENT_STOCK", "Stock insuficiente en la bodega")
    return JsonResponse({"productId": product_id, "warehouseId": warehouse_id, "requested": quantity,
                         "allocations": allocations})


@csrf_exempt
@require_http_methods(["GET", "POST"])
@roles("GERENTE", "JEFE_COMPRAS", "AUX_COMPRAS", "JEFE_BODEGA", "BODEGUERO", "AUDITOR")
@idempotent
def movements(request):
    if request.method == "GET":
        f = request.GET
        items = [m for m in MOVEMENTS if f.get("productId") in (None, m["productId"])
                 and f.get("warehouseId") in (None, m["warehouseId"]) and f.get("type") in (None, m["type"])]
        return JsonResponse(page(request, list(reversed(items))))

    if user(request)["role"] not in ("JEFE_BODEGA", "BODEGUERO"):
        return error(request, 403, "FORBIDDEN", "Solo bodega registra movimientos")
    data = body(request) or {}
    missing = [f for f in ("type", "productId", "warehouseId", "quantity", "reason") if data.get(f) in (None, "")]
    if missing:
        return error(request, 400, "VALIDATION_ERROR", "Campos obligatorios faltantes", {"missing": missing})
    mtype, pid, wid, qty = data["type"], data["productId"], data["warehouseId"], float(data["quantity"])
    if mtype not in ("ENTRADA", "SALIDA", "AJUSTE"):
        return error(request, 400, "VALIDATION_ERROR", "type debe ser ENTRADA, SALIDA o AJUSTE")
    if wid not in WAREHOUSES:
        return error(request, 400, "VALIDATION_ERROR", "Bodega inexistente")
    if not _can_use_warehouse(request, wid):
        return error(request, 403, "FORBIDDEN", "Bodega fuera del alcance del usuario")
    if pid not in PRODUCTS:
        if not data.get("product"):
            return error(request, 400, "VALIDATION_ERROR", "Producto desconocido: enviar 'product' (ProductRef)")
        PRODUCTS[pid] = {**data["product"], "productId": pid}
    product, uid = PRODUCTS[pid], user(request)["id"]

    if mtype == "ENTRADA":
        if product["requiresLot"] and not (data.get("lotNumber") and data.get("expiryDate")):
            return error(request, 400, "VALIDATION_ERROR", "Producto con control de lote: lotNumber y expiryDate obligatorios")
        lot = data.get("lotNumber") if product["requiresLot"] else None
        created = [_apply("ENTRADA", pid, wid, lot, qty, data["reason"], uid, expiry=data.get("expiryDate"))]
    elif mtype == "SALIDA":
        if data.get("lotNumber"):
            current = STOCK.get((pid, wid, data["lotNumber"]), {}).get("quantity", 0)
            allocations = [{"lotNumber": data["lotNumber"], "quantity": qty}] if current >= qty else None
        else:
            allocations = _fefo(pid, wid, qty)
        if allocations is None:
            return error(request, 422, "INSUFFICIENT_STOCK", "Stock insuficiente en la bodega")
        created = [_apply("SALIDA", pid, wid, a["lotNumber"], -a["quantity"], data["reason"], uid) for a in allocations]
    else:
        lot = data.get("lotNumber") if product["requiresLot"] else None
        if STOCK.get((pid, wid, lot), {}).get("quantity", 0) + qty < 0:
            return error(request, 422, "INSUFFICIENT_STOCK", "El ajuste dejaría saldo negativo")
        created = [_apply("AJUSTE", pid, wid, lot, qty, data["reason"], uid)]
    return JsonResponse(created, status=201, safe=False)


def _transfer_or_404(request, transfer_id):
    t = TRANSFERS.get(transfer_id)
    return (t, None) if t else (None, error(request, 404, "NOT_FOUND", "Traslado no encontrado"))


def _change(t, status, uid, notes=""):
    t["status"] = status
    t["updatedAt"] = _now()
    t["history"].append({"status": status, "userId": uid, "at": _now(), "notes": notes})


@csrf_exempt
@require_http_methods(["GET", "POST"])
@roles("GERENTE", "JEFE_BODEGA", "BODEGUERO", "VENDEDOR", "AUDITOR")
@idempotent
def transfers(request):
    if request.method == "GET":
        items = [t for t in TRANSFERS.values() if request.GET.get("status") in (None, t["status"])]
        return JsonResponse(page(request, items))
    if user(request)["role"] not in ("VENDEDOR", "BODEGUERO", "JEFE_BODEGA"):
        return error(request, 403, "FORBIDDEN", "Rol sin permiso para solicitar traslados")
    data = body(request) or {}
    origin, dest, items = data.get("originId"), data.get("destinationId"), data.get("items") or []
    if origin not in WAREHOUSES or dest not in WAREHOUSES or origin == dest or not items:
        return error(request, 400, "VALIDATION_ERROR", "originId/destinationId válidos y distintos, e items no vacío")
    tid = len(TRANSFERS) + 1
    TRANSFERS[tid] = {
        "id": tid, "originId": origin, "destinationId": dest, "status": "SOLICITADO",
        "items": [{"productId": i["productId"], "requestedQuantity": i["quantity"], "lots": []} for i in items],
        "history": [], "createdAt": _now(), "updatedAt": _now(),
    }
    _change(TRANSFERS[tid], "SOLICITADO", user(request)["id"], data.get("notes", ""))
    return JsonResponse(TRANSFERS[tid], status=201)


@require_http_methods(["GET"])
@roles("GERENTE", "JEFE_BODEGA", "BODEGUERO", "VENDEDOR", "AUDITOR")
def transfer_detail(request, transfer_id):
    t, err = _transfer_or_404(request, transfer_id)
    return err or JsonResponse(t)


@csrf_exempt
@require_http_methods(["POST"])
@roles("JEFE_BODEGA")
def transfer_approve(request, transfer_id):
    t, err = _transfer_or_404(request, transfer_id)
    if err:
        return err
    if t["status"] != "SOLICITADO":
        return error(request, 409, "INVALID_STATE", f"No se puede aprobar en estado {t['status']}")
    _change(t, "APROBADO", user(request)["id"])
    return JsonResponse(t)


@csrf_exempt
@require_http_methods(["POST"])
@roles("JEFE_BODEGA", "BODEGUERO")
@idempotent
def transfer_dispatch(request, transfer_id):
    """Descuenta en origen (FEFO) y deja el traslado EN_TRANSITO, todo o nada."""
    t, err = _transfer_or_404(request, transfer_id)
    if err:
        return err
    if t["status"] != "APROBADO":
        return error(request, 409, "INVALID_STATE", f"No se puede despachar en estado {t['status']}")
    plan = []
    for item in t["items"]:
        allocations = _fefo(item["productId"], t["originId"], item["requestedQuantity"])
        if allocations is None:
            return error(request, 422, "INSUFFICIENT_STOCK", f"Stock insuficiente de {item['productId']} en origen")
        plan.append((item, allocations))
    uid = user(request)["id"]
    for item, allocations in plan:
        for a in allocations:
            _apply("TRASLADO_SALIDA", item["productId"], t["originId"], a["lotNumber"], -a["quantity"],
                   "TRASLADO", uid, "TRASLADO", str(t["id"]))
            item["lots"].append({"lotNumber": a["lotNumber"], "expiryDate": a["expiryDate"],
                                 "dispatchedQuantity": a["quantity"], "receivedQuantity": None,
                                 "difference": None, "differenceReason": None})
    _change(t, "EN_TRANSITO", uid)
    return JsonResponse(t)


@csrf_exempt
@require_http_methods(["POST"])
@roles("JEFE_BODEGA", "BODEGUERO")
@idempotent
def transfer_receive(request, transfer_id):
    """Suma en destino lo recibido por lote y registra diferencias contra lo despachado."""
    t, err = _transfer_or_404(request, transfer_id)
    if err:
        return err
    if t["status"] != "EN_TRANSITO":
        return error(request, 409, "INVALID_STATE", f"No se puede recibir en estado {t['status']}")
    received = {(r["productId"], r.get("lotNumber")): r for r in (body(request) or {}).get("lots", [])}
    uid, with_diff = user(request)["id"], False
    for item in t["items"]:
        for lot in item["lots"]:
            r = received.get((item["productId"], lot["lotNumber"]))
            qty = float(r["receivedQuantity"]) if r else lot["dispatchedQuantity"]
            lot["receivedQuantity"] = qty
            lot["difference"] = qty - lot["dispatchedQuantity"]
            lot["differenceReason"] = (r or {}).get("differenceReason")
            with_diff = with_diff or lot["difference"] != 0
            if qty > 0:
                _apply("TRASLADO_ENTRADA", item["productId"], t["destinationId"], lot["lotNumber"], qty,
                       "TRASLADO", uid, "TRASLADO", str(t["id"]), expiry=lot["expiryDate"])
    _change(t, "RECIBIDO_CON_DIFERENCIAS" if with_diff else "RECIBIDO", uid)
    return JsonResponse(t)


@csrf_exempt
@require_http_methods(["POST"])
@idempotent
def internal_entries(request):
    """Entrada por recepción de OC. Solo la llama Compras (en K8s, NetworkPolicy)."""
    if not request.headers.get("Idempotency-Key"):
        return error(request, 400, "VALIDATION_ERROR", "Idempotency-Key obligatoria")
    data = body(request) or {}
    if data.get("warehouseId") not in WAREHOUSES or not data.get("lines"):
        return error(request, 400, "VALIDATION_ERROR", "warehouseId válido y lines obligatorios")
    created = []
    for line in data["lines"]:
        product = line["product"]
        PRODUCTS.setdefault(product["productId"], product)
        lot = line.get("lotNumber") if product.get("requiresLot") else None
        created.append(_apply("ENTRADA_COMPRA", product["productId"], data["warehouseId"], lot,
                              float(line["quantity"]), "COMPRA", user(request)["id"], "RECEPCION_OC",
                              data.get("receiptId"), expiry=line.get("expiryDate")))
    return JsonResponse(created, status=201, safe=False)
