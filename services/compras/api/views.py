"""Stub de Compras: proveedores y órdenes de compra en memoria; la recepción llama a Inventario
(contrato: docs/api/compras.json)."""
import json
import os
import urllib.error
import urllib.request
from datetime import datetime, timezone

from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

from .common import body, error, page, roles, user

CATALOGO_URL = os.getenv("CATALOGO_URL", "http://127.0.0.1:8002/api/v1")
INVENTARIO_URL = os.getenv("INVENTARIO_URL", "http://127.0.0.1:8003/api/v1")
INTERNAL_TIMEOUT = float(os.getenv("INTERNAL_TIMEOUT_S", "2"))
APPROVAL_THRESHOLD = 20_000_000

SUPPLIERS = {
    1: {"id": 1, "nit": "900123456-7", "name": "Agroquímicos del Café S.A.S.", "type": "MULTINACIONAL",
        "email": "ventas@agrocafe.co", "defaultLeadTimeDays": 8, "active": True},
    2: {"id": 2, "nit": "800987654-1", "name": "Fertilizantes Andinos Ltda.", "type": "IMPORTADOR",
        "email": "pedidos@fertiandinos.co", "defaultLeadTimeDays": 12, "active": True},
}
ORDERS = {}
RECEIPTS = {}


def _now():
    return datetime.now(timezone.utc).isoformat()


def _call(method, url, request, payload=None, idempotency_key=None):
    """Llamada REST interna propagando usuario y correlación. Lanza URLError/HTTPError."""
    u = user(request)
    headers = {"Content-Type": "application/json", "X-Correlation-Id": request.correlation_id,
               "X-User-Id": str(u["id"]), "X-User-Role": u["role"]}
    if idempotency_key:
        headers["Idempotency-Key"] = idempotency_key
    data = json.dumps(payload).encode() if payload is not None else None
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    with urllib.request.urlopen(req, timeout=INTERNAL_TIMEOUT) as resp:
        return json.loads(resp.read() or b"null")


def _change(order, status, uid, notes=""):
    order["status"] = status
    order["updatedAt"] = _now()
    order["history"].append({"status": status, "userId": uid, "at": _now(), "notes": notes})


@csrf_exempt
@require_http_methods(["GET", "POST"])
@roles("GERENTE", "JEFE_COMPRAS", "AUX_COMPRAS", "AUDITOR")
def suppliers(request):
    if request.method == "GET":
        q = (request.GET.get("q") or "").lower()
        items = [s for s in SUPPLIERS.values() if q in s["name"].lower() or q in s["nit"]]
        return JsonResponse(page(request, items))
    if user(request)["role"] != "JEFE_COMPRAS":
        return error(request, 403, "FORBIDDEN", "Solo el jefe de compras registra proveedores")
    data = body(request) or {}
    if not data.get("nit") or not data.get("name"):
        return error(request, 400, "VALIDATION_ERROR", "nit y name son obligatorios")
    if any(s["nit"] == data["nit"] for s in SUPPLIERS.values()):
        return error(request, 409, "CONFLICT", "NIT ya registrado")
    sid = max(SUPPLIERS) + 1
    SUPPLIERS[sid] = {**data, "id": sid, "active": True, "createdAt": _now(), "updatedAt": _now()}
    return JsonResponse(SUPPLIERS[sid], status=201)


@csrf_exempt
@require_http_methods(["GET", "POST"])
@roles("GERENTE", "JEFE_COMPRAS", "AUX_COMPRAS", "JEFE_BODEGA", "AUDITOR")
def purchase_orders(request):
    if request.method == "GET":
        items = [o for o in ORDERS.values() if request.GET.get("status") in (None, o["status"])]
        return JsonResponse(page(request, items))
    if user(request)["role"] != "JEFE_COMPRAS":
        return error(request, 403, "FORBIDDEN", "Solo el jefe de compras crea órdenes")
    data = body(request) or {}
    if data.get("supplierId") not in SUPPLIERS or not data.get("destinationWarehouseId") or not data.get("lines"):
        return error(request, 400, "VALIDATION_ERROR", "supplierId válido, destinationWarehouseId y lines obligatorios")
    lines = []
    for i, line in enumerate(data["lines"], start=1):
        # Consulta no crítica al Catálogo: copia los datos del producto en la línea.
        try:
            product = _call("GET", f"{CATALOGO_URL}/products/{line['productId']}", request)
        except urllib.error.HTTPError:
            return error(request, 422, "PRODUCT_NOT_FOUND", f"Producto {line['productId']} no existe en Catálogo")
        except (urllib.error.URLError, TimeoutError):
            return error(request, 503, "CATALOGO_UNAVAILABLE", "Catálogo no disponible, intente más tarde")
        qty, price = float(line["quantity"]), float(line["unitPrice"])
        lines.append({"id": i, "productId": product["id"], "productCode": product["code"],
                      "productName": product["name"], "unit": product["unit"],
                      "requiresLot": product["requiresLot"], "quantity": qty, "receivedQuantity": 0,
                      "pendingQuantity": qty, "unitPrice": price, "subtotal": qty * price})
    oid = len(ORDERS) + 1
    ORDERS[oid] = {
        "id": oid, "number": f"OC-2026-{oid:04d}", "supplierId": data["supplierId"],
        "supplierName": SUPPLIERS[data["supplierId"]]["name"],
        "destinationWarehouseId": data["destinationWarehouseId"], "status": "BORRADOR",
        "total": sum(ln["subtotal"] for ln in lines), "expectedDeliveryDate": data.get("expectedDeliveryDate"),
        "lines": lines, "history": [], "createdBy": user(request)["id"], "approvedBy": None,
        "createdAt": _now(), "updatedAt": _now(),
    }
    _change(ORDERS[oid], "BORRADOR", user(request)["id"])
    return JsonResponse(ORDERS[oid], status=201)


