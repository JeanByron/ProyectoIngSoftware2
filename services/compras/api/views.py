import json
import os
import urllib.error
import urllib.request
from datetime import datetime, timezone

from django.db import transaction
from django.db.models import Q
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

from .common import body, error, page, roles, user
from .models import PurchaseOrder, PurchaseOrderLine, Receipt, Supplier

CATALOGO_URL = os.getenv("CATALOGO_URL", "http://127.0.0.1:8002/api/v1")
INVENTARIO_URL = os.getenv("INVENTARIO_URL", "http://127.0.0.1:8003/api/v1")
INTERNAL_TIMEOUT = float(os.getenv("INTERNAL_TIMEOUT_S", "2"))
APPROVAL_THRESHOLD = 20_000_000


def _now():
    return datetime.now(timezone.utc).isoformat()


def _call(method, url, request, payload=None, idempotency_key=None):
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
    order.status = status
    order.history = order.history + [{"status": status, "userId": uid, "at": _now(), "notes": notes}]
    order.save()


@csrf_exempt
@require_http_methods(["GET", "POST"])
@roles("GERENTE", "JEFE_COMPRAS", "AUX_COMPRAS", "AUDITOR")
def suppliers(request):
    if request.method == "GET":
        q = (request.GET.get("q") or "").lower()
        items = [s.to_dict() for s in Supplier.objects.filter(Q(name__icontains=q) | Q(nit__contains=q))]
        return JsonResponse(page(request, items))
    if user(request)["role"] != "JEFE_COMPRAS":
        return error(request, 403, "FORBIDDEN", "Solo el jefe de compras registra proveedores")
    data = body(request) or {}
    if not data.get("nit") or not data.get("name"):
        return error(request, 400, "VALIDATION_ERROR", "nit y name son obligatorios")
    if Supplier.objects.filter(nit=data["nit"]).exists():
        return error(request, 409, "CONFLICT", "NIT ya registrado")
    supplier = Supplier.objects.create(
        nit=data["nit"], name=data["name"], type=data.get("type"), contact_name=data.get("contactName"),
        email=data.get("email"), phone=data.get("phone"), city=data.get("city"),
        default_lead_time_days=data.get("defaultLeadTimeDays"),
    )
    return JsonResponse(supplier.to_dict(), status=201)


@csrf_exempt
@require_http_methods(["GET", "POST"])
@roles("GERENTE", "JEFE_COMPRAS", "AUX_COMPRAS", "JEFE_BODEGA", "AUDITOR")
def purchase_orders(request):
    if request.method == "GET":
        qs = PurchaseOrder.objects.select_related("supplier").prefetch_related("lines")
        if request.GET.get("status") is not None:
            qs = qs.filter(status=request.GET["status"])
        return JsonResponse(page(request, [o.to_dict() for o in qs]))
    if user(request)["role"] != "JEFE_COMPRAS":
        return error(request, 403, "FORBIDDEN", "Solo el jefe de compras crea órdenes")
    data = body(request) or {}
    supplier_id = data.get("supplierId")
    supplier = Supplier.objects.filter(id=supplier_id).first() if isinstance(supplier_id, int) else None
    if not supplier or not data.get("destinationWarehouseId") or not data.get("lines"):
        return error(request, 400, "VALIDATION_ERROR", "supplierId válido, destinationWarehouseId y lines obligatorios")
    lines = []
    for i, line in enumerate(data["lines"], start=1):
        try:
            product = _call("GET", f"{CATALOGO_URL}/products/{line['productId']}", request)
        except urllib.error.HTTPError:
            return error(request, 422, "PRODUCT_NOT_FOUND", f"Producto {line['productId']} no existe en Catálogo")
        except (urllib.error.URLError, TimeoutError):
            return error(request, 503, "CATALOGO_UNAVAILABLE", "Catálogo no disponible, intente más tarde")
        qty, price = float(line["quantity"]), float(line["unitPrice"])
        lines.append(PurchaseOrderLine(
            line_number=i, product_id=product["id"], product_code=product["code"], product_name=product["name"],
            unit=product["unit"], requires_lot=product["requiresLot"], quantity=qty, received_quantity=0,
            pending_quantity=qty, unit_price=price, subtotal=qty * price,
        ))
    with transaction.atomic():
        order = PurchaseOrder.objects.create(
            supplier=supplier, destination_warehouse_id=data["destinationWarehouseId"], status="BORRADOR",
            total=sum(ln.subtotal for ln in lines), expected_delivery_date=data.get("expectedDeliveryDate"),
            created_by=user(request)["id"],
        )
        order.number = f"OC-2026-{order.id:04d}"
        for ln in lines:
            ln.order = order
        PurchaseOrderLine.objects.bulk_create(lines)
        _change(order, "BORRADOR", user(request)["id"])
    order.refresh_from_db()
    return JsonResponse(order.to_dict(), status=201)


def _order_or_404(request, order_id, lock=False):
    qs = PurchaseOrder.objects.select_for_update() if lock else PurchaseOrder.objects
    o = qs.filter(id=order_id).first()
    return (o, None) if o else (None, error(request, 404, "NOT_FOUND", "Orden no encontrada"))


