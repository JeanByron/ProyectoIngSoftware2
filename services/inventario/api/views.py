from datetime import datetime, timezone

from django.db import transaction
from django.db.models import F
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

from .common import body, error, idempotent, page, roles, user
from .models import Movement, ProductRef, Stock, Transfer, Warehouse


def _now():
    return datetime.now(timezone.utc).isoformat()


def _fefo(product_id, warehouse_id, quantity, lock=False):
    qs = Stock.objects.filter(product_id=product_id, warehouse_id=warehouse_id, quantity__gt=0).order_by(
        F("expiry_date").asc(nulls_last=True), "id")
    if lock:
        qs = qs.select_for_update()
    allocations, remaining = [], quantity
    for s in qs:
        if remaining <= 0:
            break
        take = min(s.quantity, remaining)
        allocations.append({"lotNumber": s.lot_number or None,
                            "expiryDate": s.expiry_date.isoformat() if s.expiry_date else None,
                            "quantity": take})
        remaining -= take
    return allocations if remaining <= 0 else None


def _apply(mtype, product_id, warehouse_id, lot, qty, reason, uid, ref_type="MANUAL", ref_id=None, expiry=None):
    row, _ = Stock.objects.select_for_update().get_or_create(
        product_id=product_id, warehouse_id=warehouse_id, lot_number=lot or "",
        defaults={"expiry_date": expiry, "quantity": 0},
    )
    row.quantity += qty
    row.updated_at = datetime.now(timezone.utc)
    row.save()
    movement = Movement.objects.create(
        type=mtype, product_id=product_id, warehouse_id=warehouse_id, lot_number=lot, quantity=qty,
        balance_after=row.quantity, reason=reason, reference_type=ref_type, reference_id=ref_id, user_id=uid,
    )
    return movement.to_dict()


def _filters(request, fields):
    return {field: request.GET[param] for param, field in fields.items() if param in request.GET}


def _can_use_warehouse(request, warehouse_id):
    allowed = user(request)["warehouses"]
    return not allowed or warehouse_id in allowed


@require_http_methods(["GET"])
@roles()
def warehouses(request):
    return JsonResponse([w.to_dict() for w in Warehouse.objects.all()], safe=False)


@require_http_methods(["GET"])
@roles()
def stock(request):
    qs = Stock.objects.select_related("product").filter(**_filters(
        request, {"productId": "product_id", "warehouseId": "warehouse_id", "lotNumber": "lot_number"}))
    return JsonResponse(page(request, [s.to_dict() for s in qs]))


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
        qs = Movement.objects.filter(**_filters(
            request, {"productId": "product_id", "warehouseId": "warehouse_id", "type": "type"}))
        return JsonResponse(page(request, [m.to_dict() for m in qs]))

    if user(request)["role"] not in ("JEFE_BODEGA", "BODEGUERO"):
        return error(request, 403, "FORBIDDEN", "Solo bodega registra movimientos")
    data = body(request) or {}
    missing = [f for f in ("type", "productId", "warehouseId", "quantity", "reason") if data.get(f) in (None, "")]
    if missing:
        return error(request, 400, "VALIDATION_ERROR", "Campos obligatorios faltantes", {"missing": missing})
    mtype, pid, wid, qty = data["type"], data["productId"], data["warehouseId"], float(data["quantity"])
    if mtype not in ("ENTRADA", "SALIDA", "AJUSTE"):
        return error(request, 400, "VALIDATION_ERROR", "type debe ser ENTRADA, SALIDA o AJUSTE")
    if not Warehouse.objects.filter(id=wid).exists():
        return error(request, 400, "VALIDATION_ERROR", "Bodega inexistente")
    if not _can_use_warehouse(request, wid):
        return error(request, 403, "FORBIDDEN", "Bodega fuera del alcance del usuario")
    product = ProductRef.objects.filter(product_id=pid).first()
    if not product:
        ref = data.get("product")
        if not ref:
            return error(request, 400, "VALIDATION_ERROR", "Producto desconocido: enviar 'product' (ProductRef)")
        product = ProductRef.objects.create(product_id=pid, code=ref.get("code", ""), name=ref.get("name", ""),
                                            unit=ref.get("unit", ""), requires_lot=bool(ref.get("requiresLot")))
    uid = user(request)["id"]

    with transaction.atomic():
        if mtype == "ENTRADA":
            if product.requires_lot and not (data.get("lotNumber") and data.get("expiryDate")):
                return error(request, 400, "VALIDATION_ERROR",
                             "Producto con control de lote: lotNumber y expiryDate obligatorios")
            lot = data.get("lotNumber") if product.requires_lot else None
            created = [_apply("ENTRADA", pid, wid, lot, qty, data["reason"], uid, expiry=data.get("expiryDate"))]
        elif mtype == "SALIDA":
            if data.get("lotNumber"):
                row = Stock.objects.select_for_update().filter(
                    product_id=pid, warehouse_id=wid, lot_number=data["lotNumber"]).first()
                current = row.quantity if row else 0
                allocations = [{"lotNumber": data["lotNumber"], "quantity": qty}] if current >= qty else None
            else:
                allocations = _fefo(pid, wid, qty, lock=True)
            if allocations is None:
                return error(request, 422, "INSUFFICIENT_STOCK", "Stock insuficiente en la bodega")
            created = [_apply("SALIDA", pid, wid, a["lotNumber"], -a["quantity"], data["reason"], uid)
                       for a in allocations]
        else:
            lot = data.get("lotNumber") if product.requires_lot else None
            row = Stock.objects.select_for_update().filter(product_id=pid, warehouse_id=wid,
                                                           lot_number=lot or "").first()
            if (row.quantity if row else 0) + qty < 0:
                return error(request, 422, "INSUFFICIENT_STOCK", "El ajuste dejaría saldo negativo")
            created = [_apply("AJUSTE", pid, wid, lot, qty, data["reason"], uid)]
    return JsonResponse(created, status=201, safe=False)