def _order_or_404(request, order_id):
    o = ORDERS.get(order_id)
    return (o, None) if o else (None, error(request, 404, "NOT_FOUND", "Orden no encontrada"))


@require_http_methods(["GET"])
@roles("GERENTE", "JEFE_COMPRAS", "AUX_COMPRAS", "JEFE_BODEGA", "AUDITOR")
def order_detail(request, order_id):
    o, err = _order_or_404(request, order_id)
    return err or JsonResponse(o)


@csrf_exempt
@require_http_methods(["POST"])
@roles("JEFE_COMPRAS", "GERENTE")
def order_approve(request, order_id):
    o, err = _order_or_404(request, order_id)
    if err:
        return err
    if o["status"] != "BORRADOR":
        return error(request, 409, "INVALID_STATE", f"No se puede aprobar en estado {o['status']}")
    u = user(request)
    if o["total"] > APPROVAL_THRESHOLD and u["role"] != "GERENTE":
        return error(request, 403, "APPROVAL_REQUIRES_MANAGER",
                     "El total supera el umbral; debe aprobar el gerente", {"threshold": APPROVAL_THRESHOLD})
    o["approvedBy"] = u["id"]
    _change(o, "APROBADA", u["id"])
    return JsonResponse(o)


@csrf_exempt
@require_http_methods(["POST"])
@roles("JEFE_COMPRAS", "AUX_COMPRAS")
def order_send(request, order_id):
    o, err = _order_or_404(request, order_id)
    if err:
        return err
    if o["status"] != "APROBADA":
        return error(request, 409, "INVALID_STATE", f"No se puede enviar en estado {o['status']}")
    _change(o, "ENVIADA", user(request)["id"])
    return JsonResponse(o)


@csrf_exempt
@require_http_methods(["GET", "POST"])
@roles("GERENTE", "JEFE_COMPRAS", "AUX_COMPRAS", "JEFE_BODEGA", "BODEGUERO", "AUDITOR")
def order_receipts(request, order_id):
    o, err = _order_or_404(request, order_id)
    if err:
        return err
    if request.method == "GET":
        return JsonResponse([r for r in RECEIPTS.values() if r["purchaseOrderId"] == order_id], safe=False)

    receipt_id = request.headers.get("Idempotency-Key")
    if not receipt_id:
        return error(request, 400, "VALIDATION_ERROR", "Idempotency-Key obligatoria")
    if receipt_id in RECEIPTS:
        return JsonResponse(RECEIPTS[receipt_id], status=201)
    if o["status"] not in ("ENVIADA", "RECIBIDA_PARCIAL"):
        return error(request, 409, "INVALID_STATE", f"No se puede recibir en estado {o['status']}")
    data = body(request) or {}
    by_id = {ln["id"]: ln for ln in o["lines"]}
    entry_lines, plan = [], []
    for r in data.get("lines", []):
        ln = by_id.get(r.get("lineId"))
        qty = float(r.get("quantity", 0))
        if not ln or qty <= 0 or qty > ln["pendingQuantity"]:
            return error(request, 422, "INVALID_QUANTITY", "Línea inexistente o cantidad mayor a lo pendiente",
                         {"lineId": r.get("lineId")})
        if ln["requiresLot"] and not (r.get("lotNumber") and r.get("expiryDate")):
            return error(request, 422, "LOT_REQUIRED", "Lote y vencimiento obligatorios", {"lineId": ln["id"]})
        plan.append((ln, qty))
        entry_lines.append({"product": {"productId": ln["productId"], "code": ln["productCode"],
                                        "name": ln["productName"], "unit": ln["unit"],
                                        "requiresLot": ln["requiresLot"]},
                            "lotNumber": r.get("lotNumber"), "expiryDate": r.get("expiryDate"), "quantity": qty})
    if not plan:
        return error(request, 400, "VALIDATION_ERROR", "lines obligatorio")
    warehouse_id = data.get("warehouseId") or o["destinationWarehouseId"]

    # Paso remoto primero: si Inventario falla no se modifica nada local (equivale a revertir).
    try:
        movements = _call("POST", f"{INVENTARIO_URL}/internal/entries", request,
                          {"receiptId": receipt_id, "purchaseOrderId": o["id"], "warehouseId": warehouse_id,
                           "lines": entry_lines}, idempotency_key=receipt_id)
    except urllib.error.HTTPError as exc:
        return error(request, 502, "INVENTARIO_ERROR", "Inventario rechazó la entrada", {"status": exc.code})
    except (urllib.error.URLError, TimeoutError):
        return error(request, 503, "INVENTARIO_UNAVAILABLE",
                     "Inventario no disponible; reintente con el mismo Idempotency-Key")

    for ln, qty in plan:
        ln["receivedQuantity"] += qty
        ln["pendingQuantity"] -= qty
    complete = all(ln["pendingQuantity"] == 0 for ln in o["lines"])
    _change(o, "RECIBIDA" if complete else "RECIBIDA_PARCIAL", user(request)["id"])
    RECEIPTS[receipt_id] = {
        "id": receipt_id, "purchaseOrderId": o["id"], "warehouseId": warehouse_id,
        "deliveryNote": data.get("deliveryNote"),
        "lines": [{"lineId": ln["id"], "productId": ln["productId"], "quantity": q} for ln, q in plan],
        "inventoryMovementIds": [m["id"] for m in movements], "receivedBy": user(request)["id"],
        "receivedAt": _now(),
    }
    return JsonResponse(RECEIPTS[receipt_id], status=201)