@require_http_methods(["GET"])
@roles("GERENTE", "JEFE_COMPRAS", "AUX_COMPRAS", "JEFE_BODEGA", "AUDITOR")
def order_detail(request, order_id):
    o, err = _order_or_404(request, order_id)
    return err or JsonResponse(o.to_dict())


@csrf_exempt
@require_http_methods(["POST"])
@roles("JEFE_COMPRAS", "GERENTE")
@transaction.atomic
def order_approve(request, order_id):
    o, err = _order_or_404(request, order_id, lock=True)
    if err:
        return err
    if o.status != "BORRADOR":
        return error(request, 409, "INVALID_STATE", f"No se puede aprobar en estado {o.status}")
    u = user(request)
    if o.total > APPROVAL_THRESHOLD and u["role"] != "GERENTE":
        return error(request, 403, "APPROVAL_REQUIRES_MANAGER",
                     "El total supera el umbral; debe aprobar el gerente", {"threshold": APPROVAL_THRESHOLD})
    o.approved_by = u["id"]
    _change(o, "APROBADA", u["id"])
    return JsonResponse(o.to_dict())


@csrf_exempt
@require_http_methods(["POST"])
@roles("JEFE_COMPRAS", "AUX_COMPRAS")
@transaction.atomic
def order_send(request, order_id):
    o, err = _order_or_404(request, order_id, lock=True)
    if err:
        return err
    if o.status != "APROBADA":
        return error(request, 409, "INVALID_STATE", f"No se puede enviar en estado {o.status}")
    _change(o, "ENVIADA", user(request)["id"])
    return JsonResponse(o.to_dict())


@csrf_exempt
@require_http_methods(["GET", "POST"])
@roles("GERENTE", "JEFE_COMPRAS", "AUX_COMPRAS", "JEFE_BODEGA", "BODEGUERO", "AUDITOR")
def order_receipts(request, order_id):
    o, err = _order_or_404(request, order_id)
    if err:
        return err
    if request.method == "GET":
        return JsonResponse([r.to_dict() for r in o.receipts.all()], safe=False)

    receipt_id = request.headers.get("Idempotency-Key")
    if not receipt_id:
        return error(request, 400, "VALIDATION_ERROR", "Idempotency-Key obligatoria")
    saved = Receipt.objects.filter(id=receipt_id).first()
    if saved:
        return JsonResponse(saved.to_dict(), status=201)
    if o.status not in ("ENVIADA", "RECIBIDA_PARCIAL"):
        return error(request, 409, "INVALID_STATE", f"No se puede recibir en estado {o.status}")
    data = body(request) or {}
    by_id = {ln.line_number: ln for ln in o.lines.all()}
    entry_lines, plan = [], []
    for r in data.get("lines", []):
        ln = by_id.get(r.get("lineId"))
        qty = float(r.get("quantity", 0))
        if not ln or qty <= 0 or qty > ln.pending_quantity:
            return error(request, 422, "INVALID_QUANTITY", "Línea inexistente o cantidad mayor a lo pendiente",
                         {"lineId": r.get("lineId")})
        if ln.requires_lot and not (r.get("lotNumber") and r.get("expiryDate")):
            return error(request, 422, "LOT_REQUIRED", "Lote y vencimiento obligatorios", {"lineId": ln.line_number})
        plan.append((ln, qty))
        entry_lines.append({"product": {"productId": ln.product_id, "code": ln.product_code,
                                        "name": ln.product_name, "unit": ln.unit,
                                        "requiresLot": ln.requires_lot},
                            "lotNumber": r.get("lotNumber"), "expiryDate": r.get("expiryDate"), "quantity": qty})
    if not plan:
        return error(request, 400, "VALIDATION_ERROR", "lines obligatorio")
    warehouse_id = data.get("warehouseId") or o.destination_warehouse_id

    try:
        movements = _call("POST", f"{INVENTARIO_URL}/internal/entries", request,
                          {"receiptId": receipt_id, "purchaseOrderId": o.id, "warehouseId": warehouse_id,
                           "lines": entry_lines}, idempotency_key=receipt_id)
    except urllib.error.HTTPError as exc:
        return error(request, 502, "INVENTARIO_ERROR", "Inventario rechazó la entrada", {"status": exc.code})
    except (urllib.error.URLError, TimeoutError):
        return error(request, 503, "INVENTARIO_UNAVAILABLE",
                     "Inventario no disponible; reintente con el mismo Idempotency-Key")

    with transaction.atomic():
        for ln, qty in plan:
            ln.received_quantity += qty
            ln.pending_quantity -= qty
            ln.save()
        complete = all(ln.pending_quantity == 0 for ln in by_id.values())
        _change(o, "RECIBIDA" if complete else "RECIBIDA_PARCIAL", user(request)["id"])
        receipt = Receipt.objects.create(
            id=receipt_id, order=o, warehouse_id=warehouse_id, delivery_note=data.get("deliveryNote"),
            lines=[{"lineId": ln.line_number, "productId": ln.product_id, "quantity": q} for ln, q in plan],
            inventory_movement_ids=[m["id"] for m in movements], received_by=user(request)["id"],
        )
    return JsonResponse(receipt.to_dict(), status=201)