def _transfer_or_404(request, transfer_id, lock=False):
    qs = Transfer.objects.select_for_update() if lock else Transfer.objects
    t = qs.filter(id=transfer_id).first()
    return (t, None) if t else (None, error(request, 404, "NOT_FOUND", "Traslado no encontrado"))


def _change(t, status, uid, notes=""):
    t.status = status
    t.history = t.history + [{"status": status, "userId": uid, "at": _now(), "notes": notes}]
    t.save()


@csrf_exempt
@require_http_methods(["GET", "POST"])
@roles("GERENTE", "JEFE_BODEGA", "BODEGUERO", "VENDEDOR", "AUDITOR")
@idempotent
def transfers(request):
    if request.method == "GET":
        qs = Transfer.objects.filter(**_filters(request, {"status": "status"}))
        return JsonResponse(page(request, [t.to_dict() for t in qs]))
    if user(request)["role"] not in ("VENDEDOR", "BODEGUERO", "JEFE_BODEGA"):
        return error(request, 403, "FORBIDDEN", "Rol sin permiso para solicitar traslados")
    data = body(request) or {}
    origin, dest, items = data.get("originId"), data.get("destinationId"), data.get("items") or []
    valid = set(Warehouse.objects.filter(id__in=[origin, dest]).values_list("id", flat=True))
    if origin not in valid or dest not in valid or origin == dest or not items:
        return error(request, 400, "VALIDATION_ERROR", "originId/destinationId válidos y distintos, e items no vacío")
    t = Transfer(
        origin_id=origin, destination_id=dest, status="SOLICITADO",
        items=[{"productId": i["productId"], "requestedQuantity": i["quantity"], "lots": []} for i in items],
    )
    _change(t, "SOLICITADO", user(request)["id"], data.get("notes", ""))
    return JsonResponse(t.to_dict(), status=201)


@require_http_methods(["GET"])
@roles("GERENTE", "JEFE_BODEGA", "BODEGUERO", "VENDEDOR", "AUDITOR")
def transfer_detail(request, transfer_id):
    t, err = _transfer_or_404(request, transfer_id)
    return err or JsonResponse(t.to_dict())


@csrf_exempt
@require_http_methods(["POST"])
@roles("JEFE_BODEGA")
@transaction.atomic
def transfer_approve(request, transfer_id):
    t, err = _transfer_or_404(request, transfer_id, lock=True)
    if err:
        return err
    if t.status != "SOLICITADO":
        return error(request, 409, "INVALID_STATE", f"No se puede aprobar en estado {t.status}")
    _change(t, "APROBADO", user(request)["id"])
    return JsonResponse(t.to_dict())


@csrf_exempt
@require_http_methods(["POST"])
@roles("JEFE_BODEGA", "BODEGUERO")
@idempotent
@transaction.atomic
def transfer_dispatch(request, transfer_id):
    t, err = _transfer_or_404(request, transfer_id, lock=True)
    if err:
        return err
    if t.status != "APROBADO":
        return error(request, 409, "INVALID_STATE", f"No se puede despachar en estado {t.status}")
    plan = []
    for item in t.items:
        allocations = _fefo(item["productId"], t.origin_id, item["requestedQuantity"], lock=True)
        if allocations is None:
            return error(request, 422, "INSUFFICIENT_STOCK", f"Stock insuficiente de {item['productId']} en origen")
        plan.append((item, allocations))
    uid = user(request)["id"]
    for item, allocations in plan:
        for a in allocations:
            _apply("TRASLADO_SALIDA", item["productId"], t.origin_id, a["lotNumber"], -a["quantity"],
                   "TRASLADO", uid, "TRASLADO", str(t.id))
            item["lots"].append({"lotNumber": a["lotNumber"], "expiryDate": a["expiryDate"],
                                 "dispatchedQuantity": a["quantity"], "receivedQuantity": None,
                                 "difference": None, "differenceReason": None})
    _change(t, "EN_TRANSITO", uid)
    return JsonResponse(t.to_dict())


@csrf_exempt
@require_http_methods(["POST"])
@roles("JEFE_BODEGA", "BODEGUERO")
@idempotent
@transaction.atomic
def transfer_receive(request, transfer_id):
    t, err = _transfer_or_404(request, transfer_id, lock=True)
    if err:
        return err
    if t.status != "EN_TRANSITO":
        return error(request, 409, "INVALID_STATE", f"No se puede recibir en estado {t.status}")
    received = {(r["productId"], r.get("lotNumber")): r for r in (body(request) or {}).get("lots", [])}
    uid, with_diff = user(request)["id"], False
    for item in t.items:
        for lot in item["lots"]:
            r = received.get((item["productId"], lot["lotNumber"]))
            qty = float(r["receivedQuantity"]) if r else lot["dispatchedQuantity"]
            lot["receivedQuantity"] = qty
            lot["difference"] = qty - lot["dispatchedQuantity"]
            lot["differenceReason"] = (r or {}).get("differenceReason")
            with_diff = with_diff or lot["difference"] != 0
            if qty > 0:
                _apply("TRASLADO_ENTRADA", item["productId"], t.destination_id, lot["lotNumber"], qty,
                       "TRASLADO", uid, "TRASLADO", str(t.id), expiry=lot["expiryDate"])
    _change(t, "RECIBIDO_CON_DIFERENCIAS" if with_diff else "RECIBIDO", uid)
    return JsonResponse(t.to_dict())


@csrf_exempt
@require_http_methods(["POST"])
@idempotent
@transaction.atomic
def internal_entries(request):
    if not request.headers.get("Idempotency-Key"):
        return error(request, 400, "VALIDATION_ERROR", "Idempotency-Key obligatoria")
    data = body(request) or {}
    if not data.get("lines") or not Warehouse.objects.filter(id=data.get("warehouseId")).exists():
        return error(request, 400, "VALIDATION_ERROR", "warehouseId válido y lines obligatorios")
    created = []
    for line in data["lines"]:
        product = line["product"]
        ProductRef.objects.get_or_create(
            product_id=product["productId"],
            defaults={"code": product.get("code", ""), "name": product.get("name", ""),
                      "unit": product.get("unit", ""), "requires_lot": bool(product.get("requiresLot"))},
        )
        lot = line.get("lotNumber") if product.get("requiresLot") else None
        created.append(_apply("ENTRADA_COMPRA", product["productId"], data["warehouseId"], lot,
                              float(line["quantity"]), "COMPRA", user(request)["id"], "RECEPCION_OC",
                              data.get("receiptId"), expiry=line.get("expiryDate")))
    return JsonResponse(created, status=201, safe=False)
